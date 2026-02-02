from typing import List, Optional, ForwardRef
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import datetime, date
import uuid
from app.models import (
    BillingInfo,
    Payment,
)
from app.schemas.subscription import (
    UserSubscriptionResponse,
    PaymentResponse,
    BillingInfoResponse,
)

# Forward references for circular dependencies
UserRef = ForwardRef("User")
SubscriptionPlanRef = ForwardRef("SubscriptionPlan")
UserSubscriptionRef = ForwardRef("UserSubscription")
PaymentRef = ForwardRef("Payment")
BillingInfoRef = ForwardRef("BillingInfo")


# Shared properties
class UserBase(BaseModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    full_name: str | None = Field(default=None, max_length=255)
    phone_number: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    website_url: str | None = None
    avatar_url: str | None = None
    lemon_customer_id: str | None = Field(default=None, max_length=255)
    is_superuser: bool = False
    ref_code: str | None = Field(default=None, max_length=32, unique=True, index=True)
    request_delete_at: datetime | None = None
    inactive_at: datetime | None = None
    trial_expired_at: datetime | None = None
    email_verified: bool | None = None
    last_login_provider: str | None = Field(default=None, max_length=50)
    country_code: str | None = Field(default=None, max_length=3)  # ISO 3166-1 alpha-2 (e.g. "VN", "US")
    locale: str | None = Field(default="en", max_length=10)  # e.g. "en", "vi", "en-US"
    timezone: str | None = Field(default=None, max_length=50)  # e.g. "Asia/Ho_Chi_Minh"
    currency: str | None = Field(default=None, max_length=3)  # ISO 4217, e.g. "USD", "VND"
    gender: str | None = Field(default=None, max_length=20)  # e.g. "male", "female", "other"
    birth_date: date | None = None
    bio: str | None = Field(default=None, max_length=500)
    job_title: str | None = Field(default=None, max_length=255)


class UserPublic(UserBase):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    model_config = ConfigDict(from_attributes=True)


class User(UserBase):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    # Relationships
    billing_info: Optional[BillingInfoResponse] = None
    subscriptions: List[UserSubscriptionResponse] = []
    social_accounts: List["SocialAccountResponse"] = []

    model_config = ConfigDict(from_attributes=True)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=40)


class UserRegister(BaseModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=40)
    full_name: str | None = Field(default=None, max_length=255)
    phone_number: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=40)
    full_name: str | None = Field(default=None, max_length=255)
    phone_number: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    website_url: str | None = None
    lemon_customer_id: str | None = Field(default=None, max_length=255)
    is_superuser: bool | None = None
    ref_code: str | None = Field(default=None, max_length=32)
    request_delete_at: datetime | None = None
    inactive_at: datetime | None = None
    trial_expired_at: datetime | None = None
    email_verified: bool | None = None
    last_login_provider: str | None = Field(default=None, max_length=50)
    country_code: str | None = Field(default=None, max_length=3)
    locale: str | None = Field(default=None, max_length=10)
    timezone: str | None = Field(default=None, max_length=50)
    currency: str | None = Field(default=None, max_length=3)
    gender: str | None = Field(default=None, max_length=20)
    birth_date: date | None = None
    bio: str | None = Field(default=None, max_length=500)
    job_title: str | None = Field(default=None, max_length=255)


class UserUpdateMe(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)
    phone_number: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    website_url: str | None = None
    country_code: str | None = Field(default=None, max_length=3)
    locale: str | None = Field(default=None, max_length=10)
    timezone: str | None = Field(default=None, max_length=50)
    currency: str | None = Field(default=None, max_length=3)
    gender: str | None = Field(default=None, max_length=20)
    birth_date: date | None = None
    bio: str | None = Field(default=None, max_length=500)
    job_title: str | None = Field(default=None, max_length=255)


class UpdatePassword(BaseModel):
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


# Properties to return via API, id is always required
class UserResponse(User):
    billing_info: Optional[BillingInfoResponse] = None
    subscriptions: List[UserSubscriptionResponse] = []


# Contents of JWT token
class TokenPayload(BaseModel):
    sub: str | None = None


class NewPassword(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)


# JSON payload containing access token and refresh token
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


# Payload nhận refresh token từ client
class RefreshTokenRequest(BaseModel):
    refresh_token: str


# Social login request/response schemas
class SocialLoginRequest(BaseModel):
    provider: str = Field(..., pattern="^(facebook|google|apple)$")
    access_token: str  # Token từ client-side OAuth


class SocialAccountResponse(BaseModel):
    id: uuid.UUID
    provider: str
    provider_email: str | None
    linked_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SocialLinkRequest(BaseModel):
    provider: str = Field(..., pattern="^(facebook|google|apple)$")
    access_token: str  # Token từ client-side OAuth
    

class NotificationTokenRegisterRequest(BaseModel):
    """Request to register a new device token."""
    
    provider: str = Field(..., description="Provider: fcm, apns, firebase, onesignal, web_push")
    device_token: str = Field(..., description="Token from provider")
    device_type: str = Field(..., description="Device type: ios, android, web, macos, windows")
    device_name: Optional[str] = Field(None, description="User-friendly device name")
    device_id: Optional[str] = Field(None, description="Hardware device identifier")
    app_version: Optional[str] = Field(None, description="App version")
    os_version: Optional[str] = Field(None, description="OS version")
 

class NotificationTokenResponse(BaseModel):
    """Response with device token data."""
    
    id: uuid.UUID
    provider: str
    device_type: str
    device_name: Optional[str]
    is_active: bool
    is_verified: bool
    last_used_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# OTP Email Update schemas
class RequestUpdateEmailOTP(BaseModel):
    """Request to send OTP for email update"""

    new_email: EmailStr


class VerifyUpdateEmailOTP(BaseModel):
    """Verify OTP and get confirmation token (Step 2 of 3)"""

    new_email: EmailStr
    otp_code: str = Field(min_length=6, max_length=6, pattern="^[0-9]{6}$")


class ConfirmUpdateEmail(BaseModel):
    """Confirm email update using token from OTP verification (Step 3 of 3)"""

    confirmation_token: str
    new_email: EmailStr


class EmailUpdateTokenResponse(BaseModel):
    """Response containing confirmation token after OTP verification"""

    confirmation_token: str
    message: str = (
        "OTP verified successfully. Use the confirmation_token to update your email."
    )


# Phone update schemas
class RequestUpdatePhoneCheck(BaseModel):
    """Request payload to check new phone availability"""

    new_phone_number: str = Field(min_length=5, max_length=20)


class PhoneAvailabilityResponse(BaseModel):
    """Response indicating whether phone number is available"""

    is_available: bool


class ConfirmUpdatePhone(BaseModel):
    """Confirm phone update using Firebase ID token"""

    new_phone_number: str = Field(min_length=5, max_length=20)
    id_token: str  # Firebase ID token from phone authentication


# Update forward references
User.model_rebuild()

