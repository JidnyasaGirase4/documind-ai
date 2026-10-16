from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel, UTCDateTime


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = " ".join(value.split())
    return value or None


class CollectionIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(None, max_length=1000)
    color: str | None = None
    icon: str | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = _clean(v)
        if not v:
            raise ValueError("Name cannot be blank.")
        return v


class CollectionPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=1000)
    color: str | None = None
    icon: str | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = _clean(v)
        if not v:
            raise ValueError("Name cannot be blank.")
        return v


class CollectionOut(ORMModel):
    id: int
    name: str
    description: str | None = None
    color: str | None = None
    icon: str | None = None
    document_count: int = 0
    role: str = "owner"  # the caller's role: owner | editor | viewer
    owner_name: str | None = None
    is_shared: bool = False
    member_count: int = 0
    created_at: UTCDateTime
    updated_at: UTCDateTime


class CollectionDocumentsIn(BaseModel):
    document_ids: list[int] = Field(min_length=1, max_length=100)
    move_from_collection_id: int | None = None  # when set, the documents are moved (removed from that collection)


class NamedIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(None, max_length=1000)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = _clean(v)
        if not v:
            raise ValueError("Name cannot be blank.")
        return v


class CategoryPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=1000)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = _clean(v)
        if not v:
            raise ValueError("Name cannot be blank.")
        return v


class CategoryOut(ORMModel):
    id: int
    name: str
    description: str | None = None
    document_count: int = 0


class TagIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = _clean(v)
        if not v:
            raise ValueError("Name cannot be blank.")
        return v


class TagOut(ORMModel):
    id: int
    name: str
    document_count: int = 0


class DocumentMetadataPatch(BaseModel):
    """Only the fields that are sent are changed. `category_id: null` clears the category; `tags` replaces the tag set
    (names; missing tags are created); `collection_ids` replaces the document's collection memberships."""

    category_id: int | None = None
    tags: list[str] | None = Field(None, max_length=30)
    collection_ids: list[int] | None = Field(None, max_length=50)


class MemberOut(BaseModel):
    user_id: int
    name: str
    email: str
    role: str  # owner | editor | viewer
    added_at: UTCDateTime


class InviteIn(BaseModel):
    email: str = Field(min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    role: Literal["viewer", "editor"] = "viewer"


class RoleIn(BaseModel):
    role: Literal["viewer", "editor"]
