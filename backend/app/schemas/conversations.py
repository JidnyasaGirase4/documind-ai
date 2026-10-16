from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel, UTCDateTime

MAX_QUESTION_CHARS = 4000


class CitationOut(BaseModel):
    document_id: int
    document_name: str
    page_number: int
    excerpt: str | None = None
    chunk_id: str | None = None
    version_id: int | None = None  # the document version the passage came from
    version_number: int | None = None
    version_is_current: bool | None = None  # filled in when a conversation is read


class FeedbackIn(BaseModel):
    rating: Literal["up", "down"]
    category: Literal["inaccurate", "missing_information", "wrong_source", "unclear", "other"] | None = None
    comment: str | None = Field(default=None, max_length=2000)

    @field_validator("comment")
    @classmethod
    def _clean(cls, v: str | None) -> str | None:
        v = (v or "").strip()
        return v or None


class FeedbackOut(BaseModel):
    rating: str
    category: str | None = None
    comment: str | None = None
    updated_at: UTCDateTime


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    citations: list[CitationOut] = []
    feedback: FeedbackOut | None = None
    created_at: UTCDateTime


class ConversationOut(ORMModel):
    id: int
    title: str
    created_at: UTCDateTime
    updated_at: UTCDateTime
    message_count: int = 0


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = []


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    document_ids: list[int] | None = None  # accepted for forward compatibility; scope is set per message


class ConversationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)

    @field_validator("title")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty.")
        return v


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)
    document_ids: list[int] | None = Field(default=None, max_length=50)  # empty/None means "all my documents"

    @field_validator("content")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty.")
        return v


class SendMessageResponse(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut
