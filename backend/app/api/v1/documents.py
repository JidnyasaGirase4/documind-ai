from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models.document import ALL_STATUSES
from app.models.user import User
from app.repositories import document_repository as repo
from app.schemas.common import page_of
from app.schemas.documents import DocumentOut
from app.services import document_service
from app.utils.rate_limit import rate_limit

router = APIRouter(prefix="/documents", tags=["documents"])

StatusFilter = Literal[ALL_STATUSES]  # type: ignore[valid-type]


@router.post("/upload", response_model=DocumentOut, status_code=202, dependencies=[Depends(rate_limit("upload", 20, 60))])
async def upload_document(file: UploadFile, background_tasks: BackgroundTasks, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = await document_service.create_from_upload(db, user, file)
    background_tasks.add_task(document_service.process_document, doc.id)
    return doc


@router.get("")
def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str | None = Query(None, max_length=255),
    status: StatusFilter | None = None,
    sort_by: Literal["name", "created_at"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = repo.list_owned(db, user.id, page=page, page_size=page_size, search=search, status=status, sort_by=sort_by, sort_order=sort_order)
    return page_of([DocumentOut.model_validate(d) for d in items], total, page, page_size)


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = repo.get_owned(db, user.id, document_id)
    if doc is None:
        raise AppError(404, "NOT_FOUND", "Document not found.")
    return doc


@router.get("/{document_id}/preview")
def preview_document(document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Streams the PDF to its owner. The internal storage path is never exposed."""
    doc = repo.get_owned(db, user.id, document_id)
    if doc is None:
        raise AppError(404, "NOT_FOUND", "Document not found.")
    return FileResponse(
        doc.storage_path,
        media_type="application/pdf",
        content_disposition_type="inline",
        filename=f"document-{doc.id}.pdf",
    )


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    document_service.delete_document(db, user, document_id)
    return Response(status_code=204)


@router.post("/{document_id}/retry", response_model=DocumentOut, status_code=202)
def retry_document(document_id: int, background_tasks: BackgroundTasks, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = document_service.prepare_retry(db, user, document_id)
    background_tasks.add_task(document_service.process_document, doc.id)
    return doc

