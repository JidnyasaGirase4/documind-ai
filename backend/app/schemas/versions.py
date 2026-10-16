from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UTCDateTime


class UploaderOut(BaseModel):
    id: int
    name: str


class VersionOut(BaseModel):
    """A version as shown to anyone who may read the document. The storage path is never included."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    version_number: int
    original_filename: str
    file_size: int
    mime_type: str
    checksum_sha256: str | None = None
    total_pages: int | None = None
    processing_status: str  # queued | processing | ready | failed (uploaded for legacy rows)
    processing_error: str | None = None
    is_current: bool = False
    change_note: str | None = None
    restored_from_version_number: int | None = None
    uploaded_by: UploaderOut | None = None
    created_at: UTCDateTime
    job_id: int | None = None
    progress: int | None = None


class VersionCompareSide(BaseModel):
    id: int
    version_number: int
    created_at: UTCDateTime
    is_current: bool
    processing_status: str


class VersionCompareOut(BaseModel):
    document_id: int
    from_version: VersionCompareSide
    to_version: VersionCompareSide
    comparable: bool
    reason: str | None = None
    stats: dict
    blocks: list[dict]
    notice: str


class RestoreIn(BaseModel):
    change_note: str | None = Field(None, max_length=500)
