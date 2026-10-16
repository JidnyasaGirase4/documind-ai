"""Version history: list, upload, restore, download and compare. Authorization always goes through access_service:
any reader may inspect history, files and comparisons; owners and editors may upload, restore and retry."""

import logging
import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.models.document import ACTIVE_JOB_STATUSES, STATUS_FAILED, STATUS_QUEUED, STATUS_READY, Document, DocumentVersion, ProcessingJob
from app.models.user import User
from app.repositories import document_repository as repo
from app.schemas.versions import UploaderOut, VersionCompareOut, VersionCompareSide, VersionOut
from app.services import access_service, document_service, job_service, pdf_service, version_diff_service
from app.services.pdf_service import PdfError

logger = logging.getLogger("documind.versions")


# ------------------------------------------------------------- read side
def _out(db: Session, doc: Document, versions: list[DocumentVersion]) -> list[VersionOut]:
    ids = [v.id for v in versions]
    names = {u.id: u.name for u in db.scalars(select(User).where(User.id.in_({v.created_by for v in versions if v.created_by} or {0})))}
    numbers = {v.id: v.version_number for v in db.scalars(select(DocumentVersion).where(DocumentVersion.document_id == doc.id))}
    newest = select(func.max(ProcessingJob.id)).where(ProcessingJob.version_id.in_(ids or [0])).group_by(ProcessingJob.version_id)
    jobs = {j.version_id: j for j in db.scalars(select(ProcessingJob).where(ProcessingJob.id.in_(newest)))}
    out = []
    for v in versions:
        item = VersionOut.model_validate(v)
        item.is_current = v.id == doc.current_version_id
        item.uploaded_by = UploaderOut(id=v.created_by, name=names[v.created_by]) if v.created_by in names else None
        item.restored_from_version_number = numbers.get(v.restored_from_version_id) if v.restored_from_version_id else None
        job = jobs.get(v.id)
        if job and job.status in ACTIVE_JOB_STATUSES:
            item.job_id, item.progress = job.id, job.progress
        out.append(item)
    return out


def list_versions(db: Session, user: User, document_id: int) -> list[VersionOut]:
    doc, _ = access_service.get_document(db, user.id, document_id)
    versions = list(db.scalars(select(DocumentVersion).where(DocumentVersion.document_id == doc.id).order_by(DocumentVersion.version_number.desc())))
    return _out(db, doc, versions)


def get_version(db: Session, user: User, document_id: int, version_id: int) -> VersionOut:
    doc, _ = access_service.get_document(db, user.id, document_id)
    version = _require_version(db, doc, version_id)
    return _out(db, doc, [version])[0]


def _require_version(db: Session, doc: Document, version_id: int) -> DocumentVersion:
    version = repo.get_version(db, doc.id, version_id)  # a version of ANOTHER document is "not found" too
    if version is None:
        raise AppError(404, "NOT_FOUND", "Version not found.")
    return version


def version_file(db: Session, user: User, document_id: int, version_id: int) -> tuple[DocumentVersion, Path]:
    doc, _ = access_service.get_document(db, user.id, document_id)
    version = _require_version(db, doc, version_id)
    path = Path(version.storage_path)
    if not path.is_file():
        raise AppError(404, "FILE_MISSING", "The file of this version is no longer available.")
    return version, path


# ------------------------------------------------------------ write side
def _create_version(
    db: Session, doc_id: int, user: User, *, filename: str, path: Path, size: int, mime: str, checksum: str | None, pages: int | None, note: str | None, restored_from: int | None
) -> DocumentVersion:
    """Allocates the next number and queues processing in ONE transaction while holding a row lock on the document, so two
    concurrent uploads/restores cannot get the same number and at most one version is being processed at a time."""
    try:
        doc = db.execute(select(Document).where(Document.id == doc_id).with_for_update().execution_options(populate_existing=True)).scalar_one()
        busy = db.scalar(select(ProcessingJob.id).where(ProcessingJob.document_id == doc.id, ProcessingJob.status.in_(ACTIVE_JOB_STATUSES)).limit(1))
        if busy:
            raise AppError(409, "VERSION_IN_PROGRESS", "Another version of this document is still being processed. Wait for it to finish.")
        current = db.get(DocumentVersion, doc.current_version_id) if doc.current_version_id else None
        if current and current.checksum_sha256 and checksum and current.checksum_sha256 == checksum:
            raise AppError(409, "DUPLICATE_VERSION", f"This file is identical to the current version (v{current.version_number}), so no new version was created.")
        number = (db.scalar(select(func.max(DocumentVersion.version_number)).where(DocumentVersion.document_id == doc.id)) or 0) + 1
        version = DocumentVersion(
            document_id=doc.id, version_number=number, original_filename=filename, storage_path=str(path), file_size=size, mime_type=mime,
            checksum_sha256=checksum, total_pages=pages, processing_status=STATUS_QUEUED, created_by=user.id, change_note=(note or "").strip() or None,
            restored_from_version_id=restored_from,
        )
        db.add(version)
        db.flush()
        job_service.enqueue(db, doc, version)  # a NEW version never replaces the current one until its job succeeds
        db.commit()
        db.refresh(version)
        return version
    except IntegrityError as exc:
        db.rollback()
        path.unlink(missing_ok=True)
        raise AppError(409, "VERSION_IN_PROGRESS", "Another version of this document is being created. Try again in a moment.") from exc
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        raise


