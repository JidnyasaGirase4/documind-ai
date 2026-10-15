from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel, UTCDateTime

MAX_QUESTION_CHARS = 4000


class CitationOut(BaseModel):
    document_id: int
    document_name: str
    page_number: int
    excerpt: str | None = None
    chunk_id: str | None = None


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    citations: list[CitationOut] = []
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
    document_ids: list[int] | None = None  # empty/None means "all my documents"

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
