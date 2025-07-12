import uuid
from typing import Any, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlmodel import col, delete, func, select
from sqlalchemy.orm import joinedload, selectinload

from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.models import User, UserSubscription, Payment
from app.schemas.base import Message, ListResponse
from app.schemas.user import (
    UserCreate,
    TokenResponse,
    UserResponse,
    UserUpdate,
    UserUpdateMe,
    UserRegister,
    UpdatePassword,
    SocialLoginRequest,
    SocialAccountResponse,
    SocialLinkRequest,
)
from app.cruds.users import (
    create_user,
    get_user_by_email,
)
from app.utils.sent_email import (
    generate_new_account_email,
    send_email,
)
from app.utils.file_uploads import file_upload_service

from app.cruds.social_account import (
    get_social_account_by_provider,
    create_social_account,
    get_user_social_accounts,
    delete_social_account,
    get_user_info_from_provider,
    create_user_from_social,
)
from app.core import security
import logging
import os

logger = logging.getLogger("users")

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=ListResponse,
)
def read_users(session: SessionDep, offset: int = 0, limit: int = 100) -> Any:
    """
    Retrieve users.
    """

    count_statement = select(func.count()).select_from(User)
    count = session.exec(count_statement).one()

    statement = (
        select(User)
        .options(
            joinedload(User.billing_info),
            joinedload(User.subscriptions),
            joinedload(User.payments),
        )
        .offset(offset)
        .limit(limit)
    )
    users = session.exec(statement).unique().all()

    return ListResponse(data=users, count=count)


@router.post(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserResponse,
)
def create_user_endpoint(*, session: SessionDep, user_in: UserCreate) -> Any:
    """
    Create new user.
    """
    user = get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    user = create_user(session=session, user_create=user_in)
    if settings.emails_enabled and user_in.email:
        email_data = generate_new_account_email(
            email_to=user_in.email, username=user_in.email, password=user_in.password
        )
        send_email(
            email_to=user_in.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return user


@router.patch("/me", response_model=UserResponse)
def update_user_me(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    full_name: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    company_name: Optional[str] = Form(None),
    website_url: Optional[str] = Form(None),
    avatar: Optional[UploadFile] = File(None),
) -> Any:
    """
    Update own user with optional avatar upload.
    """

    # Handle avatar upload if provided
    avatar_url = None
    if avatar:
        # Validate avatar file
        if not avatar.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail=f"avatar must be an image",
            )

        # Delete old avatar if exists
        # if current_user.avatar_url:
        #     old_avatar_path = current_user.avatar_url.replace("/public/", "public/")
        #     delete_file(old_avatar_path)

        # Save new avatar
        try:
            file_info = file_upload_service.upload_compressed_image(
                file=avatar,
                folder="user-avatars",
                filename=f"avatar_{current_user.id}.webp",
                type="image",
                max_size=5 * 1024 * 1024,
                quality=80,
                max_width=512,
                max_height=512,
                format="webp",
            )
            avatar_url = file_info.url
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to upload avatar: {str(e)}"
            )

    # Prepare update data
    update_data = {}
    if full_name is not None:
        update_data["full_name"] = full_name
    if phone_number is not None:
        update_data["phone_number"] = phone_number
    if company_name is not None:
        update_data["company_name"] = company_name
    if website_url is not None:
        update_data["website_url"] = website_url
    if avatar_url is not None:
        update_data["avatar_url"] = avatar_url

    # Update user
    if update_data:
        current_user.sqlmodel_update(update_data)
        session.add(current_user)
        session.commit()
        session.refresh(current_user)

    return current_user


@router.patch("/me/password", response_model=Message)
def update_password_me(
    *, session: SessionDep, body: UpdatePassword, current_user: CurrentUser
) -> Any:
    """
    Update own password.
    """
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400, detail="New password cannot be the same as the current one"
        )
    hashed_password = get_password_hash(body.new_password)
    current_user.hashed_password = hashed_password
    session.add(current_user)
    session.commit()
    return Message(message="Password updated successfully")


