from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.utils.time import utcnow

# ----- review outcomes (ReviewHistory.outcome)
OUTCOMES = ("approved", "changes_required", "outdated", "needs_clarification")

# ----- conflict vocabulary
CONFLICT_TYPES = ("value_mismatch", "deadline_or_date", "limit_or_threshold", "policy_contradiction", "version_change", "other")
ASSESSMENTS = ("potential_conflict", "needs_review")  # what the AI said; never "confirmed"
DECISIONS = ("pending", "confirmed", "not_conflict", "needs_review")  # what a person decided
KIND_CROSS_DOCUMENT = "cross_document"
KIND_CROSS_VERSION = "cross_version"
REPORT_RUNNING, REPORT_COMPLETED, REPORT_FAILED = "running", "completed", "failed"


class DocumentReview(Base):
    """Review schedule of one LOGICAL document (not of a version): reviews are about whether the content is still right, and
    a new upload does not reset or move the schedule. The version that was reviewed is recorded in ReviewHistory.
    Status (upcoming / due / overdue ...) is derived from the dates on read; it is never stored."""

    __tablename__ = "document_reviews"
    __table_args__ = (
        UniqueConstraint("document_id", name="uq_document_reviews_document"),
        Index("ix_document_reviews_next", "next_review_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    interval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    assigned_reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    in_review: Mapped[bool] = mapped_column(Boolean, default=False)
    in_review_started_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    in_review_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    last_outcome: Mapped[str | None] = mapped_column(String(30), nullable=True)
    last_reviewed_version_id: Mapped[int | None] = mapped_column(ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ReviewHistory(Base):
    """Append-only: one row per completed review. Never updated when versions are uploaded."""

    __tablename__ = "document_review_history"
    __table_args__ = (Index("ix_review_history_document", "document_id", "reviewed_at"), Index("ix_review_history_reviewed_at", "reviewed_at"))

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    version_id: Mapped[int | None] = mapped_column(ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True)
    version_number: Mapped[int | None] = mapped_column(Integer, nullable=True)  # kept even if the version row were ever removed
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    outcome: Mapped[str] = mapped_column(String(30))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_next_review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_review_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class ConflictReport(Base):
    """One user-initiated analysis run (a document or a collection)."""

    __tablename__ = "conflict_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    scope_document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True)
    scope_collection_id: Mapped[int | None] = mapped_column(ForeignKey("collections.id", ondelete="CASCADE"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default=REPORT_RUNNING)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    passages_examined: Mapped[int] = mapped_column(Integer, default=0)
    pairs_examined: Mapped[int] = mapped_column(Integer, default=0)
    pairs_unparsed: Mapped[int] = mapped_column(Integer, default=0)
    pairs_compatible: Mapped[int] = mapped_column(Integer, default=0)
    findings_created: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DocumentConflict(Base):
    """A POTENTIAL conflict between two exact passages of two exact versions. Evidence is stored by reference (document,
    version, chunk, page) plus a copy of the passage text as it was; the text is only ever shown to users who can still read
    both documents."""

    __tablename__ = "document_conflicts"
    __table_args__ = (UniqueConstraint("pair_key", name="uq_document_conflicts_pair"), Index("ix_document_conflicts_a_doc", "a_document_id"), Index("ix_document_conflicts_b_doc", "b_document_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("conflict_reports.id", ondelete="CASCADE"), index=True)
    pair_key: Mapped[str] = mapped_column(String(40))  # "<min chunk id>-<max chunk id>": the same evidence is never stored twice
    kind: Mapped[str] = mapped_column(String(20), default=KIND_CROSS_DOCUMENT)
    conflict_type: Mapped[str] = mapped_column(String(30), default="other")
    assessment: Mapped[str] = mapped_column(String(20), default="needs_review")
    explanation: Mapped[str] = mapped_column(Text)
    a_document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    a_version_id: Mapped[int | None] = mapped_column(ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True)
    a_chunk_id: Mapped[int | None] = mapped_column(ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True)
    a_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    a_excerpt: Mapped[str] = mapped_column(Text)
    b_document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    b_version_id: Mapped[int | None] = mapped_column(ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True)
    b_chunk_id: Mapped[int | None] = mapped_column(ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True)
    b_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    b_excerpt: Mapped[str] = mapped_column(Text)
    quotes_verified: Mapped[bool] = mapped_column(Boolean, default=False)  # the model's quoted evidence was found verbatim in both passages
    review_status: Mapped[str] = mapped_column(String(20), default="pending")
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ConflictDecision(Base):
    """Append-only record of every reviewer decision on a finding."""

    __tablename__ = "conflict_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    conflict_id: Mapped[int] = mapped_column(ForeignKey("document_conflicts.id", ondelete="CASCADE"), index=True)
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decision: Mapped[str] = mapped_column(String(20))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
