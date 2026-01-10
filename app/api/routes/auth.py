from datetime import timedelta
from typing import Annotated, Any
import logging
from collections import defaultdict
from time import time

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr

from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser, get_db, get_current_user
from app.core import security
from app.core.config import settings
from app.core.security import get_password_hash
from app.schemas.base import Message
from app.schemas.user import (
    TokenResponse,
    RefreshTokenRequest,
    NewPassword,
    UserResponse,
    UserRegister,
    UserCreate,
    SocialLoginRequest,
    SocialLinkRequest,
    SocialAccountResponse,
    NotificationTokenRegisterRequest,
    NotificationTokenResponse,
) 

from app.cruds.users import (
    authenticate,
    get_user_by_email,
    create_user,
)

from app.cruds.social_account import (
    get_social_account_by_provider,
    create_social_account,
    get_user_social_accounts,
    delete_social_account,
    get_user_info_from_provider,
    create_user_from_social,
)

from app.cruds.device_tokens import DeviceTokenCRUD as NotificationTokenCRUD

from app.models import User

from app.utils.sent_email import (
    generate_password_reset_token,
    generate_reset_password_email,
    send_email,
    verify_password_reset_token,
    generate_new_account_email,
)

router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger(__name__)

# Simple rate limiting for password recovery
password_recovery_attempts = defaultdict(list)
MAX_ATTEMPTS_PER_HOUR = 3
RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds


