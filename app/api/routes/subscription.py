from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, func
from sqlalchemy.orm import joinedload
from app.models import (
    SubscriptionPlan,
    BillingInfo,
    UserSubscription,
    Payment,
    User,
)
from app.api.deps import get_db, get_current_active_superuser, get_current_user
from typing import List
import uuid
from app.schemas.base import ListResponse
from app.schemas.subscription import (
    UserSubscriptionResponse,
    SubscriptionPlanResponse,
    BillingInfoResponse,
    PaymentResponse,
)

router = APIRouter(prefix="/subscription", tags=["subscription"])


# ---------------------- SubscriptionPlan CRUD ----------------------
@router.get(
    "/subscription-plans/", response_model=ListResponse[SubscriptionPlanResponse]
)
def list_subscription_plans(
    db: Session = Depends(get_db),
    offset: int = 0,
    limit: int = 100,
):
    """List all subscription plans (with pagination)"""
    count_statement = select(func.count()).select_from(SubscriptionPlan)
    count = db.exec(count_statement).one()
    statement = select(SubscriptionPlan).offset(offset).limit(limit)
    plans = db.exec(statement).all()
    return ListResponse(data=plans, count=count)


@router.get("/subscription-plans/{plan_id}", response_model=SubscriptionPlan)
def get_subscription_plan(
    plan_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_superuser),
):
    """Get a subscription plan by ID (admin only)"""
    plan = db.get(SubscriptionPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="SubscriptionPlan not found")
    return plan


@router.post(
    "/subscription-plans/",
    response_model=SubscriptionPlan,
    status_code=status.HTTP_201_CREATED,
)
def create_subscription_plan(
    plan_in: SubscriptionPlan,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_superuser),
):
    """Create a new subscription plan (admin only)"""
    db.add(plan_in)
    db.commit()
    db.refresh(plan_in)
    return plan_in


@router.put("/subscription-plans/{plan_id}", response_model=SubscriptionPlan)
def update_subscription_plan(
    plan_id: uuid.UUID,
    plan_in: SubscriptionPlan,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_superuser),
):
    """Update a subscription plan (admin only)"""
    plan = db.get(SubscriptionPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="SubscriptionPlan not found")
    for field, value in plan_in.dict(exclude_unset=True).items():
        setattr(plan, field, value)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/subscription-plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription_plan(
    plan_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_superuser),
):
    """Delete a subscription plan (admin only)"""
    plan = db.get(SubscriptionPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="SubscriptionPlan not found")
    db.delete(plan)
    db.commit()
    return None


# ---------------------- BillingInfo Read/Delete ----------------------
@router.get("/billing-infos/", response_model=ListResponse[BillingInfoResponse])
def list_billing_infos(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_superuser),
    offset: int = 0,
    limit: int = 100,
):
    """List all billing infos (admin only, with pagination)"""
    count_statement = select(func.count()).select_from(BillingInfo)
    count = db.exec(count_statement).one()
    statement = select(BillingInfo).offset(offset).limit(limit)
    infos = db.exec(statement).all()
    return ListResponse(data=infos, count=count)


@router.get("/billing-infos/{billing_id}", response_model=BillingInfo)
def get_billing_info(
    billing_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_superuser),
):
    """Get a billing info by ID (admin only)"""
    billing = db.get(BillingInfo, billing_id)
    if not billing:
        raise HTTPException(status_code=404, detail="BillingInfo not found")
    return billing


@router.delete("/billing-infos/{billing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_billing_info(
    billing_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_superuser),
):
    """Delete a billing info (admin only)"""
    billing = db.get(BillingInfo, billing_id)
    if not billing:
        raise HTTPException(status_code=404, detail="BillingInfo not found")
    db.delete(billing)
    db.commit()
    return None


# ---------------------- UserSubscription Read/Delete ----------------------
@router.get("/user-subscriptions/current", response_model=UserSubscriptionResponse)
def get_current_user_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the current user's subscription"""
    statement = (
        select(UserSubscription)
        .options(
            joinedload(UserSubscription.user),
            joinedload(UserSubscription.subscription_plan),
            joinedload(UserSubscription.payments),
        )
        .where(UserSubscription.user_id == current_user.id)
    )
    subscription = db.exec(statement).unique().first()
    if not subscription:
        raise HTTPException(status_code=404, detail="UserSubscription not found")
    return subscription


@router.get(
    "/user-subscriptions/", response_model=ListResponse[UserSubscriptionResponse]
)
def list_user_subscriptions(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_superuser),
    offset: int = 0,
    limit: int = 100,
):
    """List all user subscriptions (admin only, with pagination)"""
    count_statement = select(func.count()).select_from(UserSubscription)
    count = db.exec(count_statement).one()
    statement = (
        select(UserSubscription)
        .options(
            joinedload(UserSubscription.user),
            joinedload(UserSubscription.subscription_plan),
            joinedload(UserSubscription.payments),
        )
        .offset(offset)
        .limit(limit)
    )
    subscriptions = db.exec(statement).unique().all()
    return ListResponse(data=subscriptions, count=count)


@router.get("/user-subscriptions/{subscription_id}", response_model=UserSubscription)
def get_user_subscription(
    subscription_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_superuser),
):
    """Get a user subscription by ID (admin only)"""
    subscription = db.get(UserSubscription, subscription_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="UserSubscription not found")
    return subscription


@router.delete(
    "/user-subscriptions/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_user_subscription(
    subscription_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_superuser),
):
    """Delete a user subscription (admin only)"""
    subscription = db.get(UserSubscription, subscription_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="UserSubscription not found")
    db.delete(subscription)
    db.commit()
    return None


# ---------------------- Payment Read/Delete ----------------------
@router.get("/payments/", response_model=ListResponse[PaymentResponse])
def list_payments(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_superuser),
    offset: int = 0,
    limit: int = 100,
):
    """List all payments (admin only, with pagination)"""
    count_statement = select(func.count()).select_from(Payment)
    count = db.exec(count_statement).one()
    statement = (
        select(Payment)
        .options(
            joinedload(Payment.user),
            joinedload(Payment.user_subscription),
        )
        .offset(offset)
        .limit(limit)
    )
    payments = db.exec(statement).unique().all()
    return ListResponse(data=payments, count=count)


@router.get("/payments/{payment_id}", response_model=Payment)
def get_payment(
    payment_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_superuser),
):
    """Get a payment by ID (admin only)"""
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.delete("/payments/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment(
    payment_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_superuser),
):
    """Delete a payment (admin only)"""
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    db.delete(payment)
    db.commit()
    return None
