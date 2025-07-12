import uuid

from datetime import datetime
from typing import Optional
from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import Column, JSON, UniqueConstraint as sa_UniqueConstraint, ForeignKey


# Database model, database table inferred from class name
class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
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
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    # Relationships
    billing_info: "BillingInfo" = Relationship(back_populates="user")
    subscriptions: list["UserSubscription"] = Relationship(back_populates="user")
    payments: list["Payment"] = Relationship(back_populates="user")
    social_accounts: list["SocialAccount"] = Relationship(back_populates="user")

    class Config:
        arbitrary_types_allowed = True


# Social Account Model for social login
class SocialAccount(SQLModel, table=True):
    __tablename__ = "social_accounts"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        sa_column=Column("user_id", ForeignKey("user.id", ondelete="CASCADE"))
    )

    # Provider info (tối thiểu)
    provider: str = Field(max_length=50)  # facebook, google, apple
    provider_user_id: str = Field(max_length=255)  # ID từ provider
    provider_email: str | None = Field(default=None, max_length=255)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    linked_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    user: User = Relationship(back_populates="social_accounts")

    class Config:
        table_args = (
            # Unique constraint: 1 provider chỉ link với 1 user
            sa_UniqueConstraint(
                "provider", "provider_user_id", name="uq_provider_user"
            ),
        )


# Billing info for user (company, tax, address, ...)
class BillingInfo(SQLModel, table=True):
    __tablename__ = "billing_info"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        sa_column=Column(
            "user_id", ForeignKey("user.id", ondelete="CASCADE"), unique=True
        )
    )
    company_name: str = Field(max_length=255)
    tax_code: str | None = Field(default=None, max_length=255)
    address: str
    email: str = Field(max_length=255)
    phone_number: str | None = Field(default=None, max_length=255)
    country: str = Field(default="VN", max_length=32)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    user: User = Relationship(back_populates="billing_info")


# Subscription plan (Start, Automate, Enterprise)
class SubscriptionPlan(SQLModel, table=True):
    __tablename__ = "subscription_plans"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    code: str = Field(max_length=64, unique=True)
    name: str = Field(max_length=255)
    description: str | None = None
    price: int
    currency: str = Field(default="usd", max_length=16)
    interval: str = Field(default="month", max_length=16)
    features: dict | None = Field(default=None, sa_column=Column(JSON))
    # New limits and permissions fields

    # Lemon Squeezy integration
    lemon_product_id: str | None = Field(default=None, max_length=255)
    lemon_variant_id: str | None = Field(default=None, max_length=255)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    subscriptions: list["UserSubscription"] = Relationship(
        back_populates="subscription_plan"
    )


# User's subscription
class UserSubscription(SQLModel, table=True):
    __tablename__ = "user_subscriptions"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        sa_column=Column("user_id", ForeignKey("user.id", ondelete="CASCADE"))
    )
    subscription_plan_id: uuid.UUID = Field(
        sa_column=Column(
            "subscription_plan_id",
            ForeignKey("subscription_plans.id", ondelete="RESTRICT"),
        )
    )
    lemon_subscription_id: str | None = Field(default=None, max_length=255)
    status: str = Field(max_length=32)
    start_date: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    canceled_at: datetime | None = None
    trial_end: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    user: User = Relationship(back_populates="subscriptions")
    subscription_plan: SubscriptionPlan = Relationship(back_populates="subscriptions")
    payments: list["Payment"] = Relationship(back_populates="user_subscription")


# Payment for subscription
class Payment(SQLModel, table=True):
    __tablename__ = "payments"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        sa_column=Column("user_id", ForeignKey("user.id", ondelete="CASCADE"))
    )
    user_subscription_id: uuid.UUID = Field(
        sa_column=Column(
            "user_subscription_id",
            ForeignKey("user_subscriptions.id", ondelete="CASCADE"),
        )
    )
    lemon_order_id: str | None = Field(default=None, max_length=255)
    amount_in_cents: int | None = None
    currency: str = Field(default="usd", max_length=16)
    status: str = Field(max_length=32)
    paid_at: datetime | None = None
    receipt_url: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    user: User = Relationship(back_populates="payments")
    user_subscription: UserSubscription = Relationship(back_populates="payments")


