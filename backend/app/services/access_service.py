"""The single place that decides who may see or change what. Every check reads the database on every request, so a
revoked member loses access immediately.

Collection roles: owner (Collection.owner_id) > editor > viewer.

Document access (never inferred from anything but these rules):
  * the document's own owner (Document.user_id) -> "owner" of the document;
  * otherwise, through a collection that contains the document: the collection's owner or an editor -> "editor",
    a viewer -> "viewer" (the highest role over all such collections).
A document is NOT reachable merely because its owner shares some other collection, and being in a collection grants
nothing on other documents.

Capabilities: read = any role; write (metadata, retry processing) = document owner or editor; delete = document owner."""

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, not_found
from app.models.document import Document
from app.models.knowledge import ROLE_EDITOR, ROLE_VIEWER, Collection, CollectionDocument, CollectionMember

OWNER = "owner"
RANK = {ROLE_VIEWER: 1, ROLE_EDITOR: 2, OWNER: 3}


def forbidden(message: str = "You do not have permission to do that.") -> AppError:
    return AppError(403, "FORBIDDEN", message)


# ------------------------------------------------------------ collections
def collection_role(db: Session, user_id: int, collection: Collection) -> str | None:
    if collection.owner_id == user_id:
        return OWNER
    return db.scalar(select(CollectionMember.role).where(CollectionMember.collection_id == collection.id, CollectionMember.user_id == user_id))


def collection_roles(db: Session, user_id: int, collection_ids: list[int]) -> dict[int, str]:
    if not collection_ids:
        return {}
    roles = {cid: OWNER for cid in db.scalars(select(Collection.id).where(Collection.owner_id == user_id, Collection.id.in_(collection_ids)))}
    for cid, role in db.execute(select(CollectionMember.collection_id, CollectionMember.role).where(CollectionMember.user_id == user_id, CollectionMember.collection_id.in_(collection_ids))):
        roles.setdefault(cid, role)
    return roles


def get_collection(db: Session, user_id: int, collection_id: int, need: str = ROLE_VIEWER) -> tuple[Collection, str]:
    """404 when the user has no role at all (existence is not revealed); 403 when they have a role that is too low."""
    coll = db.get(Collection, collection_id)
    role = collection_role(db, user_id, coll) if coll else None
    if coll is None or role is None:
        raise not_found("Collection")
    if RANK[role] < RANK[need]:
        raise forbidden("Only the collection owner can do that." if need == OWNER else "You need editor access to do that.")
    return coll, role


def accessible_collection_ids(user_id: int):
    """Subquery of the ids of all collections the user owns or is a member of."""
    return select(Collection.id).where(Collection.owner_id == user_id).union(select(CollectionMember.collection_id).where(CollectionMember.user_id == user_id))


# -------------------------------------------------------------- documents
def readable_document_ids(user_id: int):
    """Subquery of the ids of every document the user may read: own documents plus documents in collections shared with them."""
    via_collection = select(CollectionDocument.document_id).where(CollectionDocument.collection_id.in_(accessible_collection_ids(user_id)))
    return select(Document.id).where(Document.user_id == user_id).union(via_collection)


def document_roles(db: Session, user_id: int, doc_ids: list[int]) -> dict[int, str]:
    """Effective role per document id; documents the user cannot access are absent."""
    if not doc_ids:
        return {}
    roles: dict[int, str] = {d.id: OWNER for d in db.execute(select(Document.id).where(Document.user_id == user_id, Document.id.in_(doc_ids)))}
    rest = [i for i in doc_ids if i not in roles]
    if rest:
        owned_c = select(Collection.id).where(Collection.owner_id == user_id)
        rows = db.execute(
            select(CollectionDocument.document_id, CollectionMember.role)
            .join(CollectionMember, and_(CollectionMember.collection_id == CollectionDocument.collection_id, CollectionMember.user_id == user_id))
            .where(CollectionDocument.document_id.in_(rest))
        )
        for doc_id, role in rows:
            if RANK[role] > RANK.get(roles.get(doc_id), 0):
                roles[doc_id] = role
        for (doc_id,) in db.execute(select(CollectionDocument.document_id).where(CollectionDocument.document_id.in_(rest), CollectionDocument.collection_id.in_(owned_c))):
            if RANK[ROLE_EDITOR] > RANK.get(roles.get(doc_id), 0):
                roles[doc_id] = ROLE_EDITOR  # a collection owner manages its documents but does not own the file
    return roles


def get_document(db: Session, user_id: int, document_id: int, need: str = ROLE_VIEWER) -> tuple[Document, str]:
    """Returns (document, effective role). 404 if the user cannot read it at all; 403 if they can read but lack `need`."""
    role = document_roles(db, user_id, [document_id]).get(document_id)
    doc = db.get(Document, document_id) if role else None
    if doc is None or role is None:
        raise not_found("Document")
    if RANK[role] < RANK[need]:
        raise forbidden("Only the document's owner can do that." if need == OWNER else "You need editor access to do that.")
    return doc, role


def get_readable_many(db: Session, user_id: int, ids: list[int]) -> list[Document]:
    if not ids:
        return []
    return list(db.scalars(select(Document).where(Document.id.in_(ids), Document.id.in_(readable_document_ids(user_id)))))


def readable_ready_ids(db: Session, user_id: int) -> list[int]:
    return list(db.scalars(select(Document.id).where(Document.processing_status == "ready", Document.id.in_(readable_document_ids(user_id)))))