async def upload_version(db: Session, user: User, document_id: int, upload: UploadFile, note: str | None) -> VersionOut:
    doc, _ = access_service.get_document(db, user.id, document_id, need="editor")
    stored = await document_service.store_upload(user, upload)
    version = _create_version(
        db, doc.id, user, filename=stored.filename, path=stored.path, size=stored.size, mime="application/pdf", checksum=stored.checksum,
        pages=stored.pages, note=note, restored_from=None,
    )
    return _out(db, doc, [version])[0]


def restore(db: Session, user: User, document_id: int, version_id: int, note: str | None) -> VersionOut:
    """Restoring never rewrites history: the old file is COPIED into a brand-new version (N+1) that is processed like any
    upload and becomes current only when it is ready."""
    doc, _ = access_service.get_document(db, user.id, document_id, need="editor")
    source = _require_version(db, doc, version_id)
    src = Path(source.storage_path)
    if source.processing_status != STATUS_READY or not src.is_file():
        raise AppError(409, "VERSION_NOT_RESTORABLE", "Only a successfully processed version with an available file can be restored.")
    if source.id == doc.current_version_id:
        raise AppError(409, "ALREADY_CURRENT", "This is already the current version.")
    dest_dir = settings.upload_path / str(user.id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{uuid.uuid4().hex}.pdf"
    shutil.copyfile(src, dest)
    version = _create_version(
        db, doc.id, user, filename=source.original_filename, path=dest, size=source.file_size, mime=source.mime_type, checksum=source.checksum_sha256,
        pages=source.total_pages, note=note or f"Restored from version {source.version_number}", restored_from=source.id,
    )
    return _out(db, doc, [version])[0]


def retry(db: Session, user: User, document_id: int, version_id: int) -> VersionOut:
    document = document_service.retry(db, user, document_id, version_id)
    version = repo.get_version(db, document.id, version_id)
    return _out(db, document, [version])[0]


# ---------------------------------------------------------------- compare
def compare(db: Session, user: User, document_id: int, from_id: int, to_id: int) -> VersionCompareOut:
    doc, _ = access_service.get_document(db, user.id, document_id)
    if from_id == to_id:
        raise AppError(400, "SAME_VERSION", "Choose two different versions to compare.")
    old, new = _require_version(db, doc, from_id), _require_version(db, doc, to_id)

    def side(v: DocumentVersion) -> VersionCompareSide:
        return VersionCompareSide(id=v.id, version_number=v.version_number, created_at=v.created_at, is_current=v.id == doc.current_version_id, processing_status=v.processing_status)

    def result(comparable: bool, reason: str | None, stats: dict | None = None, blocks: list | None = None) -> VersionCompareOut:
        return VersionCompareOut(
            document_id=doc.id, from_version=side(old), to_version=side(new), comparable=comparable, reason=reason,
            stats=stats or {"added": 0, "removed": 0, "changed": 0, "unchanged": 0, "identical": False}, blocks=blocks or [], notice=version_diff_service.NOTICE,
        )

    units = {}
    for v in (old, new):
        if v.processing_status == STATUS_FAILED:
            return result(False, f"Version {v.version_number} failed processing, so its text is not available.")
        path = Path(v.storage_path)
        if not path.is_file():
            return result(False, f"The file of version {v.version_number} is no longer available.")
        try:
            units[v.id] = pdf_service.extract_units(path)
        except PdfError as exc:
            return result(False, f"Version {v.version_number}: {exc.message}")
        if not units[v.id]:
            return result(False, f"Version {v.version_number} has no extractable text (it may be scanned images; OCR is not supported).")
    cmp = version_diff_service.compare_units(units[old.id], units[new.id])
    return result(cmp.comparable, cmp.reason, cmp.stats, cmp.blocks)
