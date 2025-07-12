from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import TypeVar, Generic, List


# Generic message
class Message(BaseModel):
    message: str


# Define a TypeVar for generic type
T = TypeVar("T")


class ListResponse(BaseModel, Generic[T]):
    """
    Generic response model for list data
    Example usage:
        ListResponse[UserResponse] - for list of users
        ListResponse[SubscriptionPlanResponse] - for list of subscription plans
    """

    data: List[T]
    count: int

    class Config:
        from_attributes = True


# Example of specific response types
# UserListResponse = ListResponse[UserResponse]
# SubscriptionPlanListResponse = ListResponse[SubscriptionPlanResponse]
# PaymentListResponse = ListResponse[PaymentResponse]
