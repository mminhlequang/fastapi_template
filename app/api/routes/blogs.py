import uuid
from typing import Any, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlmodel import select, func, or_, and_
from sqlalchemy.orm import selectinload

from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.models import (
    BlogCategory,
    BlogTag,
    BlogUserAuthorProfile,
    BlogPost,
    BlogPostCategory,
    BlogPostTag,
    User,
)
from app.schemas.base import Message, ListResponse
from app.schemas.blogs import (
    BlogCategoryCreate,
    BlogCategoryUpdate,
    BlogCategoryResponse,
    BlogTagCreate,
    BlogTagUpdate,
    BlogTagResponse,
    BlogUserAuthorProfileResponse,
    BlogPostResponse,
)
from app.utils.file_uploads import file_upload_service
import logging

logger = logging.getLogger("blogs")

router = APIRouter(prefix="/blogs", tags=["blogs"])


# --- Blog Categories APIs ---


@router.get("/categories", response_model=ListResponse)
def get_blog_categories(session: SessionDep, offset: int = 0, limit: int = 100) -> Any:
    """
    Get all blog categories (public API).
    """
    count_statement = select(func.count()).select_from(BlogCategory)
    count = session.exec(count_statement).one()

    statement = select(BlogCategory).offset(offset).limit(limit)
    categories = session.exec(statement).all()

    return ListResponse(data=categories, count=count)


