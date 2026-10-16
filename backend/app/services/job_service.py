"""Persistent background processing of documents.

The queue is the `processing_jobs` table in MySQL, so jobs survive restarts and need no extra service. A worker claims
a queued job with a single conditional UPDATE (only one worker can win it), reports real progress as it passes each
stage, and either completes the job, schedules an automatic retry with backoff (transient problems such as an
unavailable embedding model) or fails it for good (a corrupt, empty or protected PDF). Failed jobs can be retried by
their owner. The unique `active_key` guarantees a document never has two active jobs.

Every job processes ONE document version. A new version only becomes the document's current version (and therefore
searchable / used by RAG) after its text is chunked, embedded and indexed successfully; until then, and if it fails, the
previous current version stays active and untouched."""

import logging
from datetime import timedelta
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.db.session import SessionLocal
from app.models.document import (
    ACTIVE_JOB_STATUSES,
    JOB_COMPLETED,
    JOB_FAILED,
    JOB_PROCESSING,
    JOB_QUEUED,
    STATUS_FAILED,
    STATUS_PROCESSING,
    STATUS_QUEUED,
    STATUS_READY,
    Document,
    DocumentChunk,
    DocumentVersion,
    ProcessingJob,
)
from app.rag.chunker import chunk_pages
from app.repositories import document_repository as repo
from app.services import pdf_service, vector_service
from app.services.embedding_service import EmbeddingError, get_embedder
from app.services.pdf_service import PdfError
from app.utils.time import utcnow

logger = logging.getLogger("documind.jobs")

EMBED_BATCH = 32
# Stage -> progress at the start of that stage. Embedding fills 30..88 in proportion to the batches actually done.
STAGE_START = {"extracting": 5, "chunking": 25, "embedding": 30, "indexing": 90}
EMBED_FROM, EMBED_TO = 30, 88

EMBEDDING_UNAVAILABLE = "The embedding model is unavailable, so this document could not be indexed."
UNEXPECTED = "Processing failed unexpectedly."


class JobAborted(Exception):
    """The job or its document disappeared (for example the document was deleted) while it was running."""


# --------------------------------------------------------------- enqueue
def enqueue(db: Session, document: Document, version: DocumentVersion | None = None, *, retry_count: int = 0) -> ProcessingJob:
    """Creates the queued job for a version (default: the current one). Only the current version's state is mirrored onto
    the document, so queueing a NEW version never makes a ready document look unavailable. Raises 409 if the document
    already has an active job."""
    version = version or db.get(DocumentVersion, document.current_version_id)
    job = ProcessingJob(
        document_id=document.id,
        version_id=version.id if version else None,
        status=JOB_QUEUED,
        progress=0,
        retry_count=retry_count,
        attempts=0,
        max_attempts=settings.job_max_attempts,
        active_key=document.id,
    )
    if version is not None:
        version.processing_status, version.processing_error = STATUS_QUEUED, None
    if version is None or version.id == document.current_version_id:
        document.processing_status = STATUS_QUEUED
        document.processing_error = None
    db.add(job)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(409, "JOB_ALREADY_ACTIVE", "This document is already queued or being processed.") from exc
    return job


# ----------------------------------------------------------------- claim
def claim_next(worker_id: str) -> int | None:
    """Atomically takes the oldest runnable queued job. Returns its id, or None when nothing is due."""
    with SessionLocal() as db:
        now = utcnow()
        candidates = db.scalars(
            select(ProcessingJob.id)
            .where(ProcessingJob.status == JOB_QUEUED, (ProcessingJob.next_run_at.is_(None)) | (ProcessingJob.next_run_at <= now))
            .order_by(ProcessingJob.id)
            .limit(10)
        ).all()
        for job_id in candidates:
            claimed = db.execute(
                update(ProcessingJob)
                .where(ProcessingJob.id == job_id, ProcessingJob.status == JOB_QUEUED)  # loses the race if another worker got it
                .values(
                    status=JOB_PROCESSING,
                    locked_by=worker_id,
                    heartbeat_at=now,
                    started_at=now,
                    attempts=ProcessingJob.attempts + 1,
                    stage="extracting",
                    progress=STAGE_START["extracting"],
                    next_run_at=None,
                )
            )
            db.commit()
            if claimed.rowcount == 1:
                return job_id
    return None


def recover_stale() -> int:
    """Jobs whose worker vanished (no heartbeat) go back to the queue, or fail once their attempts are used up."""
    cutoff = utcnow() - timedelta(seconds=settings.job_stale_after_seconds)
    recovered = 0
    with SessionLocal() as db:
        stale = db.scalars(select(ProcessingJob).where(ProcessingJob.status == JOB_PROCESSING, ProcessingJob.heartbeat_at < cutoff)).all()
        for job in stale:
            logger.warning("Job %s (document %s) lost its worker; recovering", job.id, job.document_id)
            _requeue_or_fail(db, job, "WORKER_LOST", "Processing was interrupted.", "heartbeat expired")
            recovered += 1
        db.commit()
    return recovered


