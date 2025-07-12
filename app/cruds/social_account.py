import uuid
import logging
from typing import Any
from datetime import datetime, timedelta
import httpx
import io
from sqlmodel import Session, select
from fastapi import UploadFile

from app.core.security import get_password_hash
from app.models import User, SocialAccount
from app.schemas.user import UserCreate
from app.utils.file_uploads import FileUploadService

logger = logging.getLogger(__name__)


def get_social_account_by_provider(
    *, session: Session, provider: str, provider_user_id: str
) -> SocialAccount | None:
    """Get social account by provider and provider user ID"""
    statement = select(SocialAccount).where(
        SocialAccount.provider == provider,
        SocialAccount.provider_user_id == provider_user_id,
    )
    return session.exec(statement).first()


def create_social_account(
    *,
    session: Session,
    user_id: uuid.UUID,
    provider: str,
    provider_user_id: str,
    provider_email: str | None = None,
) -> SocialAccount:
    """Create a new social account"""
    social_account = SocialAccount(
        user_id=user_id,
        provider=provider,
        provider_user_id=provider_user_id,
        provider_email=provider_email,
        created_at=datetime.utcnow(),
        linked_at=datetime.utcnow(),
    )
    session.add(social_account)
    session.commit()
    session.refresh(social_account)
    return social_account


def get_user_social_accounts(
    *, session: Session, user_id: uuid.UUID
) -> list[SocialAccount]:
    """Get all social accounts for a user"""
    statement = select(SocialAccount).where(SocialAccount.user_id == user_id)
    return list(session.exec(statement).all())


def delete_social_account(
    *, session: Session, user_id: uuid.UUID, provider: str
) -> bool:
    """Delete a social account for a user"""
    statement = select(SocialAccount).where(
        SocialAccount.user_id == user_id, SocialAccount.provider == provider
    )
    social_account = session.exec(statement).first()
    if social_account:
        session.delete(social_account)
        session.commit()
        return True
    return False


async def get_user_info_from_provider(
    provider: str, access_token: str
) -> dict[str, Any]:
    """Get user information from social provider using access token"""

    if provider == "facebook":
        url = f"https://graph.facebook.com/me?fields=id,name,email,picture.width(400).height(400)&access_token={access_token}"
    elif provider == "google":
        url = (
            f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={access_token}"
        )
    elif provider == "apple":
        # TODO: Apple ID token validation is more complex, would need JWT decoding
        raise NotImplementedError("Apple login not implemented yet")
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            raise ValueError(f"Failed to get user info from {provider}")

        user_data = response.json()

        # Normalize the response format
        if provider == "facebook":
            normalized_data = {
                "id": user_data.get("id"),
                "email": user_data.get("email"),
                "name": user_data.get("name"),
            }
            # Get avatar URL from Facebook
            picture_data = user_data.get("picture", {}).get("data", {})
            if picture_data and not picture_data.get("is_silhouette", True):
                normalized_data["avatar_url"] = picture_data.get("url")

        elif provider == "google":
            normalized_data = {
                "id": user_data.get("id"),
                "email": user_data.get("email"),
                "name": user_data.get("name"),
            }
            # Get avatar URL from Google
            if user_data.get("picture"):
                normalized_data["avatar_url"] = user_data.get("picture")

        # Upload avatar to space if available
        if "avatar_url" in normalized_data:
            try:
                uploaded_url = await upload_avatar_from_url(
                    normalized_data["avatar_url"], provider, normalized_data["id"]
                )
                normalized_data["uploaded_avatar_url"] = uploaded_url
                logger.info(
                    f"Successfully uploaded avatar for {provider} user {normalized_data['id']}"
                )
            except Exception as e:
                # Log error but don't fail the entire process
                logger.error(
                    f"Failed to upload avatar for {provider} user {normalized_data['id']}: {e}"
                )

        return normalized_data


async def upload_avatar_from_url(avatar_url: str, provider: str, user_id: str) -> str:
    """Download avatar from URL and upload to space storage"""

    logger.info(
        f"Starting avatar download from {avatar_url} for {provider} user {user_id}"
    )

    async with httpx.AsyncClient() as client:
        # Download avatar image
        response = await client.get(avatar_url)
        if response.status_code != 200:
            raise ValueError(f"Failed to download avatar from {avatar_url}")

        # Create a file-like object from the downloaded content
        image_content = response.content
        image_buffer = io.BytesIO(image_content)

        # Determine file extension from content type
        content_type = response.headers.get("content-type", "image/jpeg")
        if "jpeg" in content_type or "jpg" in content_type:
            file_extension = "jpg"
        elif "png" in content_type:
            file_extension = "png"
        elif "webp" in content_type:
            file_extension = "webp"
        else:
            file_extension = "jpg"  # Default to jpg

        # Create filename for avatar
        filename = f"{provider}_{user_id}_avatar.{file_extension}"

        # Reset buffer position to the beginning
        image_buffer.seek(0)

        # Create UploadFile-like object
        upload_file = UploadFile(
            filename=filename,
            file=image_buffer,
            content_type=content_type,
        )

        # Upload to space using FileUploadService
        file_service = FileUploadService()
        file_info = file_service.upload_file(
            file=upload_file,
            folder="avatars",
            filename=filename,
            file_category="image",
            compress_image=True,
            upload_original=False,
        )

        # Log successful upload
        public_url = file_info.public_url or file_info.url
        logger.info(f"Avatar uploaded successfully to: {public_url}")

        # Return the public URL
        return public_url


def create_user_from_social(
    *,
    session: Session,
    provider: str,
    provider_user_id: str,
    provider_email: str | None = None,
    provider_name: str | None = None,
    avatar_url: str | None = None,
) -> User:
    """Create a new user from social login information"""

    # Generate a temporary email if not provided
    email = provider_email or f"{provider_user_id}@{provider}.local"

    # Create user with minimal info
    user_create = UserCreate(
        email=email,
        password="social_login_no_password",  # Temporary password
        full_name=provider_name,
    )

    # Calculate trial expiry date: current date + 7 days, rounded to 00:00 of the next day
    trial_end_date = datetime.now() + timedelta(days=7)
    trial_expired_at = trial_end_date.replace(hour=0, minute=0, second=0, microsecond=0)

    # Prepare user data with avatar URL if available
    user_data = {
        "hashed_password": get_password_hash(user_create.password),
        "trial_expired_at": trial_expired_at,
        "email_verified": True if provider_email else False,
        "last_login_provider": provider,
    }

    # Add avatar URL if provided
    if avatar_url:
        user_data["avatar_url"] = avatar_url

    user = User.model_validate(user_create, update=user_data)

    session.add(user)
    session.commit()
    session.refresh(user)

    return user
