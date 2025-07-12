from typing import List, Optional, ForwardRef
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import datetime
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
    role: str = Field(default="owner", max_length=32)
    lemon_customer_id: str | None = Field(default=None, max_length=255)
    is_superuser: bool = False
    ref_code: str | None = Field(default=None, max_length=32, unique=True, index=True)
    request_delete_at: datetime | None = None
    inactive_at: datetime | None = None
    trial_expired_at: datetime | None = None
    email_verified: bool | None = None
    last_login_provider: str | None = Field(default=None, max_length=50)


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
    role: str | None = Field(default=None, max_length=32)
    lemon_customer_id: str | None = Field(default=None, max_length=255)
    is_superuser: bool | None = None
    ref_code: str | None = Field(default=None, max_length=32)
    request_delete_at: datetime | None = None
    inactive_at: datetime | None = None
    trial_expired_at: datetime | None = None
    email_verified: bool | None = None
    last_login_provider: str | None = Field(default=None, max_length=50)


class UserUpdateMe(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)
    phone_number: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    website_url: str | None = None


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


# Update forward references
User.model_rebuild()
