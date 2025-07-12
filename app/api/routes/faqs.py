import uuid
from typing import Any, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select, func, or_, and_
from sqlalchemy.orm import selectinload

from app.api.deps import (
    SessionDep,
    get_current_active_superuser,
)
from app.models import (
    FAQCategory,
    FAQ,
)
from app.schemas.base import Message, ListResponse
from app.schemas.faqs import (
    FAQCategoryCreate,
    FAQCategoryUpdate,
    FAQCategoryResponse,
    FAQCreate,
    FAQUpdate,
    FAQResponse,
)
import logging

logger = logging.getLogger("faqs")

router = APIRouter(prefix="/faqs", tags=["faqs"])


# --- FAQ Categories APIs ---


@router.get("/categories", response_model=ListResponse)
def get_faq_categories(session: SessionDep, offset: int = 0, limit: int = 100) -> Any:
    """
    Get all FAQ categories (public API).
    """
    count_statement = select(func.count()).select_from(FAQCategory)
    count = session.exec(count_statement).one()

    statement = (
        select(FAQCategory)
        .where(FAQCategory.is_active == True)
        .order_by(FAQCategory.order_index, FAQCategory.name)
        .offset(offset)
        .limit(limit)
    )
    categories = session.exec(statement).all()

    return ListResponse(data=categories, count=count)


@router.post(
    "/categories",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=FAQCategoryResponse,
)
def create_faq_category(*, session: SessionDep, category_in: FAQCategoryCreate) -> Any:
    """
    Create new FAQ category (superuser only).
    """
    # Check if category with same name exists
    existing = session.exec(
        select(FAQCategory).where(FAQCategory.name == category_in.name)
    ).first()

    if existing:
        raise HTTPException(
            status_code=400, detail="Category with this name already exists"
        )

    category = FAQCategory(**category_in.model_dump(), updated_at=datetime.utcnow())
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


@router.patch(
    "/categories/{category_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=FAQCategoryResponse,
)
def update_faq_category(
    *, session: SessionDep, category_id: uuid.UUID, category_in: FAQCategoryUpdate
) -> Any:
    """
    Update FAQ category (superuser only).
    """
    category = session.get(FAQCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check for conflicts if updating name
    if category_in.name:
        existing = session.exec(
            select(FAQCategory).where(
                and_(
                    FAQCategory.id != category_id,
                    FAQCategory.name == category_in.name,
                )
            )
        ).first()

        if existing:
            raise HTTPException(
                status_code=400, detail="Category with this name already exists"
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
def delete_faq_category(session: SessionDep, category_id: uuid.UUID) -> Message:
    """
    Delete FAQ category (superuser only).
    """
    category = session.get(FAQCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    session.delete(category)
    session.commit()
    return Message(message="Category deleted successfully")


# --- FAQ APIs ---


@router.get("/", response_model=ListResponse)
def get_faqs(
    session: SessionDep,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category_id: uuid.UUID | None = None,
    is_active: bool | None = None,
    keyword: str | None = None,
) -> Any:
    """
    Get FAQs with filters (public API).
    """
    # Build query
    statement = select(FAQ).options(selectinload(FAQ.category))

    # Apply filters
    filters = []

    if is_active is not None:
        filters.append(FAQ.is_active == is_active)
    else:
        # Default: only show active FAQs for public API
        filters.append(FAQ.is_active == True)

    if category_id:
        filters.append(FAQ.faq_category_id == category_id)

    if keyword:
        keyword_filter = or_(
            FAQ.question.ilike(f"%{keyword}%"),
            FAQ.answer.ilike(f"%{keyword}%"),
            FAQ.addition_info.ilike(f"%{keyword}%"),
        )
        filters.append(keyword_filter)

    if filters:
        statement = statement.where(and_(*filters))

    # Count query
    count_statement = select(func.count()).select_from(FAQ)
    if filters:
        count_statement = count_statement.where(and_(*filters))
    count = session.exec(count_statement).one()

    # Execute main query
    statement = (
        statement.offset(offset)
        .limit(limit)
        .order_by(FAQ.order_index, FAQ.created_at.desc())
    )
    faqs = session.exec(statement).unique().all()

    return ListResponse(data=faqs, count=count)


@router.get("/{faq_id}", response_model=FAQResponse)
def get_faq(session: SessionDep, faq_id: uuid.UUID) -> Any:
    """
    Get single FAQ by ID (public API).
    """
    faq = session.exec(
        select(FAQ).options(selectinload(FAQ.category)).where(FAQ.id == faq_id)
    ).first()

    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")

    return faq


@router.post(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=FAQResponse,
)
def create_faq(*, session: SessionDep, faq_in: FAQCreate) -> Any:
    """
    Create new FAQ (superuser only).
    """
    # Validate category exists if provided
    if faq_in.faq_category_id:
        category = session.get(FAQCategory, faq_in.faq_category_id)
        if not category:
            raise HTTPException(status_code=400, detail="Category not found")

    faq = FAQ(**faq_in.model_dump(), updated_at=datetime.utcnow())
    session.add(faq)
    session.commit()
    session.refresh(faq)

    # Load relationships
    faq = session.exec(
        select(FAQ).options(selectinload(FAQ.category)).where(FAQ.id == faq.id)
    ).first()

    return faq


@router.patch(
    "/{faq_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=FAQResponse,
)
def update_faq(*, session: SessionDep, faq_id: uuid.UUID, faq_in: FAQUpdate) -> Any:
    """
    Update FAQ (superuser only).
    """
    faq = session.get(FAQ, faq_id)
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")

    # Validate category exists if provided
    if faq_in.faq_category_id:
        category = session.get(FAQCategory, faq_in.faq_category_id)
        if not category:
            raise HTTPException(status_code=400, detail="Category not found")

    faq_data = faq_in.model_dump(exclude_unset=True)
    faq_data["updated_at"] = datetime.utcnow()
    faq.sqlmodel_update(faq_data)
    session.add(faq)
    session.commit()
    session.refresh(faq)

    # Load relationships
    faq = session.exec(
        select(FAQ).options(selectinload(FAQ.category)).where(FAQ.id == faq.id)
    ).first()

    return faq


@router.delete(
    "/{faq_id}",
    dependencies=[Depends(get_current_active_superuser)],
)
def delete_faq(session: SessionDep, faq_id: uuid.UUID) -> Message:
    """
    Delete FAQ (superuser only).
    """
    faq = session.get(FAQ, faq_id)
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")

    session.delete(faq)
    session.commit()
    return Message(message="FAQ deleted successfully")
