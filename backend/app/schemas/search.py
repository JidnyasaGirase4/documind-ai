from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import UTCDateTime
from app.schemas.documents import LabelOut


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    mode: Literal["hybrid", "keyword", "semantic"] = "hybrid"
    collection_id: int | None = None
    category_id: int | None = Field(None, ge=0, description="0 = uncategorised")
    tag_id: int | None = Field(None, ge=1)
    file_type: Literal["pdf"] | None = None  # PDF is the only supported type today
    sort_by: Literal["relevance", "newest", "title"] = "relevance"
    page: int = Field(1, ge=1, le=1000)
    page_size: int = Field(10, ge=1, le=50)

    @field_validator("query")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Enter something to search for.")
        return v


class PassageOut(BaseModel):
    chunk_id: str  # e.g. "chunk-12"; usable with the citation highlight endpoint
    page_number: int
    snippet: str
    keyword_match: bool = False
    keyword_rank: int | None = None  # position in the keyword list (1 = best), when it matched
    semantic_rank: int | None = None  # position in the semantic list (1 = best), when it matched
    semantic_similarity: float | None = None  # raw cosine similarity of the embeddings; NOT a probability or confidence


class SearchResultOut(BaseModel):
    document_id: int
    title: str
    score: float  # relative ordering value within this response; its meaning is given by `score_type`
    matched_on: list[Literal["text", "title", "tag", "category"]]
    passages: list[PassageOut]
    total_pages: int | None = None
    file_type: str = "pdf"
    category: LabelOut | None = None
    tags: list[LabelOut] = []
    collections: list[LabelOut] = []  # only collections the caller can access
    role: str
    created_at: UTCDateTime
    updated_at: UTCDateTime


class RankingInfo(BaseModel):
    method: str  # "rrf" | "keyword" | "semantic"
    rrf_k: int | None = None
    keyword_weight: float | None = None
    semantic_weight: float | None = None
    score_type: str  # what `score` means for this response


class SearchResponse(BaseModel):
    query: str
    mode: str
    terms: list[str]  # words used for keyword matching (lower-case); the UI highlights these
    phrases: list[str]
    items: list[SearchResultOut]
    total: int  # documents found within the candidate pool
    total_exact: bool  # false when the candidate pool was full, so more matches may exist
    page: int
    page_size: int
    pages: int
    sort_by: str
    ranking: RankingInfo
    warnings: list[str] = []  # e.g. semantic_unavailable, relaxed_to_any_term
