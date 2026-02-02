import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, List

import emails  # type: ignore
import jwt
from jinja2 import Template
from jwt.exceptions import InvalidTokenError

from app.core import security
from app.core.config import settings
import uuid
from typing import Any

from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.models import User
from app.schemas.user import UserCreate, UserUpdate

import os
import shutil
from fastapi import UploadFile, HTTPException


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

 
@dataclass
class EmailData:
    html_content: str
    subject: str


def render_email_template(*, template_name: str, context: dict[str, Any]) -> str:
    template_str = (
        Path(__file__).parent.parent / "email-templates" / template_name
    ).read_text()
    html_content = Template(template_str).render(context)
    return html_content


def send_email(
    *,
    email_to: str,
    subject: str = "",
    html_content: str = "",
) -> None:
    assert settings.emails_enabled, "no provided configuration for email variables"
    message = emails.Message(
        subject=subject,
        html=html_content,
        mail_from=(settings.EMAILS_FROM_NAME, settings.EMAILS_FROM_EMAIL),
    )
    smtp_options = {"host": settings.SMTP_HOST, "port": settings.SMTP_PORT}
    if settings.SMTP_TLS:
        smtp_options["tls"] = True
    elif settings.SMTP_SSL:
        smtp_options["ssl"] = True
    if settings.SMTP_USER:
        smtp_options["user"] = settings.SMTP_USER
    if settings.SMTP_PASSWORD:
        smtp_options["password"] = settings.SMTP_PASSWORD
    response = message.send(to=email_to, smtp=smtp_options)
    logger.info(f"send email result: {response}")


def generate_test_email(email_to: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Test email"
    html_content = render_email_template(
        template_name="test_email.html",
        context={"project_name": settings.PROJECT_NAME, "email": email_to},
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_reset_password_email(email_to: str, email: str, token: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Password recovery for user {email}"
    link = f"{settings.FRONTEND_HOST}/reset-password?token={token}"
    html_content = render_email_template(
        template_name="reset_password.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "username": email,
            "email": email_to,
            "valid_hours": settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
            "link": link,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_new_account_email(
    email_to: str, username: str, password: str
) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - New account for user {username}"
    html_content = render_email_template(
        template_name="new_account.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "username": username,
            "password": password,
            "email": email_to,
            "link": settings.FRONTEND_HOST,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_password_reset_token(email: str) -> str:
    delta = timedelta(hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
    now = datetime.now(timezone.utc)
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {"exp": exp, "nbf": now, "sub": email},
        settings.SECRET_KEY,
        algorithm=security.ALGORITHM,
    )
    return encoded_jwt


def verify_password_reset_token(token: str) -> str | None:
    try:
        decoded_token = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        return str(decoded_token["sub"])
    except InvalidTokenError:
        return None


def generate_otp_email(
    email_to: str,
    otp_code: str,
    purpose: str,
    valid_minutes: int = 10,
) -> EmailData:
    """
    Generate OTP email for any purpose

    Args:
        email_to: Recipient email
        otp_code: 6-digit OTP code
        purpose: Purpose of OTP (password_reset, email_verification, etc.)
        valid_minutes: Validity period in minutes
    """
    project_name = settings.PROJECT_NAME

    # OTP configuration based on purpose
    otp_config = {
        "password_reset": {
            "icon": "🔐",
            "title": "Password Reset OTP",
            "greeting": "Hello",
            "message": "We received a request to reset your password for your account.",
            "purpose_detail": "Use this OTP to reset your password and regain access to your account.",
            "subject": f"{project_name} - Password Reset OTP",
            "warning_title": "Didn't request this?",
            "warning_message": "If you did not request a password reset, please ignore this email. Your account is safe.",
        },
        "email_verification": {
            "icon": "✉️",
            "title": "Email Verification OTP",
            "greeting": "Hello",
            "message": "Welcome! Please verify your email address to complete your registration.",
            "purpose_detail": "Use this OTP to verify that this email address belongs to you.",
            "subject": f"{project_name} - Email Verification OTP",
            "warning_title": "Didn't create an account?",
            "warning_message": f"If you didn't create a {project_name} account, please ignore this email.",
        },
        "phone_verification": {
            "icon": "📱",
            "title": "Phone Verification OTP",
            "greeting": "Hello",
            "message": "Please verify your phone number to complete your registration.",
            "purpose_detail": "Use this OTP to verify that this phone number belongs to you.",
            "subject": f"{project_name} - Phone Verification OTP",
            "warning_title": "Didn't request this?",
            "warning_message": "If you didn't request a phone verification, please ignore this email.",
        },
        "two_factor_auth": {
            "icon": "🔒",
            "title": "Two-Factor Authentication OTP",
            "greeting": "Hello",
            "message": "Someone is trying to access your account. Use this OTP to verify it's you.",
            "purpose_detail": "This OTP is required to log in to your account for security purposes.",
            "subject": f"{project_name} - Two-Factor Authentication OTP",
            "warning_title": "Suspicious activity?",
            "warning_message": "If this wasn't you, please change your password immediately and contact support.",
        },
        "login": {
            "icon": "🚀",
            "title": "Login OTP",
            "greeting": "Hello",
            "message": "Someone is trying to log in to your account using this email.",
            "purpose_detail": "Use this OTP to complete your login.",
            "subject": f"{project_name} - Login OTP",
            "warning_title": "Unauthorized access?",
            "warning_message": "If this wasn't you, please ignore this email and change your password.",
        },
        "email_update": {
            "icon": "✉️",
            "title": "Email Update Verification OTP",
            "greeting": "Hello",
            "message": "You requested to update the email associated with your account.",
            "purpose_detail": "Use this OTP to verify and confirm your new email address.",
            "subject": f"{project_name} - Email Update OTP",
            "warning_title": "Didn't request this?",
            "warning_message": "If you did not request an email change, please ignore this email and keep your account secure.",
        },
    }

    # Get config for this purpose, default to password_reset
    config = otp_config.get(purpose, otp_config["password_reset"])

    # Build context
    context = {
        "project_name": project_name,
        "icon": config["icon"],
        "title": config["title"],
        "greeting": config["greeting"],
        "message": config["message"],
        "purpose_detail": config["purpose_detail"],
        "otp_code": otp_code,
        "valid_minutes": valid_minutes,
        "warning_title": config["warning_title"],
        "warning_message": config["warning_message"],
    }

    html_content = render_email_template(
        template_name="otp.html",
        context=context,
    )

    return EmailData(html_content=html_content, subject=config["subject"])
