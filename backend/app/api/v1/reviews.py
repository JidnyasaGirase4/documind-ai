from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import page_of
from app.schemas.reviews import ReviewCompleteIn, ReviewHistoryOut, ReviewOut, ReviewScheduleIn, ReviewStatus, ReviewSummaryOut
from app.services import review_service

router = APIRouter(tags=["reviews"])


# ---------------------------------------------------------------- dashboard
@router.get("/reviews/summary", response_model=ReviewSummaryOut)
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Counts computed from the review dates of documents the caller can read, as of today (UTC)."""
    return review_service.summary(db, user)


@router.get("/reviews")
def list_reviews(
    status: ReviewStatus | None = None,
    collection_id: int | None = None,
    due_before: date | None = None,
    due_after: date | None = None,
    reviewer_id: int | None = Query(None, ge=1, description="Assigned reviewer"),
    assigned_to_me: bool = False,
    search: str | None = Query(None, max_length=255),
    sort: Literal["due", "title"] = "due",
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Documents with a review record (scheduled, in review or already reviewed) that the caller can read."""
    items, total = review_service.list_reviews(
        db, user, status=status, collection_id=collection_id, due_before=due_before, due_after=due_after, reviewer_id=user.id if assigned_to_me else reviewer_id,
        search=search, page=page, page_size=page_size, sort=sort,
    )
    return page_of(items, total, page, page_size)


@router.get("/reviews/overdue")
def list_overdue(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items, total = review_service.list_reviews(db, user, status="overdue", collection_id=None, due_before=None, due_after=None, reviewer_id=None, search=None, page=page, page_size=page_size)
    return page_of(items, total, page, page_size)


# ------------------------------------------------------------- one document
@router.get("/documents/{document_id}/review", response_model=ReviewOut)
def get_review(document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return review_service.get_review(db, user, document_id)


@router.put("/documents/{document_id}/review", response_model=ReviewOut)
def configure_review(document_id: int, body: ReviewScheduleIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Owner/editor: set the interval, next review date, assigned reviewer and notes."""
    return review_service.configure(db, user, document_id, body)


@router.delete("/documents/{document_id}/review", response_model=ReviewOut)
def clear_review(document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Owner/editor: removes the schedule. Review history is kept."""
    return review_service.unschedule(db, user, document_id)


@router.post("/documents/{document_id}/review/start", response_model=ReviewOut)
def start_review(document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return review_service.start(db, user, document_id)


@router.post("/documents/{document_id}/review/complete", response_model=ReviewOut)
def complete_review(document_id: int, body: ReviewCompleteIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Owner/editor: records the outcome. The reviewer is the signed-in user."""
    return review_service.complete(db, user, document_id, body)


@router.get("/documents/{document_id}/review/history")
def review_history(document_id: int, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items, total = review_service.history(db, user, document_id, page, page_size)
    return page_of([i.model_dump(mode="json") for i in items], total, page, page_size)
