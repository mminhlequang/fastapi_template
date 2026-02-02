import uuid
from typing import Any, Optional
from datetime import datetime, timedelta, date

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, status
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
    UserResponse,
    UserUpdate,
    UserUpdateMe,
    UpdatePassword,
    RequestUpdateEmailOTP,
    VerifyUpdateEmailOTP,
    ConfirmUpdateEmail,
    EmailUpdateTokenResponse,
    RequestUpdatePhoneCheck,
    PhoneAvailabilityResponse,
    ConfirmUpdatePhone,
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
    country_code: Optional[str] = Form(None),
    locale: Optional[str] = Form(None),
    timezone: Optional[str] = Form(None),
    currency: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    birth_date: Optional[date] = Form(None),
    bio: Optional[str] = Form(None),
    job_title: Optional[str] = Form(None),
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
    if country_code is not None:
        update_data["country_code"] = country_code
    if locale is not None:
        update_data["locale"] = locale
    if timezone is not None:
        update_data["timezone"] = timezone
    if currency is not None:
        update_data["currency"] = currency
    if gender is not None:
        update_data["gender"] = gender
    if birth_date is not None:
        update_data["birth_date"] = birth_date
    if bio is not None:
        update_data["bio"] = bio
    if job_title is not None:
        update_data["job_title"] = job_title
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
    country_code: Optional[str] = Form(None),
    locale: Optional[str] = Form(None),
    timezone: Optional[str] = Form(None),
    currency: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    birth_date: Optional[date] = Form(None),
    bio: Optional[str] = Form(None),
    job_title: Optional[str] = Form(None),
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
    if country_code is not None:
        update_data["country_code"] = country_code
    if locale is not None:
        update_data["locale"] = locale
    if timezone is not None:
        update_data["timezone"] = timezone
    if currency is not None:
        update_data["currency"] = currency
    if gender is not None:
        update_data["gender"] = gender
    if birth_date is not None:
        update_data["birth_date"] = birth_date
    if bio is not None:
        update_data["bio"] = bio
    if job_title is not None:
        update_data["job_title"] = job_title
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


# ============================================
# Email Update Flow with OTP
# ============================================


@router.post("/me/update-email/otp-request", response_model=Message)
def request_email_update_otp(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    body: RequestUpdateEmailOTP,
) -> Message:
    """
    Step 1: Request OTP for email update
    Sends a 6-digit OTP to the new email address
    """
    from app.services.otp_service import (
        create_otp,
        send_otp_email,
        OTP_EXPIRY_MINUTES,
        OTP_PURPOSE_EMAIL_UPDATE,
    )

    # Normalize new email
    normalized_email = body.new_email.lower()

    # Check if user is trying to update to the same email
    if current_user.email == normalized_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New email is the same as your current email.",
        )

    # Check if new email already exists in system
    existing_user = get_user_by_email(session=session, email=normalized_email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The email address is already registered in the system.",
        )

    try:
        # Create OTP
        otp_record = create_otp(
            session=session,
            purpose=OTP_PURPOSE_EMAIL_UPDATE,
            user_id=current_user.id,
            email=normalized_email,
            otp_expiry_minutes=OTP_EXPIRY_MINUTES,
        )

        # Send OTP email
        send_otp_email(
            email_to=normalized_email,
            otp_code=otp_record.otp_code,
            purpose=OTP_PURPOSE_EMAIL_UPDATE,
            valid_minutes=OTP_EXPIRY_MINUTES,
        )

        logger.info(
            f"Email update OTP sent to {normalized_email} for user {current_user.id}"
        )
        logger.info(
            f"OTP Code (dev only): {otp_record.otp_code}"
        )  # Remove in production

        return Message(
            message=f"Verification code has been sent to {normalized_email}. Valid for {OTP_EXPIRY_MINUTES} minutes."
        )

    except AssertionError as e:
        logger.error(f"Email configuration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email service is not configured properly. Please contact administrator.",
        )
    except Exception as e:
        logger.error(f"Failed to send email update OTP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification code. Please try again later.",
        )


