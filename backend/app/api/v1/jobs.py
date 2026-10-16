from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.v1.documents import document_out
from app.core.errors import AppError
from app.db.session import get_db
from app.models.user import User
from app.repositories import document_repository as repo
from app.schemas.common import page_of
from app.schemas.documents import DocumentOut, JobOut
from app.services import document_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _owned_job(db: Session, user: User, job_id: int):
    # A job of a document the caller cannot read is reported as "not found" so ids cannot be probed.
    job = repo.get_accessible_job(db, user.id, job_id)
    if job is None:
        raise AppError(404, "NOT_FOUND", "Job not found.")
    return job


@router.get("")
def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Literal["queued", "processing", "completed", "failed"] | None = None,
    document_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = repo.list_accessible_jobs(db, user.id, page=page, page_size=page_size, status=status, document_id=document_id)
    return page_of([JobOut.model_validate(j) for j in items], total, page, page_size)


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _owned_job(db, user, job_id)


@router.post("/{job_id}/retry", response_model=DocumentOut, status_code=202)
def retry_job(job_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retries the failed document this job belongs to (same effect as POST /documents/{id}/retry)."""
    job = _owned_job(db, user, job_id)
    return document_out(db, document_service.retry(db, user, job.document_id, job.version_id), viewer=user)
