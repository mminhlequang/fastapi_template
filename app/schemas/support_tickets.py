import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# --- Support Ticket Category Schemas ---


class SupportTicketCategoryBase(BaseModel):
    """Base schema for Support Ticket Category"""

    name: str = Field(..., max_length=255, description="Category name")
    description: Optional[str] = Field(None, description="Category description")
    is_active: bool = Field(True, description="Whether category is active")
    is_internal: bool = Field(
        False, description="Whether category is for internal staff use only"
    )


class SupportTicketCategoryCreate(SupportTicketCategoryBase):
    """Schema for creating a new Support Ticket Category"""

    pass


class SupportTicketCategoryUpdate(BaseModel):
    """Schema for updating an existing Support Ticket Category"""

    name: Optional[str] = Field(None, max_length=255, description="Category name")
    description: Optional[str] = Field(None, description="Category description")
    is_active: Optional[bool] = Field(None, description="Whether category is active")
    is_internal: Optional[bool] = Field(
        None, description="Whether category is for internal staff use only"
    )


class SupportTicketCategoryResponse(SupportTicketCategoryBase):
    """Schema for Support Ticket Category response"""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Support Ticket Schemas ---


class SupportTicketBase(BaseModel):
    """Base schema for Support Ticket"""

    subject: str = Field(..., max_length=500, description="Ticket subject")
    description: str = Field(..., description="Ticket description")
    email: Optional[str] = Field(None, max_length=255, description="Email")
    phone_number: Optional[str] = Field(None, max_length=255, description="Phone number")
    status: str = Field("open", max_length=50, description="Ticket status")
    priority: str = Field("medium", max_length=20, description="Ticket priority")
    ticket_category_id: Optional[uuid.UUID] = Field(None, description="Category ID")


class SupportTicketCreate(SupportTicketBase):
    """Schema for creating a new Support Ticket"""

    pass


class SupportTicketUpdate(BaseModel):
    """Schema for updating an existing Support Ticket"""

    subject: Optional[str] = Field(None, max_length=500, description="Ticket subject")
    description: Optional[str] = Field(None, description="Ticket description")
    email: Optional[str] = Field(None, max_length=255, description="Email")
    phone_number: Optional[str] = Field(None, max_length=255, description="Phone number")
    status: Optional[str] = Field(None, max_length=50, description="Ticket status")
    priority: Optional[str] = Field(None, max_length=20, description="Ticket priority")
    ticket_category_id: Optional[uuid.UUID] = Field(None, description="Category ID")
    assigned_to: Optional[uuid.UUID] = Field(None, description="Assigned user ID")


class SupportTicketResponse(SupportTicketBase):
    """Schema for Support Ticket response"""

    id: uuid.UUID
    user_id: Optional[uuid.UUID]
    assigned_to: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    # Nested relationships
    category: Optional[SupportTicketCategoryResponse] = None
    comments: List["SupportTicketCommentResponse"] = []
    attachments: List["SupportTicketAttachmentResponse"] = []

    class Config:
        from_attributes = True


# --- Support Ticket Comment Schemas ---


class SupportTicketCommentBase(BaseModel):
    """Base schema for Support Ticket Comment"""

    message: str = Field(..., description="Comment message")
    is_internal: bool = Field(False, description="Whether comment is internal only")


class SupportTicketCommentCreate(SupportTicketCommentBase):
    """Schema for creating a new Support Ticket Comment"""

    ticket_id: uuid.UUID = Field(..., description="Ticket ID")


class SupportTicketCommentUpdate(BaseModel):
    """Schema for updating an existing Support Ticket Comment"""

    message: Optional[str] = Field(None, description="Comment message")
    is_internal: Optional[bool] = Field(
        None, description="Whether comment is internal only"
    )


class SupportTicketCommentResponse(SupportTicketCommentBase):
    """Schema for Support Ticket Comment response"""

    id: uuid.UUID
    ticket_id: uuid.UUID
    user_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    # Nested relationships
    attachments: List["SupportTicketAttachmentResponse"] = []

    class Config:
        from_attributes = True


# --- Support Ticket Attachment Schemas ---


class SupportTicketAttachmentBase(BaseModel):
    """Base schema for Support Ticket Attachment"""

    file_url: str = Field(..., max_length=1000, description="File URL")
    file_name: str = Field(..., max_length=255, description="Original file name")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    file_type: Optional[str] = Field(None, max_length=100, description="File MIME type")


class SupportTicketAttachmentCreate(SupportTicketAttachmentBase):
    """Schema for creating a new Support Ticket Attachment"""

    ticket_id: uuid.UUID = Field(..., description="Ticket ID")
    comment_id: Optional[uuid.UUID] = Field(
        None, description="Comment ID (if attached to comment)"
    )


class SupportTicketAttachmentResponse(SupportTicketAttachmentBase):
    """Schema for Support Ticket Attachment response"""

    id: uuid.UUID
    ticket_id: uuid.UUID
    comment_id: Optional[uuid.UUID]
    created_at: datetime

    class Config:
        from_attributes = True


# Forward references
SupportTicketResponse.model_rebuild()
SupportTicketCommentResponse.model_rebuild()
