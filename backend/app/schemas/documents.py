from pydantic import BaseModel, ConfigDict

from app.schemas.common import ORMModel, UTCDateTime


class JobOut(ORMModel):
    """Processing job as shown to its owner. Internal error details never appear here."""

    id: int
    document_id: int
    version_id: int | None = None
    status: str  # queued | processing | completed | failed
    stage: str | None = None
    progress: int = 0
    attempts: int = 0
    max_attempts: int = 3
    retry_count: int = 0
    error_code: str | None = None
    error_message: str | None = None
    next_run_at: UTCDateTime | None = None
    started_at: UTCDateTime | None = None
    completed_at: UTCDateTime | None = None
    created_at: UTCDateTime


class LabelOut(BaseModel):
    id: int
    name: str


class DocumentOut(ORMModel):
    """Public view of a document. The internal storage path is intentionally not exposed."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    original_filename: str
    file_size: int
    mime_type: str
    processing_status: str
    processing_error: str | None = None
    total_pages: int | None = None
    created_at: UTCDateTime
    updated_at: UTCDateTime
    job: JobOut | None = None
    category: LabelOut | None = None
    tags: list[LabelOut] = []
    collection_ids: list[int] = []
    version_number: int | None = None  # number of the current version
    role: str = "owner"  # the caller's effective role on this document: owner | editor | viewer
    is_owner: bool = True


class HighlightRect(BaseModel):
    x: float
    y: float
    w: float
    h: float


class HighlightOut(BaseModel):
    """Rectangles are fractions (0..1) of the page width/height. Empty unless `reliable`."""

    page_number: int
    page_width: float
    page_height: float
    rects: list[HighlightRect] = []
    matched_words: int
    total_words: int
    coverage: float
    reliable: bool
