from datetime import timedelta
from typing import Annotated, Any
import logging
from collections import defaultdict
from time import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr

from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.core import security
from app.core.config import settings
from app.core.security import get_password_hash
from app.schemas.base import Message
from app.schemas.user import (
    TokenResponse,
    RefreshTokenRequest,
    NewPassword,
    UserResponse,
)

from app.cruds.users import (
    authenticate,
    get_user_by_email,
)

from app.utils.sent_email import (
    generate_password_reset_token,
    generate_reset_password_email,
    send_email,
    verify_password_reset_token,
)

router = APIRouter(tags=["login"])

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
