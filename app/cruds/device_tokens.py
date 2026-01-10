"""
CRUD operations for device tokens.
"""

import uuid
from datetime import datetime
from sqlmodel import Session, select

from app.models import UserDeviceToken


class DeviceTokenCRUD:
    """CRUD operations for user device tokens."""

    @staticmethod
    def register_token(
        db: Session,
        user_id: uuid.UUID,
        provider: str,
        device_token: str,
        device_type: str,
        device_name: str | None = None,
        device_id: str | None = None,
        app_version: str | None = None,
        os_version: str | None = None,
    ) -> UserDeviceToken:
        """
        Register a new device token or update existing one.
        
        If device already has a token for this provider, it will be updated.
        """
        # Check for existing token from same device/provider
        existing = db.exec(
            select(UserDeviceToken).where(
                UserDeviceToken.user_id == user_id,
                UserDeviceToken.provider == provider,
                UserDeviceToken.device_id == device_id,
            )
        ).first()

        if existing:
            # Update existing token
            existing.device_token = device_token
            existing.device_type = device_type
            existing.device_name = device_name
            existing.app_version = app_version
            existing.os_version = os_version
            existing.is_active = True
            existing.updated_at = datetime.utcnow()
            db.add(existing)
            db.commit()
            db.refresh(existing)
            return existing

        # Create new token
        token = UserDeviceToken(
            user_id=user_id,
            provider=provider,
            device_token=device_token,
            device_type=device_type,
            device_name=device_name,
            device_id=device_id,
            app_version=app_version,
            os_version=os_version,
        )
        db.add(token)
        db.commit()
        db.refresh(token)
        return token

    @staticmethod
    def get_token_by_id(db: Session, token_id: uuid.UUID) -> UserDeviceToken | None:
        """Get a token by ID."""
        return db.exec(
            select(UserDeviceToken).where(UserDeviceToken.id == token_id)
        ).first()

    @staticmethod
    def get_user_tokens(
        db: Session,
        user_id: uuid.UUID,
        is_active: bool | None = None,
    ) -> list[UserDeviceToken]:
        """Get all tokens for a user."""
        query = select(UserDeviceToken).where(
            UserDeviceToken.user_id == user_id
        )

        if is_active is not None:
            query = query.where(UserDeviceToken.is_active == is_active)

        return db.exec(query).all()

    @staticmethod
    def get_user_active_tokens(db: Session, user_id: uuid.UUID) -> list[UserDeviceToken]:
        """Get all active tokens for a user."""
        return DeviceTokenCRUD.get_user_tokens(db, user_id, is_active=True)

    @staticmethod
    def get_tokens_by_provider(
        db: Session,
        user_id: uuid.UUID,
        provider: str,
    ) -> list[UserDeviceToken]:
        """Get all tokens for a user by provider."""
        return db.exec(
            select(UserDeviceToken).where(
                UserDeviceToken.user_id == user_id,
                UserDeviceToken.provider == provider,
            )
        ).all()

    @staticmethod
    def get_tokens_by_device_type(
        db: Session,
        user_id: uuid.UUID,
        device_type: str,
    ) -> list[UserDeviceToken]:
        """Get all tokens for a user by device type."""
        return db.exec(
            select(UserDeviceToken).where(
                UserDeviceToken.user_id == user_id,
                UserDeviceToken.device_type == device_type,
            )
        ).all()

    @staticmethod
    def deactivate_token(db: Session, token_id: uuid.UUID) -> UserDeviceToken | None:
        """Deactivate (soft delete) a token."""
        token = DeviceTokenCRUD.get_token_by_id(db, token_id)
        if token:
            token.is_active = False
            token.updated_at = datetime.utcnow()
            db.add(token)
            db.commit()
            db.refresh(token)
        return token

    @staticmethod
    def delete_token(db: Session, token_id: uuid.UUID) -> bool:
        """Delete a token permanently."""
        token = DeviceTokenCRUD.get_token_by_id(db, token_id)
        if token:
            db.delete(token)
            db.commit()
            return True
        return False

    @staticmethod
    def mark_token_used(db: Session, token_id: uuid.UUID) -> UserDeviceToken | None:
        """Mark a token as used (update last_used_at)."""
        token = DeviceTokenCRUD.get_token_by_id(db, token_id)
        if token:
            token.last_used_at = datetime.utcnow()
            db.add(token)
            db.commit()
            db.refresh(token)
        return token

    @staticmethod
    def mark_token_verified(db: Session, token_id: uuid.UUID) -> UserDeviceToken | None:
        """Mark a token as verified."""
        token = DeviceTokenCRUD.get_token_by_id(db, token_id)
        if token:
            token.is_verified = True
            token.updated_at = datetime.utcnow()
            db.add(token)
            db.commit()
            db.refresh(token)
        return token

    @staticmethod
    def cleanup_expired_tokens(db: Session) -> int:
        """
        Delete all expired tokens.
        Background job - should be scheduled regularly.
        
        Returns:
            Number of tokens deleted
        """
        expired_tokens = db.exec(
            select(UserDeviceToken).where(
                UserDeviceToken.expires_at < datetime.utcnow()
            )
        ).all()

        count = len(expired_tokens)
        for token in expired_tokens:
            db.delete(token)

        db.commit()
        return count

    @staticmethod
    def cleanup_inactive_tokens(
        db: Session,
        days: int = 90,
    ) -> int:
        """
        Delete inactive tokens (not used for X days).
        Background job - should be scheduled regularly.
        
        Args:
            db: Database session
            days: Delete tokens not used for this many days (default: 90)
        
        Returns:
            Number of tokens deleted
        """
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        inactive_tokens = db.exec(
            select(UserDeviceToken).where(
                UserDeviceToken.is_active == True,
                UserDeviceToken.last_used_at < cutoff_date,
            )
        ).all()

        count = len(inactive_tokens)
        for token in inactive_tokens:
            token.is_active = False
            db.add(token)

        db.commit()
        return count

    @staticmethod
    def get_statistics(db: Session, user_id: uuid.UUID) -> dict:
        """Get statistics about user's device tokens."""
        tokens = DeviceTokenCRUD.get_user_tokens(db, user_id)
        
        active_tokens = [t for t in tokens if t.is_active]
        verified_tokens = [t for t in tokens if t.is_verified]
        
        by_device_type = {}
        by_provider = {}
        
        for token in tokens:
            if token.device_type not in by_device_type:
                by_device_type[token.device_type] = 0
            by_device_type[token.device_type] += 1
            
            if token.provider not in by_provider:
                by_provider[token.provider] = 0
            by_provider[token.provider] += 1

        return {
            "total_tokens": len(tokens),
            "active_tokens": len(active_tokens),
            "verified_tokens": len(verified_tokens),
            "by_device_type": by_device_type,
            "by_provider": by_provider,
        }