@router.post(
    "/categories",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=BlogCategoryResponse,
)
def create_blog_category(
    *, session: SessionDep, category_in: BlogCategoryCreate
) -> Any:
    """
    Create new blog category (superuser only).
    """
    # Check if category with same name or slug exists
    existing = session.exec(
        select(BlogCategory).where(
            or_(
                BlogCategory.name == category_in.name,
                BlogCategory.slug == category_in.slug,
            )
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=400, detail="Category with this name or slug already exists"
        )

    category = BlogCategory(**category_in.model_dump(), updated_at=datetime.utcnow())
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


@router.patch(
    "/categories/{category_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=BlogCategoryResponse,
)
def update_blog_category(
    *, session: SessionDep, category_id: uuid.UUID, category_in: BlogCategoryUpdate
) -> Any:
    """
    Update blog category (superuser only).
    """
    category = session.get(BlogCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check for conflicts if updating name or slug
    if category_in.name or category_in.slug:
        existing = session.exec(
            select(BlogCategory).where(
                and_(
                    BlogCategory.id != category_id,
                    or_(
                        (
                            BlogCategory.name == category_in.name
                            if category_in.name
                            else False
                        ),
                        (
                            BlogCategory.slug == category_in.slug
                            if category_in.slug
                            else False
                        ),
                    ),
                )
            )
        ).first()

        if existing:
            raise HTTPException(
                status_code=400, detail="Category with this name or slug already exists"
            )

    category_data = category_in.model_dump(exclude_unset=True)
    category_data["updated_at"] = datetime.utcnow()
    category.sqlmodel_update(category_data)
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


@router.delete(
    "/categories/{category_id}",
    dependencies=[Depends(get_current_active_superuser)],
)
def delete_blog_category(session: SessionDep, category_id: uuid.UUID) -> Message:
    """
    Delete blog category (superuser only).
    """
    category = session.get(BlogCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    session.delete(category)
    session.commit()
    return Message(message="Category deleted successfully")


# --- Blog Tags APIs ---


@router.get("/tags", response_model=ListResponse)
def get_blog_tags(session: SessionDep, offset: int = 0, limit: int = 100) -> Any:
    """
    Get all blog tags (public API).
    """
    count_statement = select(func.count()).select_from(BlogTag)
    count = session.exec(count_statement).one()

    statement = select(BlogTag).offset(offset).limit(limit)
    tags = session.exec(statement).all()

    return ListResponse(data=tags, count=count)


@router.post(
    "/tags",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=BlogTagResponse,
)
def create_blog_tag(*, session: SessionDep, tag_in: BlogTagCreate) -> Any:
    """
    Create new blog tag (superuser only).
    """
    # Check if tag with same name or slug exists
    existing = session.exec(
        select(BlogTag).where(
            or_(BlogTag.name == tag_in.name, BlogTag.slug == tag_in.slug)
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=400, detail="Tag with this name or slug already exists"
        )

    tag = BlogTag(**tag_in.model_dump(), updated_at=datetime.utcnow())
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag


@router.patch(
    "/tags/{tag_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=BlogTagResponse,
)
def update_blog_tag(
    *, session: SessionDep, tag_id: uuid.UUID, tag_in: BlogTagUpdate
) -> Any:
    """
    Update blog tag (superuser only).
    """
    tag = session.get(BlogTag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    # Check for conflicts if updating name or slug
    if tag_in.name or tag_in.slug:
        existing = session.exec(
            select(BlogTag).where(
                and_(
                    BlogTag.id != tag_id,
                    or_(
                        BlogTag.name == tag_in.name if tag_in.name else False,
                        BlogTag.slug == tag_in.slug if tag_in.slug else False,
                    ),
                )
            )
        ).first()

        if existing:
            raise HTTPException(
                status_code=400, detail="Tag with this name or slug already exists"
            )

    tag_data = tag_in.model_dump(exclude_unset=True)
    tag_data["updated_at"] = datetime.utcnow()
    tag.sqlmodel_update(tag_data)
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag


@router.delete(
    "/tags/{tag_id}",
    dependencies=[Depends(get_current_active_superuser)],
)
def delete_blog_tag(session: SessionDep, tag_id: uuid.UUID) -> Message:
    """
    Delete blog tag (superuser only).
    """
    tag = session.get(BlogTag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    session.delete(tag)
    session.commit()
    return Message(message="Tag deleted successfully")


# --- Blog User Author Profiles APIs ---


@router.get("/author-profiles", response_model=ListResponse)
def get_my_author_profiles(
    session: SessionDep, current_user: CurrentUser, offset: int = 0, limit: int = 100
) -> Any:
    """
    Get all author profiles of current user.
    """
    count_statement = (
        select(func.count())
        .select_from(BlogUserAuthorProfile)
        .where(BlogUserAuthorProfile.user_id == current_user.id)
    )
    count = session.exec(count_statement).one()

    statement = (
        select(BlogUserAuthorProfile)
        .where(BlogUserAuthorProfile.user_id == current_user.id)
        .offset(offset)
        .limit(limit)
        .order_by(BlogUserAuthorProfile.created_at.desc())
    )
    profiles = session.exec(statement).all()

    return ListResponse(data=profiles, count=count)


@router.get(
    "/author-profiles/{profile_id}", response_model=BlogUserAuthorProfileResponse
)
def get_author_profile(
    session: SessionDep, current_user: CurrentUser, profile_id: uuid.UUID
) -> Any:
    """
    Get specific author profile by ID (only profiles owned by current user).
    """
    profile = session.exec(
        select(BlogUserAuthorProfile).where(
            and_(
                BlogUserAuthorProfile.id == profile_id,
                BlogUserAuthorProfile.user_id == current_user.id,
            )
        )
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Author profile not found")

    return profile


@router.post("/author-profiles", response_model=BlogUserAuthorProfileResponse)
def create_author_profile(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    display_name: str = Form(...),
    bio: str | None = Form(None),
    is_active: bool = Form(True),
    avatar: UploadFile | None = File(None),
) -> Any:
    """
    Create new author profile for current user.
    """
    profile = BlogUserAuthorProfile(
        user_id=current_user.id,
        display_name=display_name,
        bio=bio,
        is_active=is_active,
        updated_at=datetime.utcnow(),
    )

    session.add(profile)
    session.flush()  # Get the profile ID

    # Handle avatar upload
    if avatar:
        try:
            file_info = file_upload_service.upload_compressed_image(
                file=avatar,
                folder="blog-assets/avatars",
                filename=f"avatar_{profile.id}.webp",
                type="image",
                max_size=5 * 1024 * 1024,
                quality=80,
                max_width=512,
                max_height=512,
                format="webp",
            )
            profile.avatar_url = file_info.url
        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=500, detail=f"Avatar upload failed: {str(e)}"
            )

    session.commit()
    session.refresh(profile)
    return profile


@router.patch(
    "/author-profiles/{profile_id}", response_model=BlogUserAuthorProfileResponse
)
def update_author_profile(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    profile_id: uuid.UUID,
    display_name: str | None = Form(None),
    bio: str | None = Form(None),
    is_active: bool | None = Form(None),
    avatar: UploadFile | None = File(None),
) -> Any:
    """
    Update specific author profile (only profiles owned by current user).
    """
    profile = session.exec(
        select(BlogUserAuthorProfile).where(
            and_(
                BlogUserAuthorProfile.id == profile_id,
                BlogUserAuthorProfile.user_id == current_user.id,
            )
        )
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Author profile not found")

    # Update basic fields
    if display_name is not None:
        profile.display_name = display_name
    if bio is not None:
        profile.bio = bio
    if is_active is not None:
        profile.is_active = is_active

    # Handle avatar upload
    if avatar:
        try:
            # Delete old avatar if exists
            # if profile.avatar_url:
            #     delete_file(profile.avatar_url)

            # Save new avatar
            file_info = file_upload_service.upload_compressed_image(
                file=avatar,
                folder="blog-assets/avatars",
                filename=f"avatar_{profile.id}.webp",
                type="image",
                max_size=5 * 1024 * 1024,
                quality=80,
                max_width=512,
                max_height=512,
                format="webp",
            )
            profile.avatar_url = file_info.url
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Avatar upload failed: {str(e)}"
            )

    profile.updated_at = datetime.utcnow()
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


@router.delete("/author-profiles/{profile_id}")
def delete_author_profile(
    session: SessionDep, current_user: CurrentUser, profile_id: uuid.UUID
) -> Message:
    """
    Delete specific author profile (only profiles owned by current user).
    """
    profile = session.exec(
        select(BlogUserAuthorProfile).where(
            and_(
                BlogUserAuthorProfile.id == profile_id,
                BlogUserAuthorProfile.user_id == current_user.id,
            )
        )
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Author profile not found")

    session.delete(profile)
    session.commit()
    return Message(message="Author profile deleted successfully")


# --- Blog Posts APIs ---


@router.get("/posts", response_model=ListResponse)
def get_blog_posts(
    session: SessionDep,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    is_featured: bool | None = None,
    is_hot: bool | None = None,
    status: str | None = None,
    author_profile_id: uuid.UUID | None = None,
    category_ids: str | None = Query(None, description="Comma-separated category IDs"),
    tag_ids: str | None = Query(None, description="Comma-separated tag IDs"),
    keyword: str | None = None,
) -> Any:
    """
    Get blog posts with filters (public API).
    Returns ListResponse with BlogPostResponse data including author, categories, and tags information.
    """
    # Build query
    statement = select(BlogPost).options(
        selectinload(BlogPost.author_profile),
        selectinload(BlogPost.categories),
        selectinload(BlogPost.tags),
    )

    # Apply filters
    filters = []

    if is_featured is not None:
        filters.append(BlogPost.is_featured == is_featured)

    if is_hot is not None:
        filters.append(BlogPost.is_hot == is_hot)

    if status:
        filters.append(BlogPost.status == status)

    if author_profile_id:
        filters.append(BlogPost.author_profile_id == author_profile_id)

    if keyword:
        keyword_filter = or_(
            BlogPost.title.ilike(f"%{keyword}%"),
            BlogPost.summary.ilike(f"%{keyword}%"),
            BlogPost.content.ilike(f"%{keyword}%"),
        )
        filters.append(keyword_filter)

    # Category filter
    if category_ids:
        try:
            cat_ids = [uuid.UUID(cid.strip()) for cid in category_ids.split(",")]
            category_subquery = select(BlogPostCategory.post_id).where(
                BlogPostCategory.category_id.in_(cat_ids)
            )
            filters.append(BlogPost.id.in_(category_subquery))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid category IDs format")

    # Tag filter
    if tag_ids:
        try:
            t_ids = [uuid.UUID(tid.strip()) for tid in tag_ids.split(",")]
            tag_subquery = select(BlogPostTag.post_id).where(
                BlogPostTag.tag_id.in_(t_ids)
            )
            filters.append(BlogPost.id.in_(tag_subquery))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid tag IDs format")

    if filters:
        statement = statement.where(and_(*filters))

    # Count query
    count_statement = select(func.count()).select_from(BlogPost)
    if filters:
        count_statement = count_statement.where(and_(*filters))
    count = session.exec(count_statement).one()

    # Execute main query
    statement = (
        statement.offset(offset).limit(limit).order_by(BlogPost.created_at.desc())
    )
    posts = session.exec(statement).unique().all()

    # Map to BlogPostResponse to ensure all relationships are properly serialized
    post_responses = [BlogPostResponse.model_validate(post) for post in posts]

    return ListResponse(data=post_responses, count=count)


@router.get("/posts/{post_id}", response_model=BlogPostResponse)
def get_blog_post(session: SessionDep, post_id: uuid.UUID) -> Any:
    """
    Get single blog post by ID (public API).
    """
    post = session.exec(
        select(BlogPost)
        .options(
            selectinload(BlogPost.author_profile),
            selectinload(BlogPost.categories),
            selectinload(BlogPost.tags),
        )
        .where(BlogPost.id == post_id)
    ).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Increment view count
    post.view_count += 1
    session.add(post)
    session.commit()
    session.refresh(post)

    return post


@router.post(
    "/posts",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=BlogPostResponse,
)
def create_blog_post(
    *,
    session: SessionDep,
    title: str = Form(...),
    slug: str = Form(...),
    summary: str | None = Form(None),
    content: str = Form(...),
    is_featured: bool = Form(False),
    is_hot: bool = Form(False),
    status: str = Form("draft"),
    published_at: str | None = Form(None),
    seo_title: str | None = Form(None),
    seo_description: str | None = Form(None),
    author_profile_id: str | None = Form(None),
    category_ids: str = Form(""),  # Comma-separated UUIDs
    tag_ids: str = Form(""),  # Comma-separated UUIDs
    thumbnail: UploadFile | None = File(None),
) -> Any:
    """
    Create new blog post with optional thumbnail upload (superuser only).
    """
    # Check if post with same slug exists
    existing = session.exec(select(BlogPost).where(BlogPost.slug == slug)).first()

    if existing:
        raise HTTPException(
            status_code=400, detail="Post with this slug already exists"
        )

    # Parse dates
    parsed_published_at = None
    if published_at:
        try:
            parsed_published_at = datetime.fromisoformat(
                published_at.replace("Z", "+00:00")
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid published_at format")

    # Parse UUIDs
    parsed_category_ids = []
    if category_ids.strip():
        try:
            parsed_category_ids = [
                uuid.UUID(cid.strip()) for cid in category_ids.split(",")
            ]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid category IDs format")

    parsed_tag_ids = []
    if tag_ids.strip():
        try:
            parsed_tag_ids = [uuid.UUID(tid.strip()) for tid in tag_ids.split(",")]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid tag IDs format")

    parsed_author_profile_id = None
    if author_profile_id:
        try:
            parsed_author_profile_id = uuid.UUID(author_profile_id)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid author profile ID format"
            )

    # Create post
    post = BlogPost(
        title=title,
        slug=slug,
        summary=summary,
        content=content,
        is_featured=is_featured,
        is_hot=is_hot,
        status=status,
        published_at=parsed_published_at,
        seo_title=seo_title,
        seo_description=seo_description,
        author_profile_id=parsed_author_profile_id,
        updated_at=datetime.utcnow(),
    )

    session.add(post)
    session.flush()  # Get the post ID

    # Handle thumbnail upload
    if thumbnail:
        try:
            file_info = file_upload_service.upload_compressed_image(
                file=thumbnail,
                upload_original=True,
                folder="blog-assets/thumbnails",
                filename=f"thumbnail_{post.id}.webp",
                type="image",
                max_size=5 * 1024 * 1024,
                quality=80,
                max_width=1920,
                max_height=1080,
                format="webp",
            )
            post.thumbnail_url = file_info.url
            post.thumbnail_compressed_url = file_info.compressed_url

        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=500, detail=f"Thumbnail upload failed: {str(e)}"
            )

    # Add categories
    for category_id in parsed_category_ids:
        category = session.get(BlogCategory, category_id)
        if category:
            post_category = BlogPostCategory(post_id=post.id, category_id=category_id)
            session.add(post_category)

    # Add tags
    for tag_id in parsed_tag_ids:
        tag = session.get(BlogTag, tag_id)
        if tag:
            post_tag = BlogPostTag(post_id=post.id, tag_id=tag_id)
            session.add(post_tag)

    session.commit()
    session.refresh(post)

    # Load relationships
    post = session.exec(
        select(BlogPost)
        .options(
            selectinload(BlogPost.author_profile),
            selectinload(BlogPost.categories),
            selectinload(BlogPost.tags),
        )
        .where(BlogPost.id == post.id)
    ).first()

    return post


@router.patch(
    "/posts/{post_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=BlogPostResponse,
)
def update_blog_post(
    *,
    session: SessionDep,
    post_id: uuid.UUID,
    title: str | None = Form(None),
    slug: str | None = Form(None),
    summary: str | None = Form(None),
    content: str | None = Form(None),
    is_featured: bool | None = Form(None),
    is_hot: bool | None = Form(None),
    status: str | None = Form(None),
    published_at: str | None = Form(None),
    seo_title: str | None = Form(None),
    seo_description: str | None = Form(None),
    author_profile_id: str | None = Form(None),
    category_ids: str | None = Form(None),  # Comma-separated UUIDs
    tag_ids: str | None = Form(None),  # Comma-separated UUIDs
    thumbnail: UploadFile | None = File(None),
) -> Any:
    """
    Update blog post with optional thumbnail upload (superuser only).
    """
    post = session.get(BlogPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Check for slug conflict if updating slug
    if slug and slug != post.slug:
        existing = session.exec(
            select(BlogPost).where(and_(BlogPost.id != post_id, BlogPost.slug == slug))
        ).first()

        if existing:
            raise HTTPException(
                status_code=400, detail="Post with this slug already exists"
            )

    # Update basic fields
    if title is not None:
        post.title = title
    if slug is not None:
        post.slug = slug
    if summary is not None:
        post.summary = summary
    if content is not None:
        post.content = content
    if is_featured is not None:
        post.is_featured = is_featured
    if is_hot is not None:
        post.is_hot = is_hot
    if status is not None:
        post.status = status
    if seo_title is not None:
        post.seo_title = seo_title
    if seo_description is not None:
        post.seo_description = seo_description

    # Parse dates
    if published_at is not None:
        try:
            post.published_at = datetime.fromisoformat(
                published_at.replace("Z", "+00:00")
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid published_at format")

    # Parse author profile ID
    if author_profile_id is not None:
        try:
            post.author_profile_id = (
                uuid.UUID(author_profile_id) if author_profile_id else None
            )
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid author profile ID format"
            )

    # Handle thumbnail upload
    if thumbnail:
        try:
            # Delete old thumbnail if exists
            # if post.thumbnail_url:
            #     delete_file(post.thumbnail_url)

            # Save new thumbnail
            file_info = file_upload_service.upload_compressed_image(
                file=thumbnail,
                folder="blog-assets/thumbnails",
                filename=f"thumbnail_{post_id}.webp",
                type="image",
                max_size=5 * 1024 * 1024,
                quality=80,
                max_width=1920,
                max_height=1080,
                format="webp",
            )
            post.thumbnail_url = file_info.url
            post.thumbnail_compressed_url = file_info.compressed_url
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Thumbnail upload failed: {str(e)}"
            )

    # Update categories if provided
    if category_ids is not None:
        # Remove existing categories
        session.exec(
            BlogPostCategory.__table__.delete().where(
                BlogPostCategory.post_id == post_id
            )
        )

        # Parse and add new categories
        if category_ids.strip():
            try:
                parsed_category_ids = [
                    uuid.UUID(cid.strip()) for cid in category_ids.split(",")
                ]
                for category_id in parsed_category_ids:
                    category = session.get(BlogCategory, category_id)
                    if category:
                        post_category = BlogPostCategory(
                            post_id=post.id, category_id=category_id
                        )
                        session.add(post_category)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid category IDs format"
                )

    # Update tags if provided
    if tag_ids is not None:
        # Remove existing tags
        session.exec(
            BlogPostTag.__table__.delete().where(BlogPostTag.post_id == post_id)
        )

        # Parse and add new tags
        if tag_ids.strip():
            try:
                parsed_tag_ids = [uuid.UUID(tid.strip()) for tid in tag_ids.split(",")]
                for tag_id in parsed_tag_ids:
                    tag = session.get(BlogTag, tag_id)
                    if tag:
                        post_tag = BlogPostTag(post_id=post.id, tag_id=tag_id)
                        session.add(post_tag)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid tag IDs format")

    post.updated_at = datetime.utcnow()
    session.add(post)
    session.commit()
    session.refresh(post)

    # Load relationships
    post = session.exec(
        select(BlogPost)
        .options(
            selectinload(BlogPost.author_profile),
            selectinload(BlogPost.categories),
            selectinload(BlogPost.tags),
        )
        .where(BlogPost.id == post.id)
    ).first()

    return post


@router.delete(
    "/posts/{post_id}",
    dependencies=[Depends(get_current_active_superuser)],
)
def delete_blog_post(session: SessionDep, post_id: uuid.UUID) -> Message:
    """
    Delete blog post (superuser only).
    """
    post = session.get(BlogPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Delete thumbnail file if exists
    if post.thumbnail_url:
        file_upload_service.delete_file(post.thumbnail_url)

    session.delete(post)
    session.commit()
    return Message(message="Post deleted successfully")
