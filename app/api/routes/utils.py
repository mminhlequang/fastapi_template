from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from pydantic.networks import EmailStr
import uuid

from app.api.deps import get_current_active_superuser, SessionDep, CurrentUser
from app.schemas.base import Message
from app.utils.sent_email import generate_test_email, send_email
from app.utils.firebase_messaging import fcm_service
from app.models import UserDeviceToken
from sqlmodel import select

router = APIRouter(prefix="/utils", tags=["utils"])


# ========== Email Testing ==========

@router.post(
    "/test-email/",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=201,
)
def test_email(email_to: EmailStr) -> Message:
    """
    Test emails.
    """
    email_data = generate_test_email(email_to=email_to)
    send_email(
        email_to=email_to,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return Message(message="Test email sent")


@router.get("/health-check/")
async def health_check() -> bool:
    return True


# ========== Firebase Messaging Testing ==========

class FCMTestRequest(BaseModel):
    """Request schema for FCM notification test."""
    user_id: uuid.UUID
    provider: str = "fcm"  # fcm, apns, firebase
    title: str
    body: str
    data: dict | None = None


class FCMTestResponse(BaseModel):
    """Response schema for FCM notification test."""
    success: bool
    message: str
    message_id: str | None = None
    tokens_sent: int = 0


@router.post(
    "/test-fcm/",
    response_model=FCMTestResponse,
    dependencies=[Depends(get_current_active_superuser)],
    status_code=200,
    summary="Test Firebase Cloud Messaging",
    description="Send test FCM notification to user's devices",
)
async def test_fcm_notification(
    request: FCMTestRequest,
    session: SessionDep,
) -> FCMTestResponse:
    """
    Test Firebase Cloud Messaging notification.
    
    Send a test notification to all active devices of a specific user.
    Admin only endpoint.
    
    Example:
        ```json
        {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "provider": "fcm",
            "title": "Test Notification",
            "body": "This is a test FCM notification",
            "data": {
                "action": "open_app",
                "target": "home"
            }
        }
        ```
    """
    try:
        # Get all active device tokens for the user
        statement = select(UserDeviceToken).where(
            UserDeviceToken.user_id == request.user_id,
            UserDeviceToken.is_active == True,
            UserDeviceToken.provider == request.provider,
        )
        tokens = session.exec(statement).all()

        if not tokens:
            return FCMTestResponse(
                success=False,
                message=f"No active {request.provider} tokens found for user",
                tokens_sent=0,
            )

        # Extract device tokens
        device_tokens = [token.device_token for token in tokens]

        # Send FCM notification
        if len(device_tokens) == 1:
            message_id = fcm_service.send_to_device(
                device_token=device_tokens[0],
                title=request.title,
                body=request.body,
                data=request.data,
            )
            
            return FCMTestResponse(
                success=message_id is not None,
                message="FCM notification sent successfully" if message_id else "Failed to send FCM notification",
                message_id=message_id,
                tokens_sent=1 if message_id else 0,
            )
        else:
            result = fcm_service.send_to_multiple_devices(
                device_tokens=device_tokens,
                title=request.title,
                body=request.body,
                data=request.data,
            )
            
            return FCMTestResponse(
                success=result["failed"] == 0,
                message=f"Sent to {result['successful']} devices, {result['failed']} failed",
                tokens_sent=result["successful"],
            )

    except Exception as e:
        return FCMTestResponse(
            success=False,
            message=f"Error sending FCM notification: {str(e)}",
            tokens_sent=0,
        )

