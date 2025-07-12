from fastapi import APIRouter

from app.api.routes import (
    login,
    checkout,
    subscription,
    users,
    utils,
    common,
    blogs,
    faqs,
    support_tickets,
)


api_router = APIRouter()
api_router.include_router(common.router)
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(checkout.router)
api_router.include_router(subscription.router)
api_router.include_router(blogs.router)
api_router.include_router(faqs.router)
api_router.include_router(support_tickets.router)
