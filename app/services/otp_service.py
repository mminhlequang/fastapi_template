"""
Service for handling OTP (One-Time Password) functionality
Supports multiple purposes: password reset, email verification, phone verification, 2FA, etc.
"""

import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

from sqlmodel import Session, select, col
from fastapi import HTTPException, status

from app.models import OTPVerification, User
from app.utils.sent_email import generate_otp_email, send_email


# Constants
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 10
MAX_OTP_ATTEMPTS = 5

# OTP Purposes
OTP_PURPOSE_PASSWORD_RESET = "password_reset"
OTP_PURPOSE_EMAIL_VERIFICATION = "email_verification"
OTP_PURPOSE_PHONE_VERIFICATION = "phone_verification"
OTP_PURPOSE_2FA = "two_factor_auth"
OTP_PURPOSE_LOGIN = "login"
OTP_PURPOSE_EMAIL_UPDATE = "email_update"


def generate_otp_code() -> str:
    """Generate a 6-digit OTP code"""
    return "".join(random.choices(string.digits, k=OTP_LENGTH))


def create_password_reset_otp(
    session: Session, user: User, otp_expiry_minutes: int = OTP_EXPIRY_MINUTES
) -> OTPVerification:
    """
    Create a new password reset OTP for the user
    Invalidates any existing unused OTPs for this user
    """
    return create_otp(
        session=session,
        purpose=OTP_PURPOSE_PASSWORD_RESET,
        user_id=user.id,
        email=user.email,
        otp_expiry_minutes=otp_expiry_minutes,
    )


def create_otp(
    session: Session,
    purpose: str,
    user_id: Optional[uuid.UUID] = None,
    email: Optional[str] = None,
    phone_number: Optional[str] = None,
    otp_expiry_minutes: int = OTP_EXPIRY_MINUTES,
) -> OTPVerification:
    """
    Create a new OTP for any purpose
    Invalidates any existing unused OTPs for the same purpose and contact
    """
    # Invalidate existing unused OTPs
    query_filters = [
        OTPVerification.purpose == purpose,
        OTPVerification.is_used == False,
    ]

    if user_id:
        query_filters.append(OTPVerification.user_id == user_id)
    if email:
        query_filters.append(OTPVerification.email == email)
    if phone_number:
        query_filters.append(OTPVerification.phone_number == phone_number)

    existing_otps = session.exec(select(OTPVerification).where(*query_filters)).all()

    for otp in existing_otps:
        otp.is_used = True
        session.add(otp)

    # Generate new OTP
    otp_code = generate_otp_code()
    expires_at = datetime.utcnow() + timedelta(minutes=otp_expiry_minutes)

    new_otp = OTPVerification(
        user_id=user_id,
        purpose=purpose,
        email=email,
        phone_number=phone_number,
        otp_code=otp_code,
        expires_at=expires_at,
        is_used=False,
        attempts=0,
    )

    session.add(new_otp)
    session.commit()
    session.refresh(new_otp)

    return new_otp


def send_password_reset_otp_email(
    user_email: str, otp_code: str, valid_minutes: int = OTP_EXPIRY_MINUTES
) -> None:
    """Send password reset OTP email to user"""
    email_data = generate_otp_email(
        email_to=user_email,
        otp_code=otp_code,
        purpose=OTP_PURPOSE_PASSWORD_RESET,
        valid_minutes=valid_minutes,
    )

    send_email(
        email_to=user_email,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )


def send_otp_email(
    email_to: str, otp_code: str, purpose: str, valid_minutes: int = OTP_EXPIRY_MINUTES
) -> None:
    """Send OTP email for any purpose"""
    email_data = generate_otp_email(
        email_to=email_to,
        otp_code=otp_code,
        purpose=purpose,
        valid_minutes=valid_minutes,
    )

    send_email(
        email_to=email_to,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )


def verify_otp_code(
    session: Session,
    email: str,
    otp_code: str,
    purpose: str = OTP_PURPOSE_PASSWORD_RESET,
) -> OTPVerification:
    """
    Verify OTP code for password reset

    Raises:
        HTTPException: If OTP is invalid, expired, or max attempts exceeded
    """
    # Normalize email
    normalized_email = email.lower()

    # Find the most recent unused OTP for this email and purpose
    otp_record = session.exec(
        select(OTPVerification)
        .where(
            OTPVerification.email == normalized_email,
            OTPVerification.otp_code == otp_code,
            OTPVerification.purpose == purpose,
            OTPVerification.is_used == False,
        )
        .order_by(col(OTPVerification.created_at).desc())
    ).first()

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP code"
        )

    # Check if OTP has expired
    if datetime.utcnow() > otp_record.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP code has expired. Please request a new one.",
        )

    # Increment attempts
    otp_record.attempts += 1
    session.add(otp_record)
    session.commit()

    # Check max attempts
    if otp_record.attempts > MAX_OTP_ATTEMPTS:
        otp_record.is_used = True
        session.add(otp_record)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum OTP verification attempts exceeded. Please request a new OTP.",
        )

    return otp_record


def mark_otp_as_used(session: Session, otp_record: OTPVerification) -> None:
    """Mark OTP as used after successful verification"""
    otp_record.is_used = True
    otp_record.used_at = datetime.utcnow()
    session.add(otp_record)
    session.commit()


def cleanup_expired_otps(session: Session) -> int:
    """
    Clean up expired OTPs from database
    Returns number of deleted records
    """
    expired_otps = session.exec(
        select(OTPVerification).where(OTPVerification.expires_at < datetime.utcnow())
    ).all()

    count = len(expired_otps)
    for otp in expired_otps:
        session.delete(otp)

    session.commit()
    return count