@router.get("/me", response_model=UserResponse)
def read_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Get current user.
    """

    user = session.exec(
        select(User)
        .where(User.id == str(current_user.id))
        .options(
            joinedload(User.billing_info),
            joinedload(User.subscriptions).joinedload(
                UserSubscription.subscription_plan
            ),
            joinedload(User.subscriptions).joinedload(UserSubscription.payments),
            joinedload(User.payments).joinedload(Payment.user_subscription),
            joinedload(User.social_accounts),
        )
    ).first()
    return user


@router.post("/signup", response_model=UserResponse)
def register_user(session: SessionDep, user_in: UserRegister) -> Any:
    """
    Create new user without the need to be logged in.
    """
    user = get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )
    logger.info(f"User in: {user_in}")
    # Convert UserRegister to UserCreate by extracting the dict and creating new instance
    user_create = UserCreate(**user_in.model_dump())
    user = create_user(session=session, user_create=user_create)
    return user


@router.get("/{user_id}", response_model=UserResponse)
def read_user_by_id(
    user_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Any:
    """
    Get a specific user by id.
    """
    user = session.get(User, user_id)
    if user == current_user:
        return user
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges",
        )
    return user


@router.patch(
    "/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserResponse,
)
def update_user_by_id(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    full_name: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    company_name: Optional[str] = Form(None),
    website_url: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    is_superuser: Optional[bool] = Form(None),
    password: Optional[str] = Form(None),
    avatar: Optional[UploadFile] = File(None),
) -> Any:
    """
    Update a user with optional avatar upload.
    """

    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )

    # Handle avatar upload if provided
    avatar_url = None
    if avatar:
        # Validate avatar file
        if not avatar.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail=f"avatar must be an image",
            )

        # Delete old avatar if exists
        # if current_user.avatar_url:
        #     old_avatar_path = current_user.avatar_url.replace("/public/", "public/")
        #     delete_file(old_avatar_path)

        # Save new avatar
        try:
            file_info = file_upload_service.upload_compressed_image(
                file=avatar,
                folder="user-avatars",
                filename=f"avatar_{user_id}.webp",
                type="image",
                max_size=5 * 1024 * 1024,
                quality=80,
                max_width=512,
                max_height=512,
                format="webp",
            )
            avatar_url = file_info.url
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to upload avatar: {str(e)}"
            )

    # Prepare update data
    update_data = {}
    if full_name is not None:
        update_data["full_name"] = full_name
    if phone_number is not None:
        update_data["phone_number"] = phone_number
    if company_name is not None:
        update_data["company_name"] = company_name
    if website_url is not None:
        update_data["website_url"] = website_url
    if role is not None:
        update_data["role"] = role
    if is_superuser is not None:
        update_data["is_superuser"] = is_superuser
    if password is not None:
        update_data["hashed_password"] = get_password_hash(password)
    if avatar_url is not None:
        update_data["avatar_url"] = avatar_url

    # Update user
    if update_data:
        db_user.sqlmodel_update(update_data)
        session.add(db_user)
        session.commit()
        session.refresh(db_user)

    return db_user


@router.delete("/{user_id}", dependencies=[Depends(get_current_active_superuser)])
def delete_user(
    session: SessionDep, current_user: CurrentUser, user_id: uuid.UUID
) -> Message:
    """
    Delete a user.
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user == current_user:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    session.delete(user)
    session.commit()
    return Message(message="User deleted successfully")


@router.post(
    "/{user_id}/set_active_trial", dependencies=[Depends(get_current_active_superuser)]
)
def set_active_trial(session: SessionDep, user_id: uuid.UUID) -> Message:
    """
    Set active trial for a user (extend trial by 7 days from now).
    Only accessible by superadmin.
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Calculate new trial expiry date: current date + 7 days, rounded to 00:00 of the next day
    trial_end_date = datetime.now() + timedelta(days=7)
    trial_expired_at = trial_end_date.replace(hour=0, minute=0, second=0, microsecond=0)

    user.trial_expired_at = trial_expired_at
    session.add(user)
    session.commit()

    return Message(message="Trial activated successfully")


@router.post(
    "/{user_id}/set_inactive_status",
    dependencies=[Depends(get_current_active_superuser)],
)
def set_inactive_status(
    session: SessionDep, user_id: uuid.UUID, inactive: bool
) -> Message:
    """
    Set inactive status for a user.
    If inactive=True, set inactive_at to current datetime.
    If inactive=False, set inactive_at to None.
    Only accessible by superadmin.
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if inactive:
        user.inactive_at = datetime.now()
        message = "User set to inactive status"
    else:
        user.inactive_at = None
        message = "User set to active status"

    session.add(user)
    session.commit()

    return Message(message=message)


