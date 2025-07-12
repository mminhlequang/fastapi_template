from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session, select
from app.models import User, SubscriptionPlan, UserSubscription, Payment
from app.api.deps import get_session, get_current_user
from pydantic import BaseModel
import httpx
import os
import hmac
import hashlib
import base64
from app.core.config import settings
import logging
import datetime
from dateutil import parser as date_parser

router = APIRouter(prefix="/checkout", tags=["checkout"])
logger = logging.getLogger("checkout")


# === 1. User chooses a plan and clicks "Buy" ===
class CheckoutRequest(BaseModel):
    plan_code: str


class CheckoutResponse(BaseModel):
    checkout_url: str


@router.post("/", response_model=CheckoutResponse)
def create_checkout_session(
    data: CheckoutRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    logger.info(
        f"[POST /] User {current_user.id} ({current_user.email}) requests plan {data.plan_code}"
    )
    # 1. Lookup plan by code
    plan = session.exec(
        select(SubscriptionPlan).where(SubscriptionPlan.code == data.plan_code)
    ).first()
    logger.info(f"Plan found: {plan}")

    if not plan or not plan.lemon_variant_id:
        logger.warning(
            f"Plan not found or not configured for LemonSqueezy: {data.plan_code}"
        )
        raise HTTPException(
            status_code=404, detail="Plan not found or not configured for LemonSqueezy"
        )

    # 2. Call LemonSqueezy API to create customer nếu user chưa có lemon_customer_id
    LEMON_API_KEY = settings.LEMON_SQUEEZY_API_KEY
    STORE_ID = settings.LEMON_SQUEEZY_STORE_ID

    if not LEMON_API_KEY or not STORE_ID:
        logger.error("LemonSqueezy API key or store ID not configured")
        raise HTTPException(
            status_code=500, detail="LemonSqueezy API key or store ID not configured"
        )

    # Nếu user chưa có lemon_customer_id thì tạo mới trên LemonSqueezy
    # if not current_user.lemon_customer_id:
    #     customer_payload = {
    #         "data": {
    #             "type": "customers",
    #             "attributes": {
    #                 "name": current_user.full_name or current_user.email,
    #                 "email": current_user.email,
    #                 # Có thể bổ sung city, region, country nếu có
    #             },
    #             "relationships": {
    #                 "store": {
    #                     "data": {
    #                         "type": "stores",
    #                         "id": str(STORE_ID),
    #                     }
    #                 }
    #             },
    #         }
    #     }
    #     customer_headers = {
    #         "Authorization": f"Bearer {LEMON_API_KEY}",
    #         "Content-Type": "application/vnd.api+json",
    #         "Accept": "application/vnd.api+json",
    #     }
    #     try:
    #         customer_response = httpx.post(
    #             "https://api.lemonsqueezy.com/v1/customers",
    #             json=customer_payload,
    #             headers=customer_headers,
    #             timeout=30.0,
    #         )
    #         logger.info(
    #             f"LemonSqueezy create customer response: {customer_response.json()}"
    #         )
    #         customer_response.raise_for_status()
    #         lemon_customer_id = customer_response.json()["data"]["id"]
    #         # Update user trong database
    #         current_user.lemon_customer_id = lemon_customer_id
    #         # session.add(current_user)
    #         session.commit()
    #         logger.info(
    #             f"Created LemonSqueezy customer for user {current_user.id}, id: {lemon_customer_id}"
    #         )
    #     except Exception as e:
    #         logger.error(f"LemonSqueezy create customer error: {e}")
    #         raise HTTPException(
    #             status_code=502, detail=f"LemonSqueezy create customer error: {e}"
    #         )

    # 3. Call LemonSqueezy API to create checkout session như cũ
    payload = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "product_options": {
                    "redirect_url": f"{settings.FRONTEND_HOST}/dashboard",
                    "enabled_variants": [plan.lemon_variant_id],
                },
                "checkout_options": {
                    "embed": False,
                    "media": False,
                    "skip_trial": True,
                },
                "checkout_data": {
                    "email": current_user.email,
                    "custom": {"user_id": str(current_user.id)},
                },
            },
            "relationships": {
                "store": {
                    "data": {
                        "type": "stores",
                        "id": str(STORE_ID),
                    }
                },
                "variant": {
                    "data": {
                        "type": "variants",
                        "id": str(plan.lemon_variant_id),
                    }
                },
            },
        }
    }
    headers = {
        "Authorization": f"Bearer {LEMON_API_KEY}",
        "Content-Type": "application/vnd.api+json",
        "Accept": "application/vnd.api+json",
    }
    logger.info(f"Sending LemonSqueezy checkout payload: {payload}")
    logger.info(f"Sending LemonSqueezy checkout headers: {headers}")
    try:
        response = httpx.post(
            "https://api.lemonsqueezy.com/v1/checkouts",
            json=payload,
            headers=headers,
            timeout=30.0,
        )
        logger.info(f"LemonSqueezy checkout response: {response.json()}")
        response.raise_for_status()
        url = response.json()["data"]["attributes"]["url"]
        logger.info(
            f"LemonSqueezy checkout created for user {current_user.id}, url: {url}"
        )
        return CheckoutResponse(checkout_url=url)
    except Exception as e:
        logger.error(f"LemonSqueezy error: {e}")
        raise HTTPException(status_code=502, detail=f"LemonSqueezy error: {e}")