def check_rate_limit(email: str) -> bool:
    """Check if email has exceeded rate limit for password recovery"""
    now = time()
    attempts = password_recovery_attempts[email]

    # Remove old attempts outside the window
    password_recovery_attempts[email] = [
        attempt_time
        for attempt_time in attempts
        if now - attempt_time < RATE_LIMIT_WINDOW
    ]

    # Check if current attempts exceed limit
    if len(password_recovery_attempts[email]) >= MAX_ATTEMPTS_PER_HOUR:
        return False

    # Add current attempt
    password_recovery_attempts[email].append(now)
    return True


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login/access-token", response_model=TokenResponse)
def login_access_token(session: SessionDep, body: LoginRequest) -> TokenResponse:
    """
    OAuth2 compatible token login, get an access token and refresh token for future requests
    """
    user = authenticate(session=session, email=body.username, password=body.password)
    logger.info(f"User: {user}")
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif user.inactive_at is not None:
        raise HTTPException(status_code=400, detail="Inactive user")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    refresh_token = security.create_refresh_token(
        user.id, expires_delta=refresh_token_expires
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login/refresh-token", response_model=TokenResponse)
def refresh_access_token(body: RefreshTokenRequest) -> TokenResponse:
    """
    Get new access token from refresh token
    """
    user_id = security.verify_refresh_token(body.refresh_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user_id, expires_delta=access_token_expires
    )
    return TokenResponse(access_token=access_token)


@router.post("/password-recovery/{email}")
def recover_password(email: EmailStr, session: SessionDep) -> Message:
    """
    Password Recovery
    """
    # Check rate limit
    if not check_rate_limit(email):
        raise HTTPException(
            status_code=429,
            detail="Too many password recovery attempts. Please try again after 1 hour.",
        )

    user = get_user_by_email(session=session, email=email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this email does not exist in the system.",
        )

    try:
        password_reset_token = generate_password_reset_token(email=email)
        logger.info(f"Password reset token: {password_reset_token}")
        email_data = generate_reset_password_email(
            email_to=user.email, email=email, token=password_reset_token
        )
        logger.info(f"Email data: {email_data}")
        send_email(
            email_to=user.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
        logger.info(f"Password recovery email sent to {user.email}")
        return Message(message="Password recovery email sent")
    except AssertionError as e:
        logger.error(f"Email configuration error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Email service is not configured properly. Please contact administrator.",
        )
    except Exception as e:
        logger.error(f"Failed to send password recovery email to {user.email}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to send password recovery email. Please try again later.",
        )


@router.post("/reset-password/")
def reset_password(session: SessionDep, body: NewPassword) -> Message:
    """
    Reset password
    """
    email = verify_password_reset_token(token=body.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")
    user = get_user_by_email(session=session, email=email)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this email does not exist in the system.",
        )
    elif user.inactive_at is not None:
        raise HTTPException(status_code=400, detail="Inactive user")
    hashed_password = get_password_hash(password=body.new_password)
    user.hashed_password = hashed_password
    session.add(user)
    session.commit()
    return Message(message="Password updated successfully")


@router.post(
    "/password-recovery-html-content/{email}",
    dependencies=[Depends(get_current_active_superuser)],
    response_class=HTMLResponse,
)
def recover_password_html_content(email: str, session: SessionDep) -> Any:
    """
    HTML Content for Password Recovery
    """
    user = get_user_by_email(session=session, email=email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system.",
        )
    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )

    return HTMLResponse(
        content=email_data.html_content, headers={"subject:": email_data.subject}
    )


# ============= SIGNUP ROUTE =============


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
    
    # Send welcome email if enabled
    if settings.emails_enabled and user_in.email:
        try:
            email_data = generate_new_account_email(
                email_to=user_in.email, 
                username=user_in.email, 
                password=""  # For signup, we don't send password in email
            )
            send_email(
                email_to=user_in.email,
                subject=email_data.subject,
                html_content=email_data.html_content,
            )
        except Exception as e:
            logger.warning(f"Failed to send welcome email to {user_in.email}: {e}")
    
    return user


# ============= SOCIAL AUTHENTICATION ROUTES =============


@router.post("/social/login", response_model=TokenResponse)
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
    phone_number = user_info.get("phone_number")  # For Firebase Phone auth

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
        # Try to find user by email if email is provided, or by phone for Firebase Phone
        user = None
        if provider_email:
            user = get_user_by_email(session=session, email=provider_email)
        elif phone_number and social_login.provider == "firebase_phone":
            # For Firebase Phone, try to find user by phone number
            from sqlmodel import select
            from app.models import User

            statement = select(User).where(User.phone_number == phone_number)
            user = session.exec(statement).first()

        if user:
            # User exists with same email/phone, link social account
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
                phone_number=phone_number,
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


@router.post("/social/link", response_model=Message)
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


@router.get("/social/accounts", response_model=list[SocialAccountResponse])
def get_my_social_accounts(*, session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Get all social accounts linked to current user.
    """
    social_accounts = get_user_social_accounts(session=session, user_id=current_user.id)
    return social_accounts


@router.delete("/social/{provider}", response_model=Message)
def unlink_social_account(
    *, session: SessionDep, current_user: CurrentUser, provider: str
) -> Any:
    """
    Unlink a social account from current user.
    """
    if provider not in ["facebook", "google", "apple", "firebase_phone"]:
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


# ==================== Device Token Registration ====================

@router.post(
    "/device-token",
    response_model=NotificationTokenResponse,
    summary="Register device token for push notifications",
    description="Register a new device token for push notifications. If the device already has a token for this provider, it will be updated.",
)
async def register_device_token(
    request: NotificationTokenRegisterRequest,
    current_user: CurrentUser,
    db: SessionDep,
) -> NotificationTokenResponse:
    """
    Register a device token for the authenticated user.
    
    This endpoint allows users to register their device tokens for push notifications.
    If the same device already has a token for the specified provider, it will be updated.
    
    Query Parameters:
    - provider: The push notification provider (fcm, apns, etc.)
    - device_token: The actual token from the provider
    - device_type: Type of device (ios, android, web, etc.)
    - device_name: (Optional) User-friendly name for the device
    - device_id: (Optional) Hardware identifier
    - app_version: (Optional) App version
    - os_version: (Optional) OS version
    """
    token = NotificationTokenCRUD.register_token(
        db=db,
        user_id=current_user.id,
        provider=request.provider,
        device_token=request.device_token,
        device_type=request.device_type,
        device_name=request.device_name,
        device_id=request.device_id,
        app_version=request.app_version,
        os_version=request.os_version,
    )
    return token