# --- User Project Model ---
class UserProject(SQLModel, table=True):
    __tablename__ = "user_projects"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=255, nullable=False, index=True)
    color_code: str = Field(max_length=7, regex=r"^#[0-9A-Fa-f]{6}$")
    user_id: uuid.UUID = Field(
        sa_column=Column(
            "user_id",
            ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


# --- User Website Model ---
class UserWebsite(SQLModel, table=True):
    __tablename__ = "user_websites"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    label: str | None = Field(default=None, max_length=255)
    description: str | None = None
    url: str = Field(max_length=500, nullable=False)
    logo_url: str | None = Field(default=None, max_length=500)
    company_slogan: str | None = Field(default=None, max_length=500)
    company_name: str | None = Field(default=None, max_length=255)
    color_primary1: str | None = Field(default=None, max_length=7)
    color_primary2: str | None = Field(default=None, max_length=7)
    color_background: str | None = Field(default=None, max_length=7)
    color_bubble1: str | None = Field(default=None, max_length=7)
    color_bubble2: str | None = Field(default=None, max_length=7)
    is_allow_image: bool = Field(default=True, nullable=False)
    is_allow_file: bool = Field(default=True, nullable=False)
    user_id: uuid.UUID = Field(
        sa_column=Column(
            "user_id",
            ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    user_project_id: uuid.UUID = Field(
        sa_column=Column(
            "user_project_id",
            ForeignKey("user_projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


# --- User Product Model ---
class UserProduct(SQLModel, table=True):
    __tablename__ = "user_products"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=255, nullable=False, index=True)
    thumbnail: str | None = Field(default=None, max_length=500)
    description: str | None = None
    is_active: bool = Field(default=True)
    user_id: uuid.UUID = Field(
        sa_column=Column(
            "user_id",
            ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    user_project_id: uuid.UUID = Field(
        sa_column=Column(
            "user_project_id",
            ForeignKey("user_projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    assets: list["UserProductAsset"] = Relationship(back_populates="user_product")


# --- User Product Asset Model ---
class UserProductAsset(SQLModel, table=True):
    __tablename__ = "user_product_assets"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_product_id: uuid.UUID = Field(
        sa_column=Column(
            "user_product_id",
            ForeignKey("user_products.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    label: str | None = Field(default=None, max_length=255)
    origin_url: str = Field(max_length=1000, nullable=False)
    medium_url: str | None = Field(default=None, max_length=1000)
    tiny_url: str | None = Field(default=None, max_length=1000)
    file_type: str = Field(max_length=50, nullable=False)
    file_size: int | None = None
    mime_type: str | None = Field(default=None, max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    # Relationships
    user_product: UserProduct = Relationship(back_populates="assets")


# --- User FAQ Model ---
class UserFAQ(SQLModel, table=True):
    __tablename__ = "user_faqs"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    question: str = Field(nullable=False)
    answer: str = Field(nullable=False)
    description: str | None = None
    is_active: bool = Field(default=True, index=True)
    user_id: uuid.UUID = Field(
        sa_column=Column(
            "user_id",
            ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    user_project_id: uuid.UUID = Field(
        sa_column=Column(
            "user_project_id",
            ForeignKey("user_projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    sort_order: int = Field(default=0, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    assets: list["UserFAQAsset"] = Relationship(back_populates="user_faq")


# --- User FAQ Asset Model ---
class UserFAQAsset(SQLModel, table=True):
    __tablename__ = "user_faqs_assets"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_faq_id: uuid.UUID = Field(
        sa_column=Column(
            "user_faq_id",
            ForeignKey("user_faqs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    label: str | None = Field(default=None, max_length=255)
    origin_url: str = Field(max_length=1000, nullable=False)
    medium_url: str | None = Field(default=None, max_length=1000)
    tiny_url: str | None = Field(default=None, max_length=1000)
    file_type: str = Field(max_length=50, nullable=False)
    file_size: int | None = None
    mime_type: str | None = Field(default=None, max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    # Relationships
    user_faq: UserFAQ = Relationship(back_populates="assets")


# --- Blog Models ---
class BlogPostCategory(SQLModel, table=True):
    __tablename__ = "blogs_post_categories"
    post_id: uuid.UUID = Field(
        sa_column=Column(
            "post_id",
            ForeignKey("blogs_posts.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    category_id: uuid.UUID = Field(
        sa_column=Column(
            "category_id",
            ForeignKey("blogs_categories.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class BlogPostTag(SQLModel, table=True):
    __tablename__ = "blogs_post_tags"
    post_id: uuid.UUID = Field(
        sa_column=Column(
            "post_id",
            ForeignKey("blogs_posts.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    tag_id: uuid.UUID = Field(
        sa_column=Column(
            "tag_id",
            ForeignKey("blogs_tags.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class BlogCategory(SQLModel, table=True):
    __tablename__ = "blogs_categories"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=255, nullable=False, unique=True, index=True)
    slug: str = Field(max_length=255, nullable=False, unique=True, index=True)
    description: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    # Relationships
    posts: list["BlogPost"] = Relationship(
        back_populates="categories", link_model=BlogPostCategory
    )


class BlogTag(SQLModel, table=True):
    __tablename__ = "blogs_tags"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=100, nullable=False, unique=True, index=True)
    slug: str = Field(max_length=100, nullable=False, unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    # Relationships
    posts: list["BlogPost"] = Relationship(
        back_populates="tags", link_model=BlogPostTag
    )


class BlogUserAuthorProfile(SQLModel, table=True):
    __tablename__ = "blogs_user_author_profiles"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        sa_column=Column(
            "user_id",
            ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    display_name: str = Field(max_length=255, nullable=False)
    bio: str | None = None
    avatar_url: str | None = None
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    # Relationships
    user: User = Relationship()
    posts: list["BlogPost"] = Relationship(back_populates="author_profile")


class BlogPost(SQLModel, table=True):
    __tablename__ = "blogs_posts"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    author_profile_id: uuid.UUID | None = Field(
        sa_column=Column(
            "author_profile_id",
            ForeignKey("blogs_user_author_profiles.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        )
    )
    title: str = Field(max_length=255, nullable=False)
    slug: str = Field(max_length=255, nullable=False, unique=True, index=True)
    summary: str | None = None
    content: str = Field(nullable=False)
    thumbnail_url: str | None = None
    thumbnail_compressed_url: str | None = None
    is_featured: bool = Field(default=False, index=True)
    is_hot: bool = Field(default=False, index=True)
    status: str = Field(
        default="draft", max_length=20, index=True
    )  # draft, published, archived
    published_at: datetime | None = None
    view_count: int = Field(default=0, index=True)
    seo_title: str | None = Field(default=None, max_length=255)
    seo_description: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    # Relationships
    author_profile: BlogUserAuthorProfile | None = Relationship(back_populates="posts")
    categories: list[BlogCategory] = Relationship(
        back_populates="posts", link_model=BlogPostCategory
    )
    tags: list[BlogTag] = Relationship(back_populates="posts", link_model=BlogPostTag)


# --- FAQ Models ---
class FAQCategory(SQLModel, table=True):
    __tablename__ = "faq_categories"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=255, nullable=False, index=True)
    description: str | None = None
    order_index: int = Field(default=0, index=True)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    # Relationships
    faqs: list["FAQ"] = Relationship(back_populates="category")


class FAQ(SQLModel, table=True):
    __tablename__ = "faqs"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    question: str = Field(nullable=False)
    answer: str = Field(nullable=False)
    addition_info: str | None = None
    faq_category_id: uuid.UUID | None = Field(
        sa_column=Column(
            "faq_category_id",
            ForeignKey("faq_categories.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        )
    )
    order_index: int = Field(default=0, index=True)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    # Relationships
    category: FAQCategory | None = Relationship(back_populates="faqs")


# --- Support Ticket Models ---
class SupportTicketCategory(SQLModel, table=True):
    __tablename__ = "support_ticket_categories"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=255, nullable=False, index=True)
    description: str | None = None
    is_active: bool = Field(default=True, index=True)
    is_internal: bool = Field(
        default=False, nullable=False, index=True
    )  # For internal staff use only
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    # Relationships
    tickets: list["SupportTicket"] = Relationship(back_populates="category")


class SupportTicket(SQLModel, table=True):
    __tablename__ = "support_tickets"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    subject: str = Field(max_length=500, nullable=False)
    description: str = Field(nullable=False)
    status: str = Field(
        max_length=50, nullable=False, default="open", index=True
    )  # open, in_progress, resolved, closed
    priority: str = Field(
        max_length=20, nullable=False, default="medium", index=True
    )  # low, medium, high, urgent
    ticket_category_id: uuid.UUID | None = Field(
        sa_column=Column(
            "ticket_category_id",
            ForeignKey("support_ticket_categories.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        )
    )
    user_id: uuid.UUID | None = Field(
        sa_column=Column(
            "user_id",
            ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        )
    )
    assigned_to: uuid.UUID | None = Field(
        sa_column=Column(
            "assigned_to",
            ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        )
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, nullable=False, index=True
    )
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    # Relationships
    category: SupportTicketCategory | None = Relationship(back_populates="tickets")
    user: User | None = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[SupportTicket.user_id]"}
    )
    assigned_user: User | None = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[SupportTicket.assigned_to]"}
    )
    comments: list["SupportTicketComment"] = Relationship(
        back_populates="ticket", cascade_delete=True
    )
    attachments: list["SupportTicketAttachment"] = Relationship(
        back_populates="ticket", cascade_delete=True
    )


class SupportTicketComment(SQLModel, table=True):
    __tablename__ = "support_ticket_comments"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    ticket_id: uuid.UUID = Field(
        sa_column=Column(
            "ticket_id",
            ForeignKey("support_tickets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    user_id: uuid.UUID | None = Field(
        sa_column=Column(
            "user_id",
            ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        )
    )
    message: str = Field(nullable=False)
    is_internal: bool = Field(
        default=False, nullable=False
    )  # Internal notes for staff only
    created_at: datetime = Field(
        default_factory=datetime.utcnow, nullable=False, index=True
    )
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    # Relationships
    ticket: SupportTicket = Relationship(back_populates="comments")
    user: User | None = Relationship()
    attachments: list["SupportTicketAttachment"] = Relationship(
        back_populates="comment", cascade_delete=True
    )


class SupportTicketAttachment(SQLModel, table=True):
    __tablename__ = "support_ticket_attachments"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    ticket_id: uuid.UUID = Field(
        sa_column=Column(
            "ticket_id",
            ForeignKey("support_tickets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    comment_id: uuid.UUID | None = Field(
        sa_column=Column(
            "comment_id",
            ForeignKey("support_ticket_comments.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        )
    )
    file_url: str = Field(max_length=1000, nullable=False)
    file_name: str = Field(max_length=255, nullable=False)
    file_size: int | None = None
    file_type: str | None = Field(default=None, max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    # Relationships
    ticket: SupportTicket = Relationship(back_populates="attachments")
    comment: SupportTicketComment | None = Relationship(back_populates="attachments")