# ------------------------------------------------------------- execution
def _touch(db: Session, job_id: int, worker_id: str, *, stage: str, progress: int) -> None:
    """Records real progress and a heartbeat. Raises JobAborted if this worker no longer owns the job."""
    result = db.execute(
        update(ProcessingJob)
        .where(ProcessingJob.id == job_id, ProcessingJob.status == JOB_PROCESSING, ProcessingJob.locked_by == worker_id)
        .values(stage=stage, progress=min(progress, 99), heartbeat_at=utcnow())
    )
    db.commit()
    if result.rowcount != 1:
        raise JobAborted()


def _cleanup_version(db: Session, document_id: int, version_id: int | None) -> None:
    """Removes the passages and vectors of ONE version so a retry never indexes it twice. Other versions are untouched."""
    chunk_ids = repo.chunk_ids_for_version(db, document_id, version_id)
    try:
        vector_service.delete_chunk_ids(chunk_ids)
        if version_id is not None:
            vector_service.delete_version(version_id)
    except Exception:
        logger.exception("Could not remove vectors for version %s of document %s", version_id, document_id)
    repo.delete_version_chunks(db, document_id, version_id)


def _drop_other_version_vectors(db: Session, document_id: int, keep_version_id: int) -> None:
    """After a version became current, its predecessors leave the vector index (their MySQL passages and files stay for
    history). Best effort: retrieval re-checks every hit against MySQL, so a leftover vector is inert anyway."""
    try:
        vector_service.delete_chunk_ids(repo.chunk_ids_of_other_versions(db, document_id, keep_version_id))
    except Exception:
        logger.exception("Could not remove superseded vectors of document %s", document_id)


def _set_states(doc: Document | None, version: DocumentVersion | None, status: str, error: str | None) -> None:
    if version is not None:
        version.processing_status, version.processing_error = status, error
    if doc is not None and (version is None or version.id == doc.current_version_id):
        doc.processing_status, doc.processing_error = status, error


def _requeue_or_fail(db: Session, job: ProcessingJob, code: str, message: str, detail: str | None) -> None:
    doc = db.get(Document, job.document_id)
    version = db.get(DocumentVersion, job.version_id) if job.version_id else None
    job.error_code, job.error_detail = code, (detail or "")[:4000]
    job.locked_by = None
    if job.attempts < job.max_attempts:
        delay = settings.job_retry_base_seconds * (3 ** (job.attempts - 1 if job.attempts > 0 else 0))
        job.status, job.stage, job.progress = JOB_QUEUED, None, 0
        job.next_run_at = utcnow() + timedelta(seconds=delay)
        job.error_message = f"{message} Retrying automatically (attempt {job.attempts + 1} of {job.max_attempts})."
        _set_states(doc, version, STATUS_QUEUED, None)
    else:
        job.status, job.active_key, job.completed_at = JOB_FAILED, None, utcnow()
        job.error_message = message
        _set_states(doc, version, STATUS_FAILED, message)


def _fail_permanently(db: Session, job_id: int, code: str, message: str, detail: str | None = None) -> None:
    db.rollback()
    job = db.get(ProcessingJob, job_id)
    if job is None:
        return
    doc = db.get(Document, job.document_id)
    version = db.get(DocumentVersion, job.version_id) if job.version_id else None
    if doc:
        _cleanup_version(db, doc.id, job.version_id)
        _set_states(doc, version, STATUS_FAILED, message)
    job.status, job.active_key, job.locked_by, job.completed_at = JOB_FAILED, None, None, utcnow()
    job.error_code, job.error_message, job.error_detail = code, message, (detail or "")[:4000]
    db.commit()


