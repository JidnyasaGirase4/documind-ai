from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.utils.time import utcnow

# Ownership rules (Phase 2): collections, categories and tags belong to exactly one user. A document may be in many of
# the owner's collections and carries at most one category and many tags. Deleting a collection, category or tag never
# deletes documents: it only removes the grouping/label.


class Collection(Base):
    __tablename__ = "collections"
    __table_args__ = (UniqueConstraint("owner_id", "name", name="uq_collections_owner_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)  # one of knowledge_service.COLORS
    icon: Mapped[str | None] = mapped_column(String(30), nullable=True)  # one of knowledge_service.ICONS
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class CollectionDocument(Base):
    __tablename__ = "collection_documents"
    __table_args__ = (Index("ix_collection_documents_document", "document_id"),)

    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("owner_id", "name", name="uq_categories_owner_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("owner_id", "name", name="uq_tags_owner_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class DocumentTag(Base):
    __tablename__ = "document_tags"
    __table_args__ = (Index("ix_document_tags_tag", "tag_id"),)

    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)


# CollectionMember.role values. The collection's owner is `Collection.owner_id` and is not stored here.
ROLE_VIEWER = "viewer"
ROLE_EDITOR = "editor"
MEMBER_ROLES = (ROLE_VIEWER, ROLE_EDITOR)


class CollectionMember(Base):
    """Explicit, immediately effective sharing of one collection with one registered user."""

    __tablename__ = "collection_members"
    __table_args__ = (UniqueConstraint("collection_id", "user_id", name="uq_collection_members_collection_user"), Index("ix_collection_members_user", "user_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(10))
    invited_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
