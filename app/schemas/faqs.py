import uuid
from typing import Optional
from pydantic import Field
from sqlmodel import SQLModel
from datetime import datetime


# --- FAQ Category Schemas ---


class FAQCategoryCreate(SQLModel):
    """Schema for creating a FAQ category."""

    name: str = Field(max_length=255, description="Category name")
    description: Optional[str] = Field(default=None, description="Category description")
    order_index: int = Field(default=0, description="Sort order")
    is_active: bool = Field(default=True, description="Active status")


class FAQCategoryUpdate(SQLModel):
    """Schema for updating a FAQ category."""

    name: Optional[str] = Field(
        default=None, max_length=255, description="Category name"
    )
    description: Optional[str] = Field(default=None, description="Category description")
    order_index: Optional[int] = Field(default=None, description="Sort order")
    is_active: Optional[bool] = Field(default=None, description="Active status")


class FAQCategoryResponse(SQLModel):
    """Schema for FAQ category response."""

    id: uuid.UUID
    name: str
    description: Optional[str]
    order_index: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# --- FAQ Schemas ---


class FAQCreate(SQLModel):
    """Schema for creating a FAQ."""

    question: str = Field(description="FAQ question")
    answer: str = Field(description="FAQ answer")
    addition_info: Optional[str] = Field(
        default=None, description="Additional information"
    )
    faq_category_id: Optional[uuid.UUID] = Field(
        default=None, description="Category ID"
    )
    order_index: int = Field(default=0, description="Sort order")
    is_active: bool = Field(default=True, description="Active status")


class FAQUpdate(SQLModel):
    """Schema for updating a FAQ."""

    question: Optional[str] = Field(default=None, description="FAQ question")
    answer: Optional[str] = Field(default=None, description="FAQ answer")
    addition_info: Optional[str] = Field(
        default=None, description="Additional information"
    )
    faq_category_id: Optional[uuid.UUID] = Field(
        default=None, description="Category ID"
    )
    order_index: Optional[int] = Field(default=None, description="Sort order")
    is_active: Optional[bool] = Field(default=None, description="Active status")


class FAQResponse(SQLModel):
    """Schema for FAQ response."""

    id: uuid.UUID
    question: str
    answer: str
    addition_info: Optional[str]
    faq_category_id: Optional[uuid.UUID]
    order_index: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Nested category info
    category: Optional[FAQCategoryResponse] = None
