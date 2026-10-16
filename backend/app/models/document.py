from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.utils.time import utcnow

# Document.processing_status values
STATUS_UPLOADED = "uploaded"  # legacy: documents created before the job queue existed
STATUS_QUEUED = "queued"
STATUS_PROCESSING = "processing"
STATUS_READY = "ready"
STATUS_FAILED = "failed"
ALL_STATUSES = (STATUS_UPLOADED, STATUS_QUEUED, STATUS_PROCESSING, STATUS_READY, STATUS_FAILED)

# ProcessingJob.status values
JOB_QUEUED = "queued"
JOB_PROCESSING = "processing"
JOB_COMPLETED = "completed"
JOB_FAILED = "failed"
ACTIVE_JOB_STATUSES = (JOB_QUEUED, JOB_PROCESSING)


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (Index("ix_documents_user_status", "user_id", "processing_status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(512))  # internal; never returned by the API
    file_size: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String(100))
    processing_status: Mapped[str] = mapped_column(String(20), default=STATUS_UPLOADED)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # The version whose file, text and vectors are used by default (preview, search, RAG). It only ever points at a
    # version whose processing finished (or at the first version while that is still being processed).
    current_version_id: Mapped[int | None] = mapped_column(ForeignKey("document_versions.id", ondelete="SET NULL", use_alter=True, name="fk_documents_current_version"), nullable=True, index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    versions: Mapped[list["DocumentVersion"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True, foreign_keys="DocumentVersion.document_id", order_by="DocumentVersion.version_number"
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan", passive_deletes=True)
    jobs: Mapped[list["ProcessingJob"]] = relationship(back_populates="document", cascade="all, delete-orphan", passive_deletes=True)


class DocumentVersion(Base):
    """One immutable upload of a logical document. `storage_path` is never overwritten; restoring an old version copies its
    file into a NEW version. Text lives in the version's chunks (and can be re-extracted from the file)."""

    __tablename__ = "document_versions"
    __table_args__ = (UniqueConstraint("document_id", "version_number", name="uq_document_versions_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(512))  # internal; never returned by the API
    file_size: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String(100))
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    total_pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processing_status: Mapped[str] = mapped_column(String(20), default=STATUS_QUEUED)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    change_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    restored_from_version_id: Mapped[int | None] = mapped_column(ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    document: Mapped[Document] = relationship(back_populates="versions", foreign_keys=[document_id])


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("ix_chunks_document_index", "document_id", "chunk_index"),
        Index("ft_chunks_text", "extracted_text", mysql_prefix="FULLTEXT"),  # keyword search (migration 0006)
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    version_id: Mapped[int | None] = mapped_column(ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=True, index=True)  # the exact version this text came from
    chunk_index: Mapped[int] = mapped_column(Integer)
    page_number: Mapped[int] = mapped_column(Integer)
    extracted_text: Mapped[str] = mapped_column(Text)
    vector_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)  # id of the vector in Chroma
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    document: Mapped[Document] = relationship(back_populates="chunks")


class ProcessingJob(Base):
    """One run of the extract -> chunk -> embed -> index pipeline. The table doubles as the persistent work queue:
    the worker claims `queued` rows atomically, so a job survives restarts and is never run by two workers."""

    __tablename__ = "processing_jobs"
    __table_args__ = (
        # At most one active (queued/processing) job per document: `active_key` holds the document id while the job is
        # active and NULL afterwards (MySQL allows many NULLs in a unique index).
        UniqueConstraint("active_key", name="uq_processing_jobs_active_key"),
        Index("ix_processing_jobs_queue", "status", "next_run_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    version_id: Mapped[int | None] = mapped_column(ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=True, index=True)  # the version this job processes
    status: Mapped[str] = mapped_column(String(20), default=JOB_QUEUED)
    stage: Mapped[str | None] = mapped_column(String(30), nullable=True)  # extracting | chunking | embedding | indexing
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100, derived from the stage actually reached
    retry_count: Mapped[int] = mapped_column(Integer, default=0)  # manual retries before this job
    attempts: Mapped[int] = mapped_column(Integer, default=0)  # worker attempts of this job (automatic retries)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # backoff before the next attempt
    locked_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    active_key: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)  # safe to show to the owner
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)  # internal; never returned by the API
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    document: Mapped[Document] = relationship(back_populates="jobs")
