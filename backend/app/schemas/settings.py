from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.common import ORMModel, UTCDateTime


class ProfileOut(ORMModel):
    id: int
    name: str
    email: EmailStr
    created_at: UTCDateTime


class ProfileUpdate(BaseModel):
    """Only the display name can be changed. Unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name is required.")
        return v
