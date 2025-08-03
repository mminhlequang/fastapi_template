"""initialize_database_schema

Revision ID: 8f9f6b5207f7
Revises:
Create Date: 2025-07-12 16:55:31.884561

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "8f9f6b5207f7"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create user table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("phone_number", sa.String(length=255), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("website_url", sa.String(), nullable=True),
        sa.Column("avatar_url", sa.String(), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("lemon_customer_id", sa.String(length=255), nullable=True),
        sa.Column("is_superuser", sa.Boolean(), nullable=False),
        sa.Column("ref_code", sa.String(length=32), nullable=True),
        sa.Column("request_delete_at", sa.DateTime(), nullable=True),
        sa.Column("inactive_at", sa.DateTime(), nullable=True),
        sa.Column("trial_expired_at", sa.DateTime(), nullable=True),
        sa.Column("email_verified", sa.Boolean(), nullable=True),
        sa.Column("last_login_provider", sa.String(length=50), nullable=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_ref_code"), "users", ["ref_code"], unique=True)

    # Create social_accounts table
    op.create_table(
        "social_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column("provider_email", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("linked_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_provider_user"),
    )

    # Create billing_info table
    op.create_table(
        "billing_infos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("tax_code", sa.String(length=255), nullable=True),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone_number", sa.String(length=255), nullable=True),
        sa.Column("country", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    # Create subscription_plans table
    op.create_table(
        "subscription_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column("interval", sa.String(length=16), nullable=False),
        sa.Column("features", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("lemon_product_id", sa.String(length=255), nullable=True),
        sa.Column("lemon_variant_id", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    # Create user_subscriptions table
    op.create_table(
        "user_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "subscription_plan_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("lemon_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("start_date", sa.DateTime(), nullable=True),
        sa.Column("current_period_end", sa.DateTime(), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False),
        sa.Column("canceled_at", sa.DateTime(), nullable=True),
        sa.Column("trial_end", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["subscription_plan_id"], ["subscription_plans.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create payments table
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "user_subscription_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("lemon_order_id", sa.String(length=255), nullable=True),
        sa.Column("amount_in_cents", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("receipt_url", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["user_subscription_id"], ["user_subscriptions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create user_projects table
    op.create_table(
        "user_projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("color_code", sa.String(length=7), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_projects_name"), "user_projects", ["name"], unique=False
    )
    op.create_index(
        op.f("ix_user_projects_user_id"), "user_projects", ["user_id"], unique=False
    )

    # Create user_websites table
    op.create_table(
        "user_websites",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("company_slogan", sa.String(length=500), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("color_primary1", sa.String(length=7), nullable=True),
        sa.Column("color_primary2", sa.String(length=7), nullable=True),
        sa.Column("color_background", sa.String(length=7), nullable=True),
        sa.Column("color_bubble1", sa.String(length=7), nullable=True),
        sa.Column("color_bubble2", sa.String(length=7), nullable=True),
        sa.Column("is_allow_image", sa.Boolean(), nullable=False),
        sa.Column("is_allow_file", sa.Boolean(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["user_project_id"], ["user_projects.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_websites_is_active"), "user_websites", ["is_active"], unique=False
    )
    op.create_index(
        op.f("ix_user_websites_user_id"), "user_websites", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_user_websites_user_project_id"),
        "user_websites",
        ["user_project_id"],
        unique=False,
    )

    # Create user_products table
    op.create_table(
        "user_products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("thumbnail", sa.String(length=500), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["user_project_id"], ["user_projects.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_products_name"), "user_products", ["name"], unique=False
    )
    op.create_index(
        op.f("ix_user_products_user_id"), "user_products", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_user_products_user_project_id"),
        "user_products",
        ["user_project_id"],
        unique=False,
    )

    # Create user_product_assets table
    op.create_table(
        "user_product_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("origin_url", sa.String(length=1000), nullable=False),
        sa.Column("medium_url", sa.String(length=1000), nullable=True),
        sa.Column("tiny_url", sa.String(length=1000), nullable=True),
        sa.Column("file_type", sa.String(length=50), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_product_id"], ["user_products.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_product_assets_user_product_id"),
        "user_product_assets",
        ["user_product_id"],
        unique=False,
    )

    # Create user_faqs table
    op.create_table(
        "user_faqs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.String(), nullable=False),
        sa.Column("answer", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["user_project_id"], ["user_projects.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_faqs_is_active"), "user_faqs", ["is_active"], unique=False
    )
    op.create_index(
        op.f("ix_user_faqs_user_id"), "user_faqs", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_user_faqs_user_project_id"),
        "user_faqs",
        ["user_project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_faqs_sort_order"), "user_faqs", ["sort_order"], unique=False
    )

    # Create user_faqs_assets table
    op.create_table(
        "user_faqs_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_faq_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("origin_url", sa.String(length=1000), nullable=False),
        sa.Column("medium_url", sa.String(length=1000), nullable=True),
        sa.Column("tiny_url", sa.String(length=1000), nullable=True),
        sa.Column("file_type", sa.String(length=50), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_faq_id"], ["user_faqs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_faqs_assets_user_faq_id"),
        "user_faqs_assets",
        ["user_faq_id"],
        unique=False,
    )

    # Create blogs_categories table
    op.create_table(
        "blogs_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_blogs_categories_name"), "blogs_categories", ["name"], unique=True
    )
    op.create_index(
        op.f("ix_blogs_categories_slug"), "blogs_categories", ["slug"], unique=True
    )

    # Create blogs_tags table
    op.create_table(
        "blogs_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_blogs_tags_name"), "blogs_tags", ["name"], unique=True)
    op.create_index(op.f("ix_blogs_tags_slug"), "blogs_tags", ["slug"], unique=True)

    # Create blogs_user_author_profiles table
    op.create_table(
        "blogs_user_author_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("bio", sa.String(), nullable=True),
        sa.Column("avatar_url", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_blogs_user_author_profiles_user_id"),
        "blogs_user_author_profiles",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_blogs_user_author_profiles_is_active"),
        "blogs_user_author_profiles",
        ["is_active"],
        unique=False,
    )

    # Create blogs_posts table
    op.create_table(
        "blogs_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.String(), nullable=True),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("thumbnail_url", sa.String(), nullable=True),
        sa.Column("thumbnail_compressed_url", sa.String(), nullable=True),
        sa.Column("is_featured", sa.Boolean(), nullable=False),
        sa.Column("is_hot", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False),
        sa.Column("seo_title", sa.String(length=255), nullable=True),
        sa.Column("seo_description", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["author_profile_id"],
            ["blogs_user_author_profiles.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_blogs_posts_slug"), "blogs_posts", ["slug"], unique=True)
    op.create_index(
        op.f("ix_blogs_posts_author_profile_id"),
        "blogs_posts",
        ["author_profile_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_blogs_posts_is_featured"), "blogs_posts", ["is_featured"], unique=False
    )
    op.create_index(
        op.f("ix_blogs_posts_is_hot"), "blogs_posts", ["is_hot"], unique=False
    )
    op.create_index(
        op.f("ix_blogs_posts_status"), "blogs_posts", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_blogs_posts_view_count"), "blogs_posts", ["view_count"], unique=False
    )

    # Create blogs_post_categories table
    op.create_table(
        "blogs_post_categories",
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"], ["blogs_categories.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["post_id"], ["blogs_posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("post_id", "category_id"),
    )

    # Create blogs_post_tags table
    op.create_table(
        "blogs_post_tags",
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["blogs_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["blogs_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("post_id", "tag_id"),
    )

    # Create faq_categories table
    op.create_table(
        "faq_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_faq_categories_name"), "faq_categories", ["name"], unique=False
    )
    op.create_index(
        op.f("ix_faq_categories_order_index"),
        "faq_categories",
        ["order_index"],
        unique=False,
    )
    op.create_index(
        op.f("ix_faq_categories_is_active"),
        "faq_categories",
        ["is_active"],
        unique=False,
    )

    # Create faqs table
    op.create_table(
        "faqs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.String(), nullable=False),
        sa.Column("answer", sa.String(), nullable=False),
        sa.Column("addition_info", sa.String(), nullable=True),
        sa.Column("faq_category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["faq_category_id"], ["faq_categories.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_faqs_faq_category_id"), "faqs", ["faq_category_id"], unique=False
    )
    op.create_index(op.f("ix_faqs_order_index"), "faqs", ["order_index"], unique=False)
    op.create_index(op.f("ix_faqs_is_active"), "faqs", ["is_active"], unique=False)

    # Create support_ticket_categories table
    op.create_table(
        "support_ticket_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_support_ticket_categories_name"),
        "support_ticket_categories",
        ["name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_support_ticket_categories_is_active"),
        "support_ticket_categories",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_support_ticket_categories_is_internal"),
        "support_ticket_categories",
        ["is_internal"],
        unique=False,
    )

    # Create support_tickets table
    op.create_table(
        "support_tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone_number", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("ticket_category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["ticket_category_id"],
            ["support_ticket_categories.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_support_tickets_status"), "support_tickets", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_support_tickets_priority"),
        "support_tickets",
        ["priority"],
        unique=False,
    )
    op.create_index(
        op.f("ix_support_tickets_ticket_category_id"),
        "support_tickets",
        ["ticket_category_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_support_tickets_user_id"), "support_tickets", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_support_tickets_assigned_to"),
        "support_tickets",
        ["assigned_to"],
        unique=False,
    )
    op.create_index(
        op.f("ix_support_tickets_created_at"),
        "support_tickets",
        ["created_at"],
        unique=False,
    )

    # Create support_ticket_comments table
    op.create_table(
        "support_ticket_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["ticket_id"], ["support_tickets.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_support_ticket_comments_ticket_id"),
        "support_ticket_comments",
        ["ticket_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_support_ticket_comments_user_id"),
        "support_ticket_comments",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_support_ticket_comments_created_at"),
        "support_ticket_comments",
        ["created_at"],
        unique=False,
    )

    # Create support_ticket_attachments table
    op.create_table(
        "support_ticket_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("file_url", sa.String(length=1000), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("file_type", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["comment_id"], ["support_ticket_comments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"], ["support_tickets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_support_ticket_attachments_ticket_id"),
        "support_ticket_attachments",
        ["ticket_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_support_ticket_attachments_comment_id"),
        "support_ticket_attachments",
        ["comment_id"],
        unique=False,
    )


def downgrade():
    # Drop tables in reverse order
    op.drop_index(
        op.f("ix_support_ticket_attachments_comment_id"),
        table_name="support_ticket_attachments",
    )
    op.drop_index(
        op.f("ix_support_ticket_attachments_ticket_id"),
        table_name="support_ticket_attachments",
    )
    op.drop_table("support_ticket_attachments")

    op.drop_index(
        op.f("ix_support_ticket_comments_created_at"),
        table_name="support_ticket_comments",
    )
    op.drop_index(
        op.f("ix_support_ticket_comments_user_id"), table_name="support_ticket_comments"
    )
    op.drop_index(
        op.f("ix_support_ticket_comments_ticket_id"),
        table_name="support_ticket_comments",
    )
    op.drop_table("support_ticket_comments")

    op.drop_index(op.f("ix_support_tickets_created_at"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_assigned_to"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_user_id"), table_name="support_tickets")
    op.drop_index(
        op.f("ix_support_tickets_ticket_category_id"), table_name="support_tickets"
    )
    op.drop_index(op.f("ix_support_tickets_priority"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_status"), table_name="support_tickets")
    op.drop_table("support_tickets")

    op.drop_index(
        op.f("ix_support_ticket_categories_is_internal"),
        table_name="support_ticket_categories",
    )
    op.drop_index(
        op.f("ix_support_ticket_categories_is_active"),
        table_name="support_ticket_categories",
    )
    op.drop_index(
        op.f("ix_support_ticket_categories_name"),
        table_name="support_ticket_categories",
    )
    op.drop_table("support_ticket_categories")

    op.drop_index(op.f("ix_faqs_is_active"), table_name="faqs")
    op.drop_index(op.f("ix_faqs_order_index"), table_name="faqs")
    op.drop_index(op.f("ix_faqs_faq_category_id"), table_name="faqs")
    op.drop_table("faqs")

    op.drop_index(op.f("ix_faq_categories_is_active"), table_name="faq_categories")
    op.drop_index(op.f("ix_faq_categories_order_index"), table_name="faq_categories")
    op.drop_index(op.f("ix_faq_categories_name"), table_name="faq_categories")
    op.drop_table("faq_categories")

    op.drop_table("blogs_post_tags")
    op.drop_table("blogs_post_categories")

    op.drop_index(op.f("ix_blogs_posts_view_count"), table_name="blogs_posts")
    op.drop_index(op.f("ix_blogs_posts_status"), table_name="blogs_posts")
    op.drop_index(op.f("ix_blogs_posts_is_hot"), table_name="blogs_posts")
    op.drop_index(op.f("ix_blogs_posts_is_featured"), table_name="blogs_posts")
    op.drop_index(op.f("ix_blogs_posts_author_profile_id"), table_name="blogs_posts")
    op.drop_index(op.f("ix_blogs_posts_slug"), table_name="blogs_posts")
    op.drop_table("blogs_posts")

    op.drop_index(
        op.f("ix_blogs_user_author_profiles_is_active"),
        table_name="blogs_user_author_profiles",
    )
    op.drop_index(
        op.f("ix_blogs_user_author_profiles_user_id"),
        table_name="blogs_user_author_profiles",
    )
    op.drop_table("blogs_user_author_profiles")

    op.drop_index(op.f("ix_blogs_tags_slug"), table_name="blogs_tags")
    op.drop_index(op.f("ix_blogs_tags_name"), table_name="blogs_tags")
    op.drop_table("blogs_tags")

    op.drop_index(op.f("ix_blogs_categories_slug"), table_name="blogs_categories")
    op.drop_index(op.f("ix_blogs_categories_name"), table_name="blogs_categories")
    op.drop_table("blogs_categories")

    op.drop_index(
        op.f("ix_user_faqs_assets_user_faq_id"), table_name="user_faqs_assets"
    )
    op.drop_table("user_faqs_assets")

    op.drop_index(op.f("ix_user_faqs_sort_order"), table_name="user_faqs")
    op.drop_index(op.f("ix_user_faqs_user_project_id"), table_name="user_faqs")
    op.drop_index(op.f("ix_user_faqs_user_id"), table_name="user_faqs")
    op.drop_index(op.f("ix_user_faqs_is_active"), table_name="user_faqs")
    op.drop_table("user_faqs")

    op.drop_index(
        op.f("ix_user_product_assets_user_product_id"), table_name="user_product_assets"
    )
    op.drop_table("user_product_assets")

    op.drop_index(op.f("ix_user_products_user_project_id"), table_name="user_products")
    op.drop_index(op.f("ix_user_products_user_id"), table_name="user_products")
    op.drop_index(op.f("ix_user_products_name"), table_name="user_products")
    op.drop_table("user_products")

    op.drop_index(op.f("ix_user_websites_user_project_id"), table_name="user_websites")
    op.drop_index(op.f("ix_user_websites_user_id"), table_name="user_websites")
    op.drop_index(op.f("ix_user_websites_is_active"), table_name="user_websites")
    op.drop_table("user_websites")

    op.drop_index(op.f("ix_user_projects_user_id"), table_name="user_projects")
    op.drop_index(op.f("ix_user_projects_name"), table_name="user_projects")
    op.drop_table("user_projects")

    op.drop_table("payments")
    op.drop_table("user_subscriptions")
    op.drop_table("subscription_plans")
    op.drop_table("billing_infos")
    op.drop_table("social_accounts")

    op.drop_index(op.f("ix_users_ref_code"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