@router.post("/me/update-email/otp-verify", response_model=EmailUpdateTokenResponse)
def verify_email_update_otp(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    body: VerifyUpdateEmailOTP,
) -> EmailUpdateTokenResponse:
    """
    Step 2: Verify OTP and get confirmation token

    Flow:
    1. User calls /otp-request with new_email → receives OTP via email
    2. User calls /otp-verify with new_email + OTP → receives confirmation_token
    3. User calls /confirm with confirmation_token + new_email → email is updated

    Args:
        body: New email and OTP code
        session: Database session
        current_user: Current authenticated user

    Returns:
        Confirmation token that can be used to update email
    """
    from app.services.otp_service import (
        verify_otp_code,
        mark_otp_as_used,
        OTP_PURPOSE_EMAIL_UPDATE,
    )
    from app.core import security

    # Normalize email
    normalized_email = body.new_email.lower()

    # Verify OTP (this will raise HTTPException if invalid)
    otp_record = verify_otp_code(
        session, normalized_email, body.otp_code, purpose=OTP_PURPOSE_EMAIL_UPDATE
    )

    # Verify that the OTP belongs to the current user
    if otp_record.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This OTP does not belong to you.",
        )

    # Generate confirmation token
    confirmation_token = security.create_otp_token(
        email=normalized_email,
        otp_id=str(otp_record.id),
        expires_delta=timedelta(minutes=15),  # 15 minutes to confirm email update
    )

    # Mark OTP as used
    mark_otp_as_used(session, otp_record)
    session.commit()

    logger.info(
        f"OTP verified for email update to {normalized_email}, user {current_user.id}"
    )

    return EmailUpdateTokenResponse(
        confirmation_token=confirmation_token,
        message="OTP verified successfully. Use the confirmation_token to update your email.",
    )


@router.post("/me/update-email/confirm", response_model=Message)
def confirm_email_update(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    body: ConfirmUpdateEmail,
) -> Message:
    """
    Step 3: Confirm email update with token from OTP verification

    Flow:
    1. User calls /otp-request with new_email → receives OTP via email
    2. User calls /otp-verify with new_email + OTP → receives confirmation_token
    3. User calls /confirm with confirmation_token + new_email → email is updated

    Args:
        body: Confirmation token and new email
        session: Database session
        current_user: Current authenticated user

    Returns:
        Success message
    """
    from app.core import security

    try:
        # Verify and decode confirmation token
        payload = security.decode_otp_token(body.confirmation_token)

        if "email" not in payload or "otp_id" not in payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid confirmation token format",
            )

        token_email = payload.get("email")
        normalized_new_email = body.new_email.lower()

        # Verify that the email in token matches the new email provided
        if token_email != normalized_new_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address does not match the verified email.",
            )

        # Check if user is trying to update to the same email
        if current_user.email == normalized_new_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New email is the same as your current email.",
            )

        # Check if new email already exists in system (double check)
        existing_user = get_user_by_email(session=session, email=normalized_new_email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The email address is already registered in the system.",
            )

        # Update user's email
        old_email = current_user.email
        current_user.email = normalized_new_email
        session.add(current_user)
        session.commit()
        session.refresh(current_user)

        logger.info(
            f"Email updated successfully for user {current_user.id}: {old_email} -> {normalized_new_email}"
        )

        return Message(message="Email address updated successfully.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to confirm email update: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired confirmation token.",
        )


# ============================================
# Phone Update Flow
# ============================================


@router.post("/me/update-phone/check", response_model=PhoneAvailabilityResponse)
def check_phone_availability(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    body: RequestUpdatePhoneCheck,
) -> PhoneAvailabilityResponse:
    """
    Check if the new phone number can be used.
    Returns availability without applying any changes.
    """
    from app.cruds.users import get_user_by_phone_number

    new_phone = body.new_phone_number.strip()

    # Same as current phone
    if current_user.phone_number == new_phone:
        return PhoneAvailabilityResponse(is_available=False)

    # Check existing user
    existing_user = get_user_by_phone_number(session=session, phone_number=new_phone)
    if existing_user and existing_user.id != current_user.id:
        return PhoneAvailabilityResponse(is_available=False)

    return PhoneAvailabilityResponse(is_available=True)


@router.post("/me/update-phone/confirm", response_model=Message)
def confirm_phone_update(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    body: ConfirmUpdatePhone,
) -> Message:
    """
    Update current user's phone number.
    Note: This is a simplified version. In production, you should verify 
    the phone number with OTP or other verification methods.
    """
    from app.cruds.users import get_user_by_phone_number

    new_phone = body.new_phone_number.strip()

    # Check if same as current phone
    if current_user.phone_number == new_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New phone number is the same as your current phone number.",
        )

    # Check if phone already exists
    existing_user = get_user_by_phone_number(session=session, phone_number=new_phone)
    if existing_user and existing_user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This phone number is already registered in the system.",
        )

    # Update phone number
    old_phone = current_user.phone_number
    current_user.phone_number = new_phone
    session.add(current_user)
    session.commit()
    session.refresh(current_user)

    logger.info(
        f"Phone updated successfully for user {current_user.id}: {old_phone} -> {new_phone}"
    )

    return Message(message="Phone number updated successfully.")