# ============= SOCIAL AUTHENTICATION ROUTES =============


@router.post("/auth/social/login", response_model=TokenResponse)
async def social_login(*, session: SessionDep, social_login: SocialLoginRequest) -> Any:
    """
    Social login/register endpoint.
    If user exists, login. If not, create new user.
    """
    try:
        # Get user info from social provider
        user_info = await get_user_info_from_provider(
            social_login.provider, social_login.access_token
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to verify {social_login.provider} token: {str(e)}",
        )

    provider_user_id = user_info.get("id")
    provider_email = user_info.get("email")
    provider_name = user_info.get("name")

    if not provider_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to get user ID from provider",
        )

    # Check if social account already exists
    social_account = get_social_account_by_provider(
        session=session,
        provider=social_login.provider,
        provider_user_id=provider_user_id,
    )

    user = None
    is_new_user = False

    if social_account:
        # Social account exists, get the user
        user = session.get(User, social_account.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found for this social account",
            )

        # Update avatar if user doesn't have one and we got one from social
        if not user.avatar_url and user_info.get("uploaded_avatar_url"):
            user.avatar_url = user_info.get("uploaded_avatar_url")
    else:
        # Social account doesn't exist
        # Try to find user by email if email is provided
        if provider_email:
            user = get_user_by_email(session=session, email=provider_email)

        if user:
            # User exists with same email, link social account
            create_social_account(
                session=session,
                user_id=user.id,
                provider=social_login.provider,
                provider_user_id=provider_user_id,
                provider_email=provider_email,
            )

            # Update avatar if user doesn't have one and we got one from social
            if not user.avatar_url and user_info.get("uploaded_avatar_url"):
                user.avatar_url = user_info.get("uploaded_avatar_url")
        else:
            # Create new user with avatar if available
            avatar_url = user_info.get("uploaded_avatar_url")
            user = create_user_from_social(
                session=session,
                provider=social_login.provider,
                provider_user_id=provider_user_id,
                provider_email=provider_email,
                provider_name=provider_name,
                avatar_url=avatar_url,
            )
            is_new_user = True

            # Create social account for new user
            create_social_account(
                session=session,
                user_id=user.id,
                provider=social_login.provider,
                provider_user_id=provider_user_id,
                provider_email=provider_email,
            )

    # Update last login provider
    user.last_login_provider = social_login.provider
    session.add(user)
    session.commit()
    session.refresh(user)

    # Generate tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    refresh_token = security.create_refresh_token(
        user.id, expires_delta=refresh_token_expires
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/me/social/link", response_model=Message)
async def link_social_account(
    *, session: SessionDep, current_user: CurrentUser, link_request: SocialLinkRequest
) -> Any:
    """
    Link a social account to current user.
    """
    try:
        # Get user info from social provider
        user_info = await get_user_info_from_provider(
            link_request.provider, link_request.access_token
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to verify {link_request.provider} token: {str(e)}",
        )

    provider_user_id = user_info.get("id")
    provider_email = user_info.get("email")

    if not provider_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to get user ID from provider",
        )

    # Check if social account already exists
    existing_social_account = get_social_account_by_provider(
        session=session,
        provider=link_request.provider,
        provider_user_id=provider_user_id,
    )

    if existing_social_account:
        if existing_social_account.user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This social account is already linked to your account",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This social account is already linked to another user",
            )

    # Create social account link
    create_social_account(
        session=session,
        user_id=current_user.id,
        provider=link_request.provider,
        provider_user_id=provider_user_id,
        provider_email=provider_email,
    )

    return Message(
        message=f"{link_request.provider.title()} account linked successfully"
    )


@router.get("/me/social/accounts", response_model=list[SocialAccountResponse])
def get_my_social_accounts(*, session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Get all social accounts linked to current user.
    """
    social_accounts = get_user_social_accounts(session=session, user_id=current_user.id)
    return social_accounts


@router.delete("/me/social/{provider}", response_model=Message)
def unlink_social_account(
    *, session: SessionDep, current_user: CurrentUser, provider: str
) -> Any:
    """
    Unlink a social account from current user.
    """
    if provider not in ["facebook", "google", "apple"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid provider"
        )

    success = delete_social_account(
        session=session, user_id=current_user.id, provider=provider
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {provider} account linked to your account",
        )

    return Message(message=f"{provider.title()} account unlinked successfully")
