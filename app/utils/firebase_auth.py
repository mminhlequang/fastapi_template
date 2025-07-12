import json
import logging
import os
from typing import Optional, Dict, Any

import firebase_admin
from firebase_admin import auth, credentials
from firebase_admin.auth import UserRecord

from app.core.config import settings

logger = logging.getLogger(__name__)


# Initialize Firebase Admin SDK
def initialize_firebase():
    """Initialize Firebase Admin SDK with service account file"""
    try:
        if not firebase_admin._apps:
            # Check if service account file exists
            service_account_path = settings.FIREBASE_SERVICE_ACCOUNT_FILE
            if not os.path.exists(service_account_path):
                logger.warning(
                    f"Firebase service account file not found: {service_account_path}"
                )
                return False

            # Initialize with service account file
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully")
            return True
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
        return False


def verify_firebase_token(id_token: str) -> Optional[Dict[str, Any]]:
    """Verify Firebase ID token and return user info"""
    try:
        if not firebase_admin._apps:
            if not initialize_firebase():
                return None

        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        logger.error(f"Failed to verify Firebase token: {e}")
        return None


def get_firebase_user_info(uid: str) -> Optional[UserRecord]:
    """Get Firebase user information by UID"""
    try:
        if not firebase_admin._apps:
            if not initialize_firebase():
                return None

        user_record = auth.get_user(uid)
        return user_record
    except Exception as e:
        logger.error(f"Failed to get Firebase user info: {e}")
        return None


def extract_phone_from_firebase_token(token_data: Dict[str, Any]) -> Optional[str]:
    """Extract phone number from Firebase token data"""
    try:
        # Check if phone number exists in token
        if "phone_number" in token_data:
            return token_data["phone_number"]

        # Check if phone number exists in user info
        if "firebase" in token_data and "identities" in token_data["firebase"]:
            identities = token_data["firebase"]["identities"]
            if "phone" in identities and identities["phone"]:
                return identities["phone"][0]

        return None
    except Exception as e:
        logger.error(f"Failed to extract phone from Firebase token: {e}")
        return None


def is_firebase_phone_provider(token_data: Dict[str, Any]) -> bool:
    """Check if the token is from Firebase Phone provider"""
    try:
        # Check if sign_in_provider is phone
        if "firebase" in token_data and "sign_in_provider" in token_data["firebase"]:
            return token_data["firebase"]["sign_in_provider"] == "phone"

        # Alternative check for phone authentication
        if "phone_number" in token_data:
            return True

        return False
    except Exception as e:
        logger.error(f"Failed to check Firebase provider: {e}")
        return False
