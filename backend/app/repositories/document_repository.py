"""Every query takes a user_id. Owner-only helpers filter by Document.user_id; the *_accessible helpers apply the sharing
rules from access_service (own documents plus documents in collections shared with the user)."""

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk, DocumentVersion, ProcessingJob
from app.models.knowledge import CollectionDocument, DocumentTag
from app.services import access_service


def get_owned(db: Session, user_id: int, document_id: int) -> Document | None:
    return db.scalar(select(Document).where(Document.id == document_id, Document.user_id == user_id))


def list_owned(
    db: Session,
    user_id: int,
    *,
    page: int,
    page_size: int,
    search: str | None = None,
    status: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    collection_id: int | None = None,
    category_id: int | None = None,
    tag_id: int | None = None,
    scope: str = "owned",
) -> tuple[list[Document], int]:
    """`scope`: owned (default), shared (only documents others own) or all readable. With `collection_id` the caller has
    already checked access to that collection, so its documents are listed whoever owns them."""
    if collection_id is not None:
        stmt = select(Document)
    elif scope == "all":
        stmt = select(Document).where(Document.id.in_(access_service.readable_document_ids(user_id)))
    elif scope == "shared":
        stmt = select(Document).where(Document.id.in_(access_service.readable_document_ids(user_id)), Document.user_id != user_id)
    else:
        stmt = select(Document).where(Document.user_id == user_id)
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(Document.original_filename.ilike(f"%{escaped}%", escape="\\"))
    if status:
        stmt = stmt.where(Document.processing_status == status)
    if collection_id is not None:
        stmt = stmt.where(Document.id.in_(select(CollectionDocument.document_id).where(CollectionDocument.collection_id == collection_id)))
    if category_id is not None:
        stmt = stmt.where(Document.category_id.is_(None) if category_id == 0 else Document.category_id == category_id)
    if tag_id is not None:
        stmt = stmt.where(Document.id.in_(select(DocumentTag.document_id).where(DocumentTag.tag_id == tag_id)))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    column = Document.original_filename if sort_by == "name" else Document.created_at
    direction = asc if sort_order == "asc" else desc
    stmt = stmt.order_by(direction(column), desc(Document.id)).offset((page - 1) * page_size).limit(page_size)
    return list(db.scalars(stmt)), total


def get_accessible_job(db: Session, user_id: int, job_id: int) -> ProcessingJob | None:
    """A job is visible to anyone who can read its document."""
    stmt = select(ProcessingJob).where(ProcessingJob.id == job_id, ProcessingJob.document_id.in_(access_service.readable_document_ids(user_id)))
    return db.scalar(stmt)


def list_accessible_jobs(db: Session, user_id: int, *, page: int, page_size: int, status: str | None = None, document_id: int | None = None):
    stmt = select(ProcessingJob).where(ProcessingJob.document_id.in_(access_service.readable_document_ids(user_id)))
    if status:
        stmt = stmt.where(ProcessingJob.status == status)
    if document_id:
        stmt = stmt.where(ProcessingJob.document_id == document_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.order_by(desc(ProcessingJob.id)).offset((page - 1) * page_size).limit(page_size)
    return list(db.scalars(stmt)), total


def chunks_by_ids(db: Session, ids: list[int]) -> dict[int, DocumentChunk]:
    if not ids:
        return {}
    return {c.id: c for c in db.scalars(select(DocumentChunk).where(DocumentChunk.id.in_(ids)))}


def leading_chunks(db: Session, document_ids: list[int], per_document: int) -> list[DocumentChunk]:
    """The first `per_document` passages (reading order) of each document's CURRENT version."""
    out: list[DocumentChunk] = []
    for doc_id in document_ids:
        stmt = (
            select(DocumentChunk)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(DocumentChunk.document_id == doc_id, DocumentChunk.version_id == Document.current_version_id)
            .order_by(DocumentChunk.chunk_index)
            .limit(per_document)
        )
        out.extend(db.scalars(stmt))
    return out


def _version_filter(document_id: int, version_id: int | None):
    return (DocumentChunk.document_id == document_id, DocumentChunk.version_id == version_id if version_id is not None else DocumentChunk.version_id.is_(None))


def chunk_ids_for_version(db: Session, document_id: int, version_id: int | None) -> list[int]:
    return list(db.scalars(select(DocumentChunk.id).where(*_version_filter(document_id, version_id))))


def chunk_ids_of_other_versions(db: Session, document_id: int, keep_version_id: int) -> list[int]:
    return list(db.scalars(select(DocumentChunk.id).where(DocumentChunk.document_id == document_id, DocumentChunk.version_id != keep_version_id)))


def delete_version_chunks(db: Session, document_id: int, version_id: int | None) -> None:
    for chunk in db.scalars(select(DocumentChunk).where(*_version_filter(document_id, version_id))):
        db.delete(chunk)
    db.flush()


def get_version(db: Session, document_id: int, version_id: int) -> DocumentVersion | None:
    return db.scalar(select(DocumentVersion).where(DocumentVersion.id == version_id, DocumentVersion.document_id == document_id))


def delete_chunks(db: Session, document_id: int) -> None:
    for chunk in db.scalars(select(DocumentChunk).where(DocumentChunk.document_id == document_id)):
        db.delete(chunk)
    db.flush()


def latest_job(db: Session, document_id: int) -> ProcessingJob | None:
    return db.scalar(select(ProcessingJob).where(ProcessingJob.document_id == document_id).order_by(desc(ProcessingJob.id)).limit(1))


def latest_jobs(db: Session, document_ids: list[int]) -> dict[int, ProcessingJob]:
    """Most recent job of each given document, in one query."""
    if not document_ids:
        return {}
    newest = select(func.max(ProcessingJob.id)).where(ProcessingJob.document_id.in_(document_ids)).group_by(ProcessingJob.document_id)
    return {j.document_id: j for j in db.scalars(select(ProcessingJob).where(ProcessingJob.id.in_(newest)))}


def version_numbers(db: Session, version_ids) -> dict[int, int]:
    ids = [i for i in set(version_ids) if i]
    if not ids:
        return {}
    return dict(db.execute(select(DocumentVersion.id, DocumentVersion.version_number).where(DocumentVersion.id.in_(ids))).all())
