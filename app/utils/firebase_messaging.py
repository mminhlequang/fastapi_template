"""
Firebase Cloud Messaging (FCM) utilities for sending push notifications.

Integration with Firebase Admin SDK to send notifications to device tokens.
"""

import logging
from typing import Optional, Any
import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)


class FirebaseMessagingService:
    """Service for sending push notifications via Firebase Cloud Messaging."""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def initialize(cls, credentials_path: str) -> None:
        """
        Initialize Firebase Admin SDK.
        
        Args:
            credentials_path: Path to Firebase service account JSON file
        
        Raises:
            FileNotFoundError: If credentials file not found
            ValueError: If Firebase already initialized
        """
        if cls._initialized:
            logger.warning("Firebase already initialized")
            return

        try:
            cred = credentials.Certificate(credentials_path)
            firebase_admin.initialize_app(cred)
            cls._initialized = True
            logger.info("Firebase initialized successfully")
        except FileNotFoundError:
            logger.error(f"Firebase credentials file not found: {credentials_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            raise

    @staticmethod
    def send_to_device(
        device_token: str,
        title: str,
        body: str,
        data: Optional[dict[str, str]] = None,
        badge: Optional[str] = None,
        sound: str = "default",
        priority: str = "high",
    ) -> Optional[str]:
        """
        Send a notification to a single device.
        
        Args:
            device_token: FCM device token
            title: Notification title
            body: Notification body/message
            data: Optional custom data dictionary (keys and values must be strings)
            badge: Optional badge number (Android)
            sound: Notification sound ("default" or custom sound name)
            priority: "high" (default) or "normal"
        
        Returns:
            Message ID if successful, None if failed
        
        Example:
            ```python
            service = FirebaseMessagingService()
            message_id = service.send_to_device(
                device_token="token123...",
                title="Hello",
                body="This is a test notification",
                data={"order_id": "123", "action": "open_app"}
            )
            ```
        """
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                android=messaging.AndroidConfig(
                    priority=priority,
                    notification=messaging.AndroidNotification(
                        sound=sound,
                        badge=badge,
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound=sound,
                            badge=int(badge) if badge else None,
                            mutable_content=True,
                        ),
                    ),
                ) if sound else None,
                webpush=messaging.WebpushConfig(
                    data=data or {},
                    notification=messaging.WebpushNotification(
                        title=title,
                        body=body,
                        icon="/icons/notification-icon.png",
                    ),
                ),
            )

            response = messaging.send(message, dry_run=False)
            logger.info(f"Message sent successfully: {response}")
            return response

        except Exception as e:
            logger.error(f"Failed to send message to {device_token}: {e}")
            return None

    @staticmethod
    def send_to_multiple_devices(
        device_tokens: list[str],
        title: str,
        body: str,
        data: Optional[dict[str, str]] = None,
        badge: Optional[str] = None,
        sound: str = "default",
        priority: str = "high",
    ) -> dict[str, Any]:
        """
        Send a notification to multiple devices (batch).
        
        Args:
            device_tokens: List of FCM device tokens
            title: Notification title
            body: Notification body/message
            data: Optional custom data dictionary
            badge: Optional badge number
            sound: Notification sound
            priority: "high" or "normal"
        
        Returns:
            Dictionary with:
            - successful: Number of successfully sent messages
            - failed: Number of failed messages
            - message_ids: List of message IDs
            - errors: List of errors for failed sends
        
        Example:
            ```python
            result = service.send_to_multiple_devices(
                device_tokens=["token1...", "token2...", "token3..."],
                title="Promotion",
                body="50% off this weekend!",
            )
            print(f"Sent: {result['successful']}, Failed: {result['failed']}")
            ```
        """
        result = {
            "successful": 0,
            "failed": 0,
            "message_ids": [],
            "errors": [],
        }

        for token in device_tokens:
            try:
                message_id = FirebaseMessagingService.send_to_device(
                    device_token=token,
                    title=title,
                    body=body,
                    data=data,
                    badge=badge,
                    sound=sound,
                    priority=priority,
                )
                if message_id:
                    result["successful"] += 1
                    result["message_ids"].append(message_id)
                else:
                    result["failed"] += 1
            except Exception as e:
                result["failed"] += 1
                result["errors"].append({"token": token, "error": str(e)})
                logger.error(f"Error sending to {token}: {e}")

        logger.info(
            f"Batch send complete: {result['successful']} successful, "
            f"{result['failed']} failed"
        )
        return result

    @staticmethod
    def send_to_topic(
        topic: str,
        title: str,
        body: str,
        data: Optional[dict[str, str]] = None,
        badge: Optional[str] = None,
        sound: str = "default",
        priority: str = "high",
    ) -> Optional[str]:
        """
        Send a notification to all devices subscribed to a topic.
        
        Args:
            topic: Topic name (e.g., "promotions", "updates", "orders")
            title: Notification title
            body: Notification body/message
            data: Optional custom data dictionary
            badge: Optional badge number
            sound: Notification sound
            priority: "high" or "normal"
        
        Returns:
            Message ID if successful, None if failed
        
        Example:
            ```python
            service.send_to_topic(
                topic="promotions",
                title="Flash Sale",
                body="Limited time offer!",
            )
            ```
        """
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                topic=topic,
                android=messaging.AndroidConfig(
                    priority=priority,
                    notification=messaging.AndroidNotification(
                        sound=sound,
                        badge=badge,
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound=sound,
                            badge=int(badge) if badge else None,
                        ),
                    ),
                ) if sound else None,
            )

            response = messaging.send(message)
            logger.info(f"Topic message sent successfully: {response}")
            return response

        except Exception as e:
            logger.error(f"Failed to send topic message to {topic}: {e}")
            return None

    @staticmethod
    def subscribe_to_topic(
        device_tokens: list[str],
        topic: str,
    ) -> bool:
        """
        Subscribe device(s) to a topic.
        
        Args:
            device_tokens: List of device tokens to subscribe
            topic: Topic name
        
        Returns:
            True if successful, False otherwise
        
        Example:
            ```python
            service.subscribe_to_topic(
                device_tokens=["token1...", "token2..."],
                topic="promotions"
            )
            ```
        """
        try:
            messaging.make_topic_management_response(
                messaging.TopicMgtResponse(
                    messaging.subscribe_to_topic(device_tokens, topic)
                )
            )
            logger.info(f"Subscribed {len(device_tokens)} devices to topic: {topic}")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to topic {topic}: {e}")
            return False

    @staticmethod
    def unsubscribe_from_topic(
        device_tokens: list[str],
        topic: str,
    ) -> bool:
        """
        Unsubscribe device(s) from a topic.
        
        Args:
            device_tokens: List of device tokens to unsubscribe
            topic: Topic name
        
        Returns:
            True if successful, False otherwise
        """
        try:
            messaging.unsubscribe_from_topic(device_tokens, topic)
            logger.info(f"Unsubscribed {len(device_tokens)} devices from topic: {topic}")
            return True
        except Exception as e:
            logger.error(f"Failed to unsubscribe from topic {topic}: {e}")
            return False

    @staticmethod
    def test_token(device_token: str) -> bool:
        """
        Test if a device token is valid by attempting to send a dry run.
        
        Args:
            device_token: Device token to test
        
        Returns:
            True if token is valid, False otherwise
        """
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title="Test",
                    body="Test notification",
                ),
            )
            # Use target_token and dry_run=True
            response = messaging.send(
                messaging.Message(
                    notification=messaging.Notification(
                        title="Test",
                        body="Test",
                    ),
                    token=device_token,
                ),
                dry_run=True,
            )
            logger.info(f"Token validation passed: {device_token}")
            return True
        except Exception as e:
            logger.warning(f"Invalid token {device_token}: {e}")
            return False


# Global instance
fcm_service = FirebaseMessagingService()


def initialize_firebase(credentials_path: str = "firebase-service-account.json") -> None:
    """
    Initialize Firebase Messaging service.
    
    Call this once during app startup.
    
    Example:
        ```python
        # In app/main.py
        from app.utils.firebase_messaging import initialize_firebase
        
        initialize_firebase("path/to/firebase-service-account.json")
        ```
    """
    fcm_service.initialize(credentials_path)
