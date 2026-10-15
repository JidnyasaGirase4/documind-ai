"""Every query takes a user_id: documents are never fetched without the owner filter."""

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk, ProcessingJob


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
) -> tuple[list[Document], int]:
    stmt = select(Document).where(Document.user_id == user_id)
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(Document.original_filename.ilike(f"%{escaped}%", escape="\\"))
    if status:
        stmt = stmt.where(Document.processing_status == status)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    column = Document.original_filename if sort_by == "name" else Document.created_at
    direction = asc if sort_order == "asc" else desc
    stmt = stmt.order_by(direction(column), desc(Document.id)).offset((page - 1) * page_size).limit(page_size)
    return list(db.scalars(stmt)), total


def get_owned_many(db: Session, user_id: int, ids: list[int]) -> list[Document]:
    if not ids:
        return []
    return list(db.scalars(select(Document).where(Document.user_id == user_id, Document.id.in_(ids))))


def ready_ids_for_user(db: Session, user_id: int) -> list[int]:
    return list(db.scalars(select(Document.id).where(Document.user_id == user_id, Document.processing_status == "ready")))


def chunks_by_ids(db: Session, ids: list[int]) -> dict[int, DocumentChunk]:
    if not ids:
        return {}
    return {c.id: c for c in db.scalars(select(DocumentChunk).where(DocumentChunk.id.in_(ids)))}


def leading_chunks(db: Session, document_ids: list[int], per_document: int) -> list[DocumentChunk]:
    """The first `per_document` chunks (in reading order) of each document."""
    out: list[DocumentChunk] = []
    for doc_id in document_ids:
        out.extend(db.scalars(select(DocumentChunk).where(DocumentChunk.document_id == doc_id).order_by(DocumentChunk.chunk_index).limit(per_document)))
    return out


def delete_chunks(db: Session, document_id: int) -> None:
    for chunk in db.scalars(select(DocumentChunk).where(DocumentChunk.document_id == document_id)):
        db.delete(chunk)
    db.flush()


def latest_job(db: Session, document_id: int) -> ProcessingJob | None:
    return db.scalar(select(ProcessingJob).where(ProcessingJob.document_id == document_id).order_by(desc(ProcessingJob.id)).limit(1))
