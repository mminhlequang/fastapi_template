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
    SupportTicketCategory,
    SupportTicket,
    SupportTicketComment,
    SupportTicketAttachment,
    User,
)
from app.schemas.base import Message, ListResponse
from app.schemas.support_tickets import (
    SupportTicketCategoryCreate,
    SupportTicketCategoryUpdate,
    SupportTicketCategoryResponse,
    SupportTicketCreate,
    SupportTicketUpdate,
    SupportTicketResponse,
    SupportTicketCommentCreate,
    SupportTicketCommentUpdate,
    SupportTicketCommentResponse,
    SupportTicketAttachmentCreate,
    SupportTicketAttachmentResponse,
)
from app.utils.file_uploads import file_upload_service
import logging

logger = logging.getLogger("support_tickets")

router = APIRouter(prefix="/support-tickets", tags=["support-tickets"])


# --- Support Ticket Categories APIs ---


@router.get("/categories", response_model=ListResponse)
def get_support_ticket_categories(
    session: SessionDep,
    offset: int = 0,
    limit: int = 100,
    is_internal: bool | None = Query(None, description="Filter by internal status"),
) -> Any:
    """
    Get support ticket categories with optional filters.
    """
    # Build filters
    filters = [SupportTicketCategory.is_active == True]

    # Filter by is_internal if provided
    if is_internal is not None:
        filters.append(SupportTicketCategory.is_internal == is_internal)

    count_statement = (
        select(func.count()).select_from(SupportTicketCategory).where(and_(*filters))
    )
    count = session.exec(count_statement).one()

    statement = (
        select(SupportTicketCategory)
        .where(and_(*filters))
        .offset(offset)
        .limit(limit)
        .order_by(SupportTicketCategory.name)
    )
    categories = session.exec(statement).all()

    return ListResponse(data=categories, count=count)


