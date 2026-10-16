"""Upload, retry and deletion of documents. Processing itself runs in the background worker (job_service)."""

import hashlib
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, bad_request
from app.models.document import STATUS_QUEUED, Document, DocumentVersion
from app.models.user import User
from app.repositories import document_repository as repo
from app.services import access_service, job_service, pdf_service, vector_service
from app.services.pdf_service import PdfError
from app.utils.files import display_filename

logger = logging.getLogger("documind.documents")

ALLOWED_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}
_READ_CHUNK = 1024 * 1024


# ---------------------------------------------------------------- upload
@dataclass
class StoredUpload:
    path: Path
    filename: str
    size: int
    pages: int
    checksum: str


async def store_upload(user: User, upload: UploadFile) -> StoredUpload:
    """Validates (type, magic bytes, size, parsable PDF, page limit) and stores an upload under a generated name, computing
    its SHA-256 on the way. Used for new documents and for new versions. The file is removed again if anything fails."""
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
    digest = hashlib.sha256()
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
                digest.update(block)
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
    return StoredUpload(dest, filename, size, pages, digest.hexdigest())


async def create_from_upload(db: Session, user: User, upload: UploadFile) -> Document:
    stored = await store_upload(user, upload)
    try:
        doc = Document(
            user_id=user.id,
            original_filename=stored.filename,
            storage_path=str(stored.path),
            file_size=stored.size,
            mime_type="application/pdf",
            processing_status=STATUS_QUEUED,
            total_pages=stored.pages,
        )
        db.add(doc)
        db.flush()
        version = DocumentVersion(
            document_id=doc.id, version_number=1, original_filename=stored.filename, storage_path=str(stored.path), file_size=stored.size,
            mime_type="application/pdf", checksum_sha256=stored.checksum, total_pages=stored.pages, processing_status=STATUS_QUEUED, created_by=user.id,
        )
        db.add(version)
        db.flush()
        doc.current_version_id = version.id
        job_service.enqueue(db, doc, version)  # the background worker picks it up; the response does not wait for processing
        db.commit()
    except Exception:
        db.rollback()
        stored.path.unlink(missing_ok=True)
        raise
    db.refresh(doc)
    return doc


# ----------------------------------------------------------------- retry
def retry(db: Session, user: User, document_id: int, version_id: int | None = None):
    """Manual retry of a failed version (default: the current one) by the document owner or an editor."""
    doc, _ = access_service.get_document(db, user.id, document_id, need="editor")
    version = None
    if version_id is not None:
        version = repo.get_version(db, doc.id, version_id)
        if version is None:
            raise AppError(404, "NOT_FOUND", "Version not found.")
    job_service.retry_failed(db, doc, version)
    db.refresh(doc)
    return doc


# ---------------------------------------------------------------- delete
def delete_document(db: Session, user: User, document_id: int) -> None:
    """Deletes the database records first, then removes vectors and the stored file.

    If vector or file cleanup fails afterwards it is logged with the document id. Orphaned vectors
    are inert: retrieval re-checks every hit against MySQL, where the chunk no longer exists."""
    doc, _ = access_service.get_document(db, user.id, document_id, need="owner")  # only the uploader may delete the file
    doc_id = doc.id
    paths = [Path(v.storage_path) for v in doc.versions] + [Path(doc.storage_path)]
    doc.current_version_id = None  # break the documents <-> versions cycle before the rows are deleted
    db.flush()
    db.delete(doc)
    db.commit()

    try:
        vector_service.delete_document(doc_id)
    except Exception:
        logger.exception("CLEANUP FAILED: vectors of deleted document %s remain in the index", doc_id)
    for path in dict.fromkeys(paths):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.exception("CLEANUP FAILED: a file of deleted document %s remains at %s", doc_id, path)
