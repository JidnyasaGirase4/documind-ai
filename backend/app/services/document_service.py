"""Upload, processing pipeline, retry and deletion of documents."""

import logging
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, bad_request
from app.db.session import SessionLocal
from app.models.document import STATUS_FAILED, STATUS_PROCESSING, STATUS_READY, Document, DocumentChunk, ProcessingJob
from app.models.user import User
from app.rag.chunker import chunk_pages
from app.repositories import document_repository as repo
from app.services import pdf_service, vector_service
from app.services.embedding_service import EmbeddingError, get_embedder
from app.services.pdf_service import PdfError
from app.utils.files import display_filename
from app.utils.time import utcnow

logger = logging.getLogger("documind.documents")

ALLOWED_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}
_READ_CHUNK = 1024 * 1024


# ---------------------------------------------------------------- upload
async def create_from_upload(db: Session, user: User, upload: UploadFile) -> Document:
    filename = display_filename(upload.filename)
    if not filename.lower().endswith(".pdf"):
        raise AppError(415, "UNSUPPORTED_FILE_TYPE", "Only PDF files are supported.")
    if (upload.content_type or "").lower() not in ALLOWED_CONTENT_TYPES:
        raise AppError(415, "UNSUPPORTED_FILE_TYPE", "Only PDF files are supported.")

    target_dir = settings.upload_path / str(user.id)
    target_dir.mkdir(parents=True, exist_ok=True)
    # The stored name is generated, never taken from the client, so path traversal is impossible.
    dest = target_dir / f"{uuid.uuid4().hex}.pdf"

    size = 0
    try:
        with open(dest, "wb") as out:
            first = True
            while True:
                block = await upload.read(_READ_CHUNK)
                if not block:
                    break
                if first:
                    if not block.startswith(b"%PDF-"):
                        raise AppError(415, "INVALID_PDF", "This file is not a valid PDF.")
                    first = False
                size += len(block)
                if size > settings.max_upload_bytes:
                    raise AppError(413, "FILE_TOO_LARGE", f"The file is larger than the {settings.max_upload_size_mb} MB limit.")
                out.write(block)
        if size == 0:
            raise bad_request("EMPTY_FILE", "The uploaded file is empty.")
        try:
            pages = pdf_service.validate_pdf(dest)
        except PdfError as exc:
            raise AppError(415, exc.code, exc.message) from exc
    except Exception:
        dest.unlink(missing_ok=True)
        raise

    doc = Document(
        user_id=user.id,
        original_filename=filename,
        storage_path=str(dest),
        file_size=size,
        mime_type="application/pdf",
        processing_status=STATUS_PROCESSING,
        total_pages=pages,
    )
    db.add(doc)
    db.flush()
    db.add(ProcessingJob(document_id=doc.id, status=STATUS_PROCESSING, retry_count=0))
    db.commit()
    db.refresh(doc)
    return doc


# ------------------------------------------------------------ processing
def _fail(db: Session, document_id: int, message: str, internal: str | None = None) -> None:
    """Marks a document as failed with a user-readable message and cleans partial index data."""
    db.rollback()
    doc = db.get(Document, document_id)
    if doc is None:
        return
    _cleanup_index(db, doc)
    doc.processing_status = STATUS_FAILED
    doc.processing_error = message
    job = repo.latest_job(db, document_id)
    if job:
        job.status = STATUS_FAILED
        job.error_message = internal or message
        job.completed_at = utcnow()
    db.commit()


def _cleanup_index(db: Session, doc: Document) -> None:
    try:
        vector_service.delete_document(doc.id)
    except Exception:
        logger.exception("Could not remove vectors for document %s", doc.id)
    repo.delete_chunks(db, doc.id)


def process_document(document_id: int) -> None:
    """Extracts, chunks, embeds and indexes a document. Runs in a background task with its own session."""
    db = SessionLocal()
    try:
        doc = db.get(Document, document_id)
        if doc is None or doc.processing_status != STATUS_PROCESSING:
            return
        job = repo.latest_job(db, document_id)
        if job:
            job.started_at = utcnow()
            db.commit()

        pages = pdf_service.extract_pages(Path(doc.storage_path))
        chunks = chunk_pages(pages, settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            raise PdfError("NO_EXTRACTABLE_TEXT", "No extractable text was found in this PDF.")

        # Clear anything from an earlier attempt so a retry never indexes a document twice.
        _cleanup_index(db, doc)
        rows = [DocumentChunk(document_id=doc.id, chunk_index=c.index, page_number=c.page_number, extracted_text=c.text) for c in chunks]
        db.add_all(rows)
        db.flush()  # assigns ids

        embeddings = get_embedder().embed([c.text for c in chunks])
        vector_ids = vector_service.add_chunks(
            user_id=doc.user_id,
            document_id=doc.id,
            chunk_ids=[r.id for r in rows],
            pages=[r.page_number for r in rows],
            texts=[r.extracted_text for r in rows],
            embeddings=embeddings,
        )
        for row, vid in zip(rows, vector_ids):
            row.vector_reference = vid

        # "ready" is only set after indexing fully succeeded.
        doc.processing_status = STATUS_READY
        doc.processing_error = None
        doc.total_pages = doc.total_pages or len(pages)
        if job:
            job.status = STATUS_READY
            job.completed_at = utcnow()
        db.commit()
    except PdfError as exc:
        _fail(db, document_id, exc.message)
    except EmbeddingError as exc:
        logger.error("Embedding failure for document %s: %s", document_id, exc)
        _fail(db, document_id, "The embedding model is unavailable, so this document could not be indexed. Please try again later.", str(exc))
    except Exception as exc:
        logger.exception("Processing failed for document %s", document_id)
        _fail(db, document_id, "Processing failed unexpectedly. You can retry.", repr(exc))
    finally:
        db.close()


# ----------------------------------------------------------------- retry
def prepare_retry(db: Session, user: User, document_id: int) -> Document:
    doc = repo.get_owned(db, user.id, document_id)
    if doc is None:
        raise AppError(404, "NOT_FOUND", "Document not found.")
    if doc.processing_status != STATUS_FAILED:
        raise bad_request("INVALID_STATE", "Only failed documents can be retried.")
    if not Path(doc.storage_path).is_file():
        raise bad_request("FILE_MISSING", "The original file is no longer available. Please upload it again.")

    previous = repo.latest_job(db, doc.id)
    _cleanup_index(db, doc)
    doc.processing_status = STATUS_PROCESSING
    doc.processing_error = None
    db.add(ProcessingJob(document_id=doc.id, status=STATUS_PROCESSING, retry_count=(previous.retry_count + 1) if previous else 1))
    db.commit()
    db.refresh(doc)
    return doc


# ---------------------------------------------------------------- delete
def delete_document(db: Session, user: User, document_id: int) -> None:
    """Deletes the database records first, then removes vectors and the stored file.

    If vector or file cleanup fails afterwards it is logged with the document id. Orphaned vectors
    are inert: retrieval re-checks every hit against MySQL, where the chunk no longer exists."""
    doc = repo.get_owned(db, user.id, document_id)
    if doc is None:
        raise AppError(404, "NOT_FOUND", "Document not found.")
    doc_id, path = doc.id, Path(doc.storage_path)
    db.delete(doc)
    db.commit()

    try:
        vector_service.delete_document(doc_id)
    except Exception:
        logger.exception("CLEANUP FAILED: vectors of deleted document %s remain in the index", doc_id)
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.exception("CLEANUP FAILED: file of deleted document %s remains at %s", doc_id, path)