@router.post(
    "/categories",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=SupportTicketCategoryResponse,
)
def create_support_ticket_category(
    *, session: SessionDep, category_in: SupportTicketCategoryCreate
) -> Any:
    """
    Create new support ticket category (superuser only).
    """
    # Check if category with same name exists
    existing = session.exec(
        select(SupportTicketCategory).where(
            SupportTicketCategory.name == category_in.name
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=400, detail="Category with this name already exists"
        )

    category = SupportTicketCategory(
        **category_in.model_dump(), updated_at=datetime.utcnow()
    )
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


@router.patch(
    "/categories/{category_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=SupportTicketCategoryResponse,
)
def update_support_ticket_category(
    *,
    session: SessionDep,
    category_id: uuid.UUID,
    category_in: SupportTicketCategoryUpdate,
) -> Any:
    """
    Update support ticket category (superuser only).
    """
    category = session.get(SupportTicketCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check for name conflict if updating name
    if category_in.name and category_in.name != category.name:
        existing = session.exec(
            select(SupportTicketCategory).where(
                and_(
                    SupportTicketCategory.id != category_id,
                    SupportTicketCategory.name == category_in.name,
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
def delete_support_ticket_category(
    session: SessionDep, category_id: uuid.UUID
) -> Message:
    """
    Delete support ticket category (superuser only).
    """
    category = session.get(SupportTicketCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    session.delete(category)
    session.commit()
    return Message(message="Category deleted successfully")


# --- Support Tickets APIs ---


@router.get("/tickets", response_model=ListResponse)
def get_support_tickets(
    session: SessionDep,
    current_user: CurrentUser,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = None,
    priority: str | None = None,
    category_id: uuid.UUID | None = None,
    assigned_to: uuid.UUID | None = None,
    keyword: str | None = None,
) -> Any:
    """
    Get support tickets with filters.
    Regular users see only their own tickets.
    Superusers see all tickets.
    """
    # Build base query with relationships
    statement = select(SupportTicket).options(
        selectinload(SupportTicket.category),
        selectinload(SupportTicket.user),
        selectinload(SupportTicket.assigned_user),
        selectinload(SupportTicket.comments),
        selectinload(SupportTicket.attachments),
    )

    # Apply filters
    filters = []

    # Non-superusers can only see their own tickets
    if not current_user.is_superuser:
        filters.append(SupportTicket.user_id == current_user.id)

    if status:
        filters.append(SupportTicket.status == status)

    if priority:
        filters.append(SupportTicket.priority == priority)

    if category_id:
        filters.append(SupportTicket.ticket_category_id == category_id)

    if assigned_to:
        filters.append(SupportTicket.assigned_to == assigned_to)

    if keyword:
        keyword_filter = or_(
            SupportTicket.subject.ilike(f"%{keyword}%"),
            SupportTicket.description.ilike(f"%{keyword}%"),
        )
        filters.append(keyword_filter)

    if filters:
        statement = statement.where(and_(*filters))

    # Count query
    count_statement = select(func.count()).select_from(SupportTicket)
    if filters:
        count_statement = count_statement.where(and_(*filters))
    count = session.exec(count_statement).one()

    # Execute main query
    statement = (
        statement.offset(offset).limit(limit).order_by(SupportTicket.created_at.desc())
    )
    tickets = session.exec(statement).unique().all()

    # Map to SupportTicketResponse to ensure all relationships are properly serialized
    ticket_responses = [
        SupportTicketResponse.model_validate(ticket) for ticket in tickets
    ]

    return ListResponse(data=ticket_responses, count=count)


@router.get("/tickets/{ticket_id}", response_model=SupportTicketResponse)
def get_support_ticket(
    session: SessionDep, current_user: CurrentUser, ticket_id: uuid.UUID
) -> Any:
    """
    Get single support ticket by ID.
    Regular users can only access their own tickets.
    """
    ticket = session.exec(
        select(SupportTicket)
        .options(
            selectinload(SupportTicket.category),
            selectinload(SupportTicket.user),
            selectinload(SupportTicket.assigned_user),
            selectinload(SupportTicket.comments).selectinload(
                SupportTicketComment.attachments
            ),
            selectinload(SupportTicket.attachments),
        )
        .where(SupportTicket.id == ticket_id)
    ).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Check permission
    if not current_user.is_superuser and ticket.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    return ticket


@router.post("/tickets_by_guest", response_model=SupportTicketResponse)
def create_support_ticket_by_guest(
    *, session: SessionDep, ticket_in: SupportTicketCreate
) -> Any:
    """
    Create new support ticket.
    """
    ticket = SupportTicket(
        **ticket_in.model_dump(),
        updated_at=datetime.utcnow(),
    )

    session.add(ticket)
    session.commit()
    session.refresh(ticket)

    # Load relationships
    ticket = session.exec(
        select(SupportTicket)
        .options(
            selectinload(SupportTicket.category),
            selectinload(SupportTicket.assigned_user),
            selectinload(SupportTicket.comments),
            selectinload(SupportTicket.attachments),
        )
        .where(SupportTicket.id == ticket.id)
    ).first()

    return ticket


@router.post("/tickets", response_model=SupportTicketResponse)
def create_support_ticket(
    *, session: SessionDep, current_user: CurrentUser, ticket_in: SupportTicketCreate
) -> Any:
    """
    Create new support ticket.
    """
    ticket = SupportTicket(
        **ticket_in.model_dump(),
        user_id=current_user.id,
        updated_at=datetime.utcnow(),
    )

    session.add(ticket)
    session.commit()
    session.refresh(ticket)

    # Load relationships
    ticket = session.exec(
        select(SupportTicket)
        .options(
            selectinload(SupportTicket.category),
            selectinload(SupportTicket.user),
            selectinload(SupportTicket.assigned_user),
            selectinload(SupportTicket.comments),
            selectinload(SupportTicket.attachments),
        )
        .where(SupportTicket.id == ticket.id)
    ).first()

    return ticket


@router.patch("/tickets/{ticket_id}", response_model=SupportTicketResponse)
def update_support_ticket(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    ticket_id: uuid.UUID,
    ticket_in: SupportTicketUpdate,
) -> Any:
    """
    Update support ticket.
    Regular users can only update their own tickets (limited fields).
    Superusers can update all fields including assignment.
    """
    ticket = session.get(SupportTicket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Check permission
    if not current_user.is_superuser and ticket.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Regular users have limited update permissions
    if not current_user.is_superuser:
        # Users can only update certain fields and cannot assign tickets
        allowed_updates = {
            k: v
            for k, v in ticket_in.model_dump(exclude_unset=True).items()
            if k
            in ["subject", "description", "status", "priority", "ticket_category_id"]
        }
        ticket_data = allowed_updates
    else:
        # Superusers can update all fields
        ticket_data = ticket_in.model_dump(exclude_unset=True)

    ticket_data["updated_at"] = datetime.utcnow()
    ticket.sqlmodel_update(ticket_data)
    session.add(ticket)
    session.commit()
    session.refresh(ticket)

    # Load relationships
    ticket = session.exec(
        select(SupportTicket)
        .options(
            selectinload(SupportTicket.category),
            selectinload(SupportTicket.user),
            selectinload(SupportTicket.assigned_user),
            selectinload(SupportTicket.comments),
            selectinload(SupportTicket.attachments),
        )
        .where(SupportTicket.id == ticket.id)
    ).first()

    return ticket


@router.delete("/tickets/{ticket_id}")
def delete_support_ticket(
    session: SessionDep, current_user: CurrentUser, ticket_id: uuid.UUID
) -> Message:
    """
    Delete support ticket.
    Regular users can only delete their own tickets.
    """
    ticket = session.get(SupportTicket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Check permission
    if not current_user.is_superuser and ticket.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    session.delete(ticket)
    session.commit()
    return Message(message="Ticket deleted successfully")


# --- Support Ticket Comments APIs ---


@router.get("/tickets/{ticket_id}/comments", response_model=ListResponse)
def get_ticket_comments(
    session: SessionDep,
    current_user: CurrentUser,
    ticket_id: uuid.UUID,
    offset: int = 0,
    limit: int = 100,
) -> Any:
    """
    Get comments for a support ticket.
    Internal comments are only visible to superusers.
    """
    # First check if user has access to the ticket
    ticket = session.get(SupportTicket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if not current_user.is_superuser and ticket.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Build query
    statement = (
        select(SupportTicketComment)
        .where(SupportTicketComment.ticket_id == ticket_id)
        .options(
            selectinload(SupportTicketComment.user),
            selectinload(SupportTicketComment.attachments),
        )
    )

    # Hide internal comments from regular users
    if not current_user.is_superuser:
        statement = statement.where(SupportTicketComment.is_internal == False)

    count_statement = (
        select(func.count())
        .select_from(SupportTicketComment)
        .where(SupportTicketComment.ticket_id == ticket_id)
    )
    if not current_user.is_superuser:
        count_statement = count_statement.where(
            SupportTicketComment.is_internal == False
        )

    count = session.exec(count_statement).one()

    statement = (
        statement.offset(offset)
        .limit(limit)
        .order_by(SupportTicketComment.created_at.asc())
    )
    comments = session.exec(statement).unique().all()

    comment_responses = [
        SupportTicketCommentResponse.model_validate(comment) for comment in comments
    ]

    return ListResponse(data=comment_responses, count=count)


@router.post(
    "/tickets/{ticket_id}/comments", response_model=SupportTicketCommentResponse
)
def create_ticket_comment(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    ticket_id: uuid.UUID,
    comment_in: SupportTicketCommentCreate,
) -> Any:
    """
    Create new comment for a ticket.
    """
    # Check if ticket exists and user has access
    ticket = session.get(SupportTicket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if not current_user.is_superuser and ticket.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Regular users cannot create internal comments
    if not current_user.is_superuser and comment_in.is_internal:
        raise HTTPException(
            status_code=403, detail="Only staff can create internal comments"
        )

    comment = SupportTicketComment(
        **comment_in.model_dump(),
        user_id=current_user.id,
        updated_at=datetime.utcnow(),
    )

    session.add(comment)
    session.commit()
    session.refresh(comment)

    # Load relationships
    comment = session.exec(
        select(SupportTicketComment)
        .options(
            selectinload(SupportTicketComment.user),
            selectinload(SupportTicketComment.attachments),
        )
        .where(SupportTicketComment.id == comment.id)
    ).first()

    return comment


@router.patch("/comments/{comment_id}", response_model=SupportTicketCommentResponse)
def update_ticket_comment(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    comment_id: uuid.UUID,
    comment_in: SupportTicketCommentUpdate,
) -> Any:
    """
    Update support ticket comment.
    Users can only edit their own comments.
    """
    comment = session.get(SupportTicketComment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Check permission
    if not current_user.is_superuser and comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Regular users cannot change internal status
    if not current_user.is_superuser and comment_in.is_internal is not None:
        raise HTTPException(
            status_code=403, detail="Only staff can change internal status"
        )

    comment_data = comment_in.model_dump(exclude_unset=True)
    comment_data["updated_at"] = datetime.utcnow()
    comment.sqlmodel_update(comment_data)
    session.add(comment)
    session.commit()
    session.refresh(comment)

    # Load relationships
    comment = session.exec(
        select(SupportTicketComment)
        .options(
            selectinload(SupportTicketComment.user),
            selectinload(SupportTicketComment.attachments),
        )
        .where(SupportTicketComment.id == comment.id)
    ).first()

    return comment


@router.delete("/comments/{comment_id}")
def delete_ticket_comment(
    session: SessionDep, current_user: CurrentUser, comment_id: uuid.UUID
) -> Message:
    """
    Delete support ticket comment.
    Users can only delete their own comments.
    """
    comment = session.get(SupportTicketComment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Check permission
    if not current_user.is_superuser and comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    session.delete(comment)
    session.commit()
    return Message(message="Comment deleted successfully")


# --- Support Ticket Attachments APIs ---


@router.post(
    "/tickets/{ticket_id}/attachments", response_model=SupportTicketAttachmentResponse
)
def upload_ticket_attachment(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    ticket_id: uuid.UUID,
    comment_id: uuid.UUID | None = Form(None),
    attachment: UploadFile = File(...),
) -> Any:
    """
    Upload attachment for a ticket or comment.
    """
    # Check if ticket exists and user has access
    ticket = session.get(SupportTicket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if not current_user.is_superuser and ticket.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # If comment_id is provided, check if it belongs to the ticket
    if comment_id:
        comment = session.get(SupportTicketComment, comment_id)
        if not comment or comment.ticket_id != ticket_id:
            raise HTTPException(
                status_code=400, detail="Invalid comment ID for this ticket"
            )

    try:
        # Upload file
        file_info = file_upload_service.upload_file(
            file=attachment,
            folder="support-ticket-attachments",
            filename=f"{ticket_id}_{uuid.uuid4()}.{attachment.filename.split('.')[-1]}",
            type="document",
            max_size=10 * 1024 * 1024,  # 10MB limit
        )

        # Create attachment record
        attachment_record = SupportTicketAttachment(
            ticket_id=ticket_id,
            comment_id=comment_id,
            file_url=file_info.url,
            file_name=attachment.filename,
            file_size=attachment.size,
            file_type=attachment.content_type,
        )

        session.add(attachment_record)
        session.commit()
        session.refresh(attachment_record)

        return attachment_record

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.delete("/attachments/{attachment_id}")
def delete_ticket_attachment(
    session: SessionDep, current_user: CurrentUser, attachment_id: uuid.UUID
) -> Message:
    """
    Delete support ticket attachment.
    """
    attachment = session.get(SupportTicketAttachment, attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    # Check permission via ticket
    ticket = session.get(SupportTicket, attachment.ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Associated ticket not found")

    if not current_user.is_superuser and ticket.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Delete file from storage
    try:
        file_upload_service.delete_file(attachment.file_url)
    except Exception as e:
        logger.warning(f"Failed to delete file {attachment.file_url}: {str(e)}")

    session.delete(attachment)
    session.commit()
    return Message(message="Attachment deleted successfully")
