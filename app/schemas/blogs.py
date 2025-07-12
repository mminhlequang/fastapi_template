from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
import uuid


# --- Blog Category Schemas ---
class BlogCategoryBase(BaseModel):
    name: str = Field(max_length=255)
    slug: str = Field(max_length=255)
    description: str | None = None


class BlogCategoryCreate(BlogCategoryBase):
    pass


class BlogCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    description: str | None = None


class BlogCategoryResponse(BlogCategoryBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Blog Tag Schemas ---
class BlogTagBase(BaseModel):
    name: str = Field(max_length=100)
    slug: str = Field(max_length=100)


class BlogTagCreate(BlogTagBase):
    pass


class BlogTagUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    slug: str | None = Field(default=None, max_length=100)


class BlogTagResponse(BlogTagBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Blog User Author Profile Schemas ---
class BlogUserAuthorProfileBase(BaseModel):
    display_name: str = Field(max_length=255)
    bio: str | None = None
    avatar_url: str | None = None
    is_active: bool = True


class BlogUserAuthorProfileResponse(BlogUserAuthorProfileBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Blog Post Schemas ---
class BlogPostBase(BaseModel):
    title: str = Field(max_length=255)
    slug: str = Field(max_length=255)
    summary: str | None = None
    content: str
    thumbnail_url: str | None = None
    thumbnail_compressed_url: str | None = None
    is_featured: bool = False
    is_hot: bool = False
    status: str = Field(default="draft", max_length=20)  # draft, published, archived
    published_at: datetime | None = None
    seo_title: str | None = Field(default=None, max_length=255)
    seo_description: str | None = None


class BlogPostResponse(BlogPostBase):
    id: uuid.UUID
    author_profile_id: uuid.UUID | None
    view_count: int
    created_at: datetime
    updated_at: datetime
    # Relationships
    author_profile: Optional[BlogUserAuthorProfileResponse] = None
    categories: List[BlogCategoryResponse] = []
    tags: List[BlogTagResponse] = []

    model_config = ConfigDict(from_attributes=True)