# === 5. Webhook endpoint for Lemon Squeezy ===
@router.post("/webhooks/lemonsqueezy")
async def lemonsqueezy_webhook(
    request: Request, session: Session = Depends(get_session)
):
    logger.info("[POST /webhooks/lemonsqueezy] Webhook received")

    # Parse các trường ngày giờ sang datetime
    def parse_dt(val):
        if val:
            try:
                return date_parser.isoparse(val)
            except Exception:
                return None
        return None

    # Hàm tìm user theo customer_id (lemon_customer_id) hoặc email
    def find_user(user_id, lemon_customer_id, user_email):
        user = None
        if user_id:
            user = session.exec(select(User).where(User.id == str(user_id))).first()
        if not user and lemon_customer_id:
            user = session.exec(
                select(User).where(User.lemon_customer_id == str(lemon_customer_id))
            ).first()
        if not user and user_email:
            user = session.exec(select(User).where(User.email == user_email)).first()
        return user

    # 1. Verify signature Lemon Squeezy webhook
    secret = settings.LEMON_SQUEEZY_WEBHOOK_SECRET
    signature = request.headers.get("X-Signature")
    raw_body = await request.body()
    if not secret or not signature:
        logger.warning("Missing webhook secret or signature")
        raise HTTPException(
            status_code=401, detail="Missing webhook secret or signature"
        )
    computed = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed, signature):
        logger.warning("Invalid webhook signature")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    payload = await request.json()
    # logger.info(f"Webhook payload: {payload}")
    event_type = payload.get("meta", {}).get("event_name")
    user_id = payload.get("meta", {}).get("custom_data").get("user_id")
    data = payload.get("data", {}).get("attributes", {})
    logger.info(f"Webhook event: {event_type}, data: {data}")

    # Đặt biến dùng chung cho các event
    customer_id = data.get("customer_id")
    user_email = data.get("user_email")
    user = find_user(user_id, customer_id, user_email)

    # === Mapping event names theo tài liệu LemonSqueezy ===
    if event_type == "order_created":
        # Xử lý khi có đơn hàng mới (single payment hoặc subscription)
        logger.info(
            f"Order created: order_id={data.get('order_id')}, user_email={data.get('user_email')}"
        )
        return {"ok": True}

    elif event_type == "subscription_created":
        variant_id = data.get("variant_id")
        subscription_id = data.get("first_subscription_item").get("subscription_id")
        plan = session.exec(
            select(SubscriptionPlan).where(
                SubscriptionPlan.lemon_variant_id == variant_id
            )
        ).first()
        if not plan:
            logger.error(f"Plan not found for variant_id: {variant_id}")
            return {"error": "Plan not found"}
        if not user:
            logger.error(
                f"User not found: customer_id={customer_id}, email={user_email}"
            )
            return {"error": "User not found"}
        sub = session.exec(
            select(UserSubscription).where(UserSubscription.user_id == user.id)
        ).first()
        if not sub:
            sub = UserSubscription(
                user_id=user.id,
                subscription_plan_id=plan.id,
                lemon_subscription_id=subscription_id,
                status=data.get("status"),
                start_date=parse_dt(data.get("created_at")),
                current_period_end=parse_dt(data.get("renews_at")),
                trial_end=parse_dt(data.get("trial_ends_at")),
            )
            session.add(sub)
            logger.info(f"Created new UserSubscription for user {user.id}")
        else:
            sub.subscription_plan_id = plan.id
            sub.lemon_subscription_id = subscription_id
            sub.status = data.get("status")
            sub.start_date = parse_dt(data.get("created_at"))
            sub.current_period_end = parse_dt(data.get("renews_at"))
            sub.trial_end = parse_dt(data.get("trial_ends_at"))
            logger.info(f"Updated UserSubscription for user {user.id}")
        session.commit()
        return {"ok": True}

    elif event_type == "subscription_payment_success":
        subscription_id = data.get("subscription_id")
        user_subscription = (
            session.exec(
                select(UserSubscription).where(
                    UserSubscription.lemon_subscription_id == subscription_id
                )
            ).first()
            if subscription_id
            else None
        )
        # Nếu chưa tìm được user thì lấy từ subscription
        if not user and user_subscription:
            user = session.get(User, user_subscription.user_id)
        payment = Payment(
            user_id=user.id if user else None,
            user_subscription_id=user_subscription.id if user_subscription else None,
            lemon_order_id=data.get("order_id"),
            amount_in_cents=data.get("total"),
            currency=data.get("currency", "usd"),
            status="succeeded",
            paid_at=parse_dt(data.get("created_at")),
            receipt_url=data.get("urls", {}).get("invoice_url"),
        )
        session.add(payment)
        session.commit()
        logger.info(
            f"Payment recorded: order_id={data.get('order_id')}, subscription_id={subscription_id}"
        )
        return {"ok": True}

    elif event_type == "subscription_updated":
        subscription_id = data.get("first_subscription_item").get("subscription_id")
        user_subscription = (
            session.exec(
                select(UserSubscription).where(
                    UserSubscription.lemon_subscription_id == subscription_id
                )
            ).first()
            if subscription_id
            else None
        )
        if user_subscription:
            variant_id = data.get("variant_id")
            if variant_id:
                plan = session.exec(
                    select(SubscriptionPlan).where(
                        SubscriptionPlan.lemon_variant_id == variant_id
                    )
                ).first()
                if plan:
                    user_subscription.subscription_plan_id = plan.id
                    logger.info(
                        f"Subscription plan updated: subscription_id={subscription_id}, new_plan_id={plan.id}"
                    )
            if data.get("status"):
                user_subscription.status = data["status"]
                logger.info(
                    f"Subscription status updated: subscription_id={subscription_id}, status={data['status']}"
                )
            user_subscription.current_period_end = (
                parse_dt(data.get("renews_at")) or user_subscription.current_period_end
            )
            session.commit()
        return {"ok": True}

    elif event_type == "subscription_cancelled":
        subscription_id = data.get("id") or data.get("subscription_id")
        user_subscription = (
            session.exec(
                select(UserSubscription).where(
                    UserSubscription.lemon_subscription_id == subscription_id
                )
            ).first()
            if subscription_id
            else None
        )
        if user_subscription:
            user_subscription.status = "cancelled"
            session.commit()
            logger.info(f"Subscription cancelled: subscription_id={subscription_id}")
        return {"ok": True}

    elif event_type == "subscription_expired":
        subscription_id = data.get("id") or data.get("subscription_id")
        user_subscription = (
            session.exec(
                select(UserSubscription).where(
                    UserSubscription.lemon_subscription_id == subscription_id
                )
            ).first()
            if subscription_id
            else None
        )
        if user_subscription:
            user_subscription.status = "expired"
            session.commit()
            logger.info(f"Subscription expired: subscription_id={subscription_id}")
        return {"ok": True}

    elif event_type == "subscription_payment_failed":
        subscription_id = data.get("subscription_id")
        user_subscription = (
            session.exec(
                select(UserSubscription).where(
                    UserSubscription.lemon_subscription_id == subscription_id
                )
            ).first()
            if subscription_id
            else None
        )
        if user_subscription:
            user_subscription.status = "payment_failed"
            session.commit()
            logger.info(
                f"Subscription payment failed: subscription_id={subscription_id}"
            )
        return {"ok": True}

    else:
        logger.info(f"Webhook event ignored: {event_type}")
        return {"ignored": True}
    return {"ok": True}
