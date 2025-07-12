from typing import List, Optional, ForwardRef, Dict, Any
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Forward references for circular dependencies
SubscriptionPlanRef = ForwardRef("SubscriptionPlan")
UserSubscriptionRef = ForwardRef("UserSubscription")
PaymentRef = ForwardRef("Payment")
BillingInfoRef = ForwardRef("BillingInfo")


class UserPublic(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    full_name: str | None = Field(default=None, max_length=255)
    phone_number: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    website_url: str | None = None
    avatar_url: str | None = None
    role: str = Field(default="owner", max_length=32)
    lemon_customer_id: str | None = Field(default=None, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    has_trial_activated: bool = Field(default=False)
    ref_code: str | None = Field(default=None, max_length=32, unique=True, index=True)

    model_config = ConfigDict(from_attributes=True)


class SubscriptionPlan(BaseModel):
    """Schema for subscription plans"""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    code: str = Field(max_length=64, unique=True)
    name: str = Field(max_length=255)
    description: str | None = None
    price: int
    currency: str = Field(default="usd", max_length=16)
    interval: str = Field(default="month", max_length=16)
    features: Dict[str, Any] | None = None
    lemon_product_id: str | None = Field(default=None, max_length=255)
    lemon_variant_id: str | None = Field(default=None, max_length=255)
    
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    model_config = ConfigDict(from_attributes=True)


class BillingInfo(BaseModel):
    """Schema for user billing information"""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    company_name: str = Field(max_length=255)
    tax_code: str | None = Field(default=None, max_length=255)
    address: str
    email: str = Field(max_length=255)
    phone_number: str | None = Field(default=None, max_length=255)
    country: str = Field(default="VN", max_length=32)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    model_config = ConfigDict(from_attributes=True)


class UserSubscription(BaseModel):
    """Schema for user subscription details"""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    subscription_plan_id: uuid.UUID
    lemon_subscription_id: str | None = Field(default=None, max_length=255)
    status: str = Field(max_length=32)
    start_date: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    canceled_at: datetime | None = None
    trial_end: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    model_config = ConfigDict(from_attributes=True)


class Payment(BaseModel):
    """Schema for payment transactions"""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    user_subscription_id: uuid.UUID
    lemon_order_id: str | None = None
    amount_in_cents: int | None = None
    currency: str = Field(default="usd", max_length=16)
    status: str = Field(max_length=32)
    paid_at: datetime | None = None
    receipt_url: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    model_config = ConfigDict(from_attributes=True)


class SubscriptionPlanResponse(SubscriptionPlan):
    """Response model for subscription plan with relationships"""

    user_subscriptions: List[UserSubscription] = []


class UserSubscriptionResponse(UserSubscription):
    """Response model for user subscription with relationships"""

    user: Optional[UserPublic] = None
    subscription_plan: Optional[SubscriptionPlan] = None
    payments: List[Payment] = []


class PaymentResponse(Payment):
    """Response model for payment with relationships"""

    user: Optional[UserPublic] = None
    subscription: Optional[UserSubscription] = None
    billing_info: Optional[BillingInfo] = None


class BillingInfoResponse(BillingInfo):
    """Response model for billing info with relationships"""

    user: Optional[UserPublic] = None


# Update forward references
SubscriptionPlan.model_rebuild()
UserSubscription.model_rebuild()
Payment.model_rebuild()
BillingInfo.model_rebuild()