def run_job(job_id: int, worker_id: str) -> None:
    """Runs one claimed job to completion, retry or failure. Never raises."""
    db = SessionLocal()
    document_id = None
    try:
        job = db.get(ProcessingJob, job_id)
        if job is None or job.status != JOB_PROCESSING or job.locked_by != worker_id:
            return
        document_id = job.document_id
        doc = db.get(Document, document_id)
        if doc is None:
            raise JobAborted()
        version = db.get(DocumentVersion, job.version_id or doc.current_version_id)
        if version is None or version.document_id != doc.id:
            raise JobAborted()
        _set_states(doc, version, STATUS_PROCESSING, None)
        db.commit()

        path = Path(version.storage_path)
        if not path.is_file():
            raise PdfError("FILE_MISSING", "The original file is no longer available. Please upload it again.")

        _touch(db, job_id, worker_id, stage="extracting", progress=STAGE_START["extracting"])
        pages = pdf_service.extract_pages(path)

        _touch(db, job_id, worker_id, stage="chunking", progress=STAGE_START["chunking"])
        chunks = chunk_pages(pages, settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            raise PdfError("NO_EXTRACTABLE_TEXT", "No extractable text was found in this PDF.")

        # Clear anything from an earlier attempt so a retry never indexes a document twice.
        _cleanup_version(db, doc.id, version.id)
        rows = [DocumentChunk(document_id=doc.id, version_id=version.id, chunk_index=c.index, page_number=c.page_number, extracted_text=c.text) for c in chunks]
        db.add_all(rows)
        db.flush()  # assigns ids
        db.commit()

        embedder = get_embedder()
        embeddings: list[list[float]] = []
        total = len(chunks)
        for start in range(0, total, EMBED_BATCH):
            batch = [c.text for c in chunks[start : start + EMBED_BATCH]]
            embeddings.extend(embedder.embed(batch))
            done = min(start + EMBED_BATCH, total)
            _touch(db, job_id, worker_id, stage="embedding", progress=EMBED_FROM + int((EMBED_TO - EMBED_FROM) * done / total))

        _touch(db, job_id, worker_id, stage="indexing", progress=STAGE_START["indexing"])
        vector_ids = vector_service.add_chunks(
            user_id=doc.user_id,
            document_id=doc.id,
            chunk_ids=[r.id for r in rows],
            pages=[r.page_number for r in rows],
            texts=[r.extracted_text for r in rows],
            embeddings=embeddings,
            version_id=version.id,
        )
        for row, vid in zip(rows, vector_ids):
            row.vector_reference = vid

        # "completed" / "ready" are only set after indexing fully succeeded, in one transaction.
        # Activation: the version becomes the document's current one only now. The document mirrors the current version's file
        # data, so preview, page images and downloads of the "current" file follow it.
        activated = version.id != doc.current_version_id
        version.total_pages = version.total_pages or len(pages)
        _set_states(doc, version, STATUS_READY, None)
        if activated:
            doc.current_version_id = version.id
            doc.storage_path, doc.file_size, doc.mime_type = version.storage_path, version.file_size, version.mime_type
            doc.processing_status, doc.processing_error = STATUS_READY, None
        doc.total_pages = version.total_pages
        job.status, job.stage, job.progress = JOB_COMPLETED, None, 100
        job.active_key, job.locked_by, job.completed_at = None, None, utcnow()
        job.error_code = job.error_message = job.error_detail = None
        db.commit()
        if activated:
            _drop_other_version_vectors(db, doc.id, version.id)
    except JobAborted:
        db.rollback()
        logger.info("Job %s stopped: it or its document no longer exists / is owned elsewhere", job_id)
        if document_id is not None and db.get(Document, document_id) is None:
            _remove_vectors_quietly(document_id)  # the document was deleted mid-run: leave no orphan vectors
    except PdfError as exc:
        _fail_permanently(db, job_id, exc.code, exc.message)
    except EmbeddingError as exc:
        logger.error("Embedding failure in job %s: %s", job_id, exc)
        _retry_or_fail(db, job_id, "EMBEDDING_UNAVAILABLE", EMBEDDING_UNAVAILABLE, str(exc), document_id)
    except Exception as exc:
        logger.exception("Job %s failed", job_id)
        if document_id is not None and db.get(Document, document_id) is None:
            _remove_vectors_quietly(document_id)
        else:
            _retry_or_fail(db, job_id, "UNEXPECTED_ERROR", UNEXPECTED, repr(exc), document_id)
    finally:
        db.close()


def _remove_vectors_quietly(document_id: int) -> None:
    try:
        vector_service.delete_document(document_id)
    except Exception:
        logger.exception("Could not remove vectors of vanished document %s", document_id)


def _retry_or_fail(db: Session, job_id: int, code: str, message: str, detail: str, document_id: int | None) -> None:
    try:
        db.rollback()
        job = db.get(ProcessingJob, job_id)
        if job is None:
            return
        if document_id is not None:
            _cleanup_version(db, document_id, job.version_id)  # an attempt never leaves partial chunks or vectors behind
        _requeue_or_fail(db, job, code, message, detail)
        db.commit()
    except Exception:
        logger.exception("Could not record the failure of job %s", job_id)
        db.rollback()


# ------------------------------------------------------------ user actions
def retry_failed(db: Session, document: Document, version: DocumentVersion | None = None) -> ProcessingJob:
    """Manual retry of a failed version (default: the current one): a new job for THAT version; earlier jobs are kept."""
    version = version or db.get(DocumentVersion, document.current_version_id)
    if version is None or version.document_id != document.id:
        raise AppError(404, "NOT_FOUND", "Version not found.")
    if version.processing_status != STATUS_FAILED:
        raise AppError(409, "INVALID_STATE", "Only failed documents can be retried.")
    if not Path(version.storage_path).is_file():
        raise AppError(400, "FILE_MISSING", "The original file is no longer available. Please upload it again.")
    previous = repo.latest_job(db, document.id)
    _cleanup_version(db, document.id, version.id)
    job = enqueue(db, document, version, retry_count=(previous.retry_count + 1) if previous else 1)
    db.commit()
    return job


def is_active(job: ProcessingJob | None) -> bool:
    return bool(job and job.status in ACTIVE_JOB_STATUSES)
