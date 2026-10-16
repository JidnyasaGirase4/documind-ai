from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import UTCDateTime

Outcome = Literal["approved", "changes_required", "outdated", "needs_clarification"]
ReviewStatus = Literal["not_scheduled", "upcoming", "due", "overdue", "in_review", "reviewed"]


class PersonOut(BaseModel):
    id: int
    name: str


class ReviewScheduleIn(BaseModel):
    """Fields that are not sent are left as they are. `interval_days` is the repeat interval used to propose the next date
    after each review; `next_review_date` is the date the next review is due (today or later, at most 10 years ahead)."""

    interval_days: int | None = Field(None, ge=1, le=3650)
    next_review_date: date | None = None
    assigned_reviewer_id: int | None = Field(None, ge=1)
    notes: str | None = Field(None, max_length=2000)

    @field_validator("notes")
    @classmethod
    def _notes(cls, v: str | None) -> str | None:
        return (v or "").strip() or None


class ReviewCompleteIn(BaseModel):
    outcome: Outcome
    notes: str | None = Field(None, max_length=4000)
    next_review_date: date | None = None  # default: today + interval_days, or no further review when there is no interval

    @field_validator("notes")
    @classmethod
    def _notes(cls, v: str | None) -> str | None:
        return (v or "").strip() or None


class ReviewOut(BaseModel):
    document_id: int
    title: str
    version_number: int | None = None  # current version
    status: ReviewStatus
    interval_days: int | None = None
    next_review_date: date | None = None
    days_until_due: int | None = None  # negative when overdue
    assigned_reviewer: PersonOut | None = None
    notes: str | None = None
    in_review: bool = False
    last_reviewed_at: UTCDateTime | None = None
    last_reviewed_by: PersonOut | None = None
    last_outcome: str | None = None
    last_reviewed_version_number: int | None = None
    version_changed_since_review: bool = False  # a newer version is current than the one last reviewed
    role: str = "viewer"


class ReviewHistoryOut(BaseModel):
    id: int
    document_id: int
    version_id: int | None = None
    version_number: int | None = None
    reviewer: PersonOut | None = None
    reviewed_at: UTCDateTime
    outcome: str
    notes: str | None = None
    previous_next_review_date: date | None = None
    next_review_date: date | None = None


class ReviewSummaryOut(BaseModel):
    today: date
    due_soon_days: int
    scheduled: int  # documents with a next review date
    upcoming: int
    due: int
    overdue: int
    in_review: int
    completed_last_30_days: int
    recent: list[dict]  # most recent completed reviews of documents the caller can read
