from fastapi import APIRouter, Depends, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.versions import RestoreIn, VersionCompareOut, VersionOut
from app.services import version_service
from app.utils.files import display_filename
from app.utils.rate_limit import rate_limit

router = APIRouter(prefix="/documents/{document_id}/versions", tags=["versions"])


@router.get("", response_model=list[VersionOut])
def list_versions(document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Newest first. Any role that can read the document can see its history."""
    return version_service.list_versions(db, user, document_id)


@router.post("", response_model=VersionOut, status_code=202, dependencies=[Depends(rate_limit("upload", 20, 60))])
async def upload_version(
    document_id: int,
    file: UploadFile,
    change_note: str | None = Form(None, max_length=500),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Owner/editor: uploads a new version. It is processed in the background and becomes current only when ready."""
    return await version_service.upload_version(db, user, document_id, file, change_note)


# Declared before "/{version_id}" so "compare" is never parsed as an id.
@router.get("/compare", response_model=VersionCompareOut)
def compare_versions(
    document_id: int,
    from_version: int = Query(..., alias="from"),
    to_version: int = Query(..., alias="to"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return version_service.compare(db, user, document_id, from_version, to_version)


@router.get("/{version_id}", response_model=VersionOut)
def get_version(document_id: int, version_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return version_service.get_version(db, user, document_id, version_id)


@router.get("/{version_id}/download")
def download_version(document_id: int, version_id: int, inline: bool = False, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The stored PDF of exactly this version (attachment by default, `inline=true` for viewing)."""
    version, path = version_service.version_file(db, user, document_id, version_id)
    stem = display_filename(version.original_filename).rsplit(".", 1)[0]
    return FileResponse(path, media_type="application/pdf", content_disposition_type="inline" if inline else "attachment", filename=f"{stem}-v{version.version_number}.pdf")


@router.post("/{version_id}/restore", response_model=VersionOut, status_code=202, dependencies=[Depends(rate_limit("upload", 20, 60))])
def restore_version(document_id: int, version_id: int, body: RestoreIn | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Owner/editor: copies this version into a NEW latest version. History is never rewritten."""
    return version_service.restore(db, user, document_id, version_id, body.change_note if body else None)


@router.post("/{version_id}/retry", response_model=VersionOut, status_code=202)
def retry_version(document_id: int, version_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return version_service.retry(db, user, document_id, version_id)
