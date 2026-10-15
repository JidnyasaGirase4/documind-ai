from pydantic import ConfigDict

from app.schemas.common import ORMModel, UTCDateTime


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
