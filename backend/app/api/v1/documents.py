from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Path as Path_, Query, Response, UploadFile
from fastapi.responses import FileResponse, Response as RawResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models.document import ALL_STATUSES
from app.models.user import User
from app.repositories import document_repository as repo
from app.schemas.common import page_of
from app.schemas.documents import DocumentOut, HighlightOut, JobOut, LabelOut
from app.schemas.knowledge import DocumentMetadataPatch
from app.models.document import DocumentVersion
from app.services import access_service, document_service, highlight_service, knowledge_service
from app.services.pdf_service import PdfError
from app.utils.rate_limit import rate_limit

_UNSET = object()

router = APIRouter(prefix="/documents", tags=["documents"])

StatusFilter = Literal[ALL_STATUSES]  # type: ignore[valid-type]


def _version_numbers(db: Session, ids: list) -> dict[int, int]:
    ids = [i for i in ids if i]
    if not ids:
        return {}
    return dict(db.execute(select(DocumentVersion.id, DocumentVersion.version_number).where(DocumentVersion.id.in_(ids))).all())


def document_out(db: Session, doc, job=_UNSET, labels=None, viewer=None, role=None) -> DocumentOut:
    """Document plus its latest processing job (status, stage, progress) and its category, tags and collections."""
    out = DocumentOut.model_validate(doc)
    if job is _UNSET:
        job = repo.latest_job(db, doc.id)
    out.job = JobOut.model_validate(job) if job else None
    if viewer is not None:
        if labels is None:
            labels = knowledge_service.document_labels(db, [doc.id], viewer.id)[doc.id]
        if role is None:
            role = access_service.document_roles(db, viewer.id, [doc.id]).get(doc.id)
    elif labels is None:
        labels = knowledge_service.document_labels(db, [doc.id])[doc.id]
    out.version_number = _version_numbers(db, [doc.current_version_id]).get(doc.current_version_id)
    out.role = role or "owner"
    out.is_owner = out.role == "owner"
    out.category = LabelOut(**labels["category"]) if labels["category"] else None
    out.tags = [LabelOut(**t) for t in labels["tags"]]
    out.collection_ids = labels["collection_ids"]
    return out


@router.post("/upload", response_model=DocumentOut, status_code=202, dependencies=[Depends(rate_limit("upload", 20, 60))])
async def upload_document(file: UploadFile, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = await document_service.create_from_upload(db, user, file)
    return document_out(db, doc, viewer=user, role="owner")


@router.get("")
def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str | None = Query(None, max_length=255),
    status: StatusFilter | None = None,
    scope: Literal["owned", "shared", "all"] = Query("owned", description="owned = my uploads; shared = others' documents shared with me; all = both"),
    collection_id: int | None = Query(None, description="Only documents in this collection"),
    category_id: int | None = Query(None, description="Only documents in this category; 0 = uncategorised"),
    tag_id: int | None = Query(None, description="Only documents carrying this tag"),
    sort_by: Literal["name", "created_at"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if collection_id is not None:
        access_service.get_collection(db, user.id, collection_id)  # 404 unless the caller owns or is a member of it
    items, total = repo.list_owned(db, user.id, scope=scope, page=page, page_size=page_size, search=search, status=status, sort_by=sort_by, sort_order=sort_order, collection_id=collection_id, category_id=category_id, tag_id=tag_id)
    ids = [d.id for d in items]
    vnums = _version_numbers(db, [d.current_version_id for d in items])
    jobs = repo.latest_jobs(db, ids)
    labels = knowledge_service.document_labels(db, ids, user.id)
    roles = access_service.document_roles(db, user.id, ids)
    page_items = [document_out(db, d, jobs.get(d.id), labels[d.id], viewer=user, role=roles.get(d.id)) for d in items]
    for d, out in zip(items, page_items):
        out.version_number = vnums.get(d.current_version_id)
    return page_of(page_items, total, page, page_size)


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc, role = access_service.get_document(db, user.id, document_id)
    return document_out(db, doc, viewer=user, role=role)


@router.patch("/{document_id}/metadata", response_model=DocumentOut)
def update_metadata(document_id: int, body: DocumentMetadataPatch, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Change a document's category, tags and collections without re-uploading or re-processing it."""
    doc, _ = access_service.get_document(db, user.id, document_id, need="editor")
    knowledge_service.update_document_metadata(db, user, doc, body)
    return document_out(db, doc, viewer=user)


@router.get("/{document_id}/preview")
def preview_document(document_id: int, version_id: int | None = Query(None), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Streams the PDF to anyone allowed to read the document: the current version, or the stored file of `version_id`.
    The internal storage path is never exposed."""
    doc, path = _readable_file(db, user, document_id, version_id)
    return FileResponse(
        path,
        media_type="application/pdf",
        content_disposition_type="inline",
        filename=f"document-{doc.id}.pdf",
    )


def _readable_file(db: Session, user: User, document_id: int, version_id: int | None = None):
    """The document must be readable by the caller (own or shared). Returns the file of the requested version, or of the
    current one. A version of another document is 'not found'."""
    doc, _ = access_service.get_document(db, user.id, document_id)
    path = Path(doc.storage_path)
    if version_id is not None:
        version = repo.get_version(db, doc.id, version_id)
        if version is None:
            raise AppError(404, "NOT_FOUND", "Version not found.")
        path = Path(version.storage_path)
    if not path.is_file():
        raise AppError(404, "FILE_MISSING", "The original file is no longer available.")
    return doc, path


@router.get("/{document_id}/pages/{page_number}/image")
def page_image(
    document_id: int,
    page_number: int = Path_(ge=1),
    scale: float = Query(highlight_service.DEFAULT_SCALE, ge=highlight_service.MIN_SCALE, le=highlight_service.MAX_SCALE),
    version_id: int | None = Query(None, description="A historical version; default is the current one"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """One page rendered as a PNG for the in-app viewer. Anyone who may read the document."""
    _, path = _readable_file(db, user, document_id, version_id)
    try:
        png = highlight_service.render_page_png(path, page_number, scale)
    except PdfError as exc:
        raise AppError(404 if exc.code == "PAGE_OUT_OF_RANGE" else 422, exc.code, exc.message) from exc
    return RawResponse(content=png, media_type="image/png", headers={"Cache-Control": "private, max-age=300"})


@router.get("/{document_id}/highlights", response_model=HighlightOut)
def citation_highlights(
    document_id: int,
    chunk_id: str = Query(..., max_length=100, description="The citation's chunk id, e.g. chunk-12"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Where a cited passage sits on its page. `reliable` is false (and `rects` empty) when the passage could not be
    located with confidence, in which case the viewer only opens the page."""
    doc, path = _readable_file(db, user, document_id)
    pk = highlight_service.chunk_pk_from_vector_id(chunk_id)
    chunk = repo.chunks_by_ids(db, [pk]).get(pk) if pk else None
    if chunk is None or chunk.document_id != doc.id:
        raise AppError(404, "NOT_FOUND", "Citation passage not found.")
    if chunk.version_id is not None:  # the passage is located in the file of the version it was extracted from
        _, path = _readable_file(db, user, document_id, chunk.version_id)
    try:
        return highlight_service.locate(path, chunk.page_number, chunk.extracted_text)
    except PdfError as exc:
        raise AppError(422, exc.code, exc.message) from exc


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    document_service.delete_document(db, user, document_id)
    return Response(status_code=204)


@router.post("/{document_id}/retry", response_model=DocumentOut, status_code=202)
def retry_document(document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return document_out(db, document_service.retry(db, user, document_id), viewer=user)

