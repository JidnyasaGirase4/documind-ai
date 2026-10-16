from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import UTCDateTime


class AnalyzeIn(BaseModel):
    document_id: int | None = Field(None, ge=1)
    collection_id: int | None = Field(None, ge=1)

    @model_validator(mode="after")
    def _one_scope(self):
        if (self.document_id is None) == (self.collection_id is None):
            raise ValueError("Provide exactly one of document_id or collection_id.")
        return self


class DecisionIn(BaseModel):
    decision: Literal["confirmed", "not_conflict", "needs_review"]
    note: str | None = Field(None, max_length=2000)


class ReportOut(BaseModel):
    id: int
    status: str  # running | completed | failed
    scope_document_id: int | None = None
    scope_collection_id: int | None = None
    passages_examined: int = 0
    pairs_examined: int = 0
    pairs_unparsed: int = 0
    pairs_compatible: int = 0
    findings_created: int = 0
    error_code: str | None = None
    error_message: str | None = None
    created_at: UTCDateTime
    completed_at: UTCDateTime | None = None


class SourceOut(BaseModel):
    document_id: int
    title: str
    version_id: int | None = None
    version_number: int | None = None
    is_current_version: bool
    page: int | None = None
    chunk_id: str | None = None
    excerpt: str


class PersonOut(BaseModel):
    id: int
    name: str


class FindingOut(BaseModel):
    id: int
    report_id: int
    kind: str  # cross_document | cross_version
    conflict_type: str
    assessment: str  # potential_conflict | needs_review: what the AI said, never a confirmed fact
    explanation: str
    quotes_verified: bool  # the quoted evidence was found word for word in both passages
    source_a: SourceOut
    source_b: SourceOut
    stale: bool  # a source version is no longer current: re-analysis recommended
    review_status: str  # pending | confirmed | not_conflict | needs_review: what a person decided
    reviewed_by: PersonOut | None = None
    reviewed_at: UTCDateTime | None = None
    review_note: str | None = None
    detected_at: UTCDateTime
    can_decide: bool


class DecisionOut(BaseModel):
    id: int
    decision: str
    note: str | None = None
    decided_at: UTCDateTime
    decided_by: PersonOut | None = None
