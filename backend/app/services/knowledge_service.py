"""Collections, categories and tags. Everything is scoped to the signed-in owner: another user's ids behave exactly like
ids that do not exist (404), so ids cannot be probed. Deleting a collection, category or tag never deletes documents."""

from sqlalchemy import asc, delete, desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError, bad_request, not_found
from app.models.document import Document
from app.models.knowledge import MEMBER_ROLES, Category, Collection, CollectionDocument, CollectionMember, DocumentTag, Tag
from app.models.user import User
from app.services import access_service as access
from app.services.access_service import OWNER
from app.schemas.knowledge import DocumentMetadataPatch

COLORS = ("burgundy", "charcoal", "rose", "amber", "emerald", "sky", "violet", "slate")
ICONS = ("folder", "book", "briefcase", "scale", "flask", "wallet", "users", "shield", "code", "star")


def _duplicate(what: str) -> AppError:
    return AppError(409, "DUPLICATE_NAME", f"You already have a {what} with that name.")


def _validate_look(color: str | None, icon: str | None) -> None:
    if color is not None and color not in COLORS:
        raise bad_request("INVALID_COLOR", f"Color must be one of: {', '.join(COLORS)}.")
    if icon is not None and icon not in ICONS:
        raise bad_request("INVALID_ICON", f"Icon must be one of: {', '.join(ICONS)}.")


def _name_taken(db: Session, model, owner_id: int, name: str, except_id: int | None = None) -> bool:
    stmt = select(model.id).where(model.owner_id == owner_id, func.lower(model.name) == name.lower())
    if except_id is not None:
        stmt = stmt.where(model.id != except_id)
    return db.scalar(stmt.limit(1)) is not None


def _get(db: Session, model, owner_id: int, obj_id: int, label: str):
    obj = db.scalar(select(model).where(model.id == obj_id, model.owner_id == owner_id))
    if obj is None:
        raise not_found(label)
    return obj


# ------------------------------------------------------------ collections
def _collection_counts(db: Session, ids: list[int]) -> dict[int, int]:
    if not ids:
        return {}
    rows = db.execute(select(CollectionDocument.collection_id, func.count()).where(CollectionDocument.collection_id.in_(ids)).group_by(CollectionDocument.collection_id))
    return {cid: n for cid, n in rows}


def collection_view(db: Session, items: list[Collection], user: User | None = None) -> list[Collection]:
    """Adds transient attributes read by CollectionOut: document count and, for the viewer, role/owner/sharing info."""
    ids = [c.id for c in items]
    counts = _collection_counts(db, ids)
    members = dict(db.execute(select(CollectionMember.collection_id, func.count()).where(CollectionMember.collection_id.in_(ids or [0])).group_by(CollectionMember.collection_id)).all())
    owners = {u.id: u.name for u in db.scalars(select(User).where(User.id.in_({c.owner_id for c in items} or {0})))}
    roles = access.collection_roles(db, user.id, ids) if user else {}
    for c in items:
        c.document_count = counts.get(c.id, 0)
        c.member_count = members.get(c.id, 0)
        c.is_shared = c.member_count > 0
        c.role = roles.get(c.id, OWNER)
        c.owner_name = owners.get(c.owner_id)
    return items


def list_collections(db: Session, user: User, *, page: int, page_size: int, search: str | None, sort_by: str, sort_order: str, scope: str = "all"):
    """`scope`: owned (collections I own), shared (shared with me by others) or all."""
    if scope == "owned":
        stmt = select(Collection).where(Collection.owner_id == user.id)
    elif scope == "shared":
        stmt = select(Collection).where(Collection.id.in_(select(CollectionMember.collection_id).where(CollectionMember.user_id == user.id)))
    else:
        stmt = select(Collection).where(Collection.id.in_(access.accessible_collection_ids(user.id)))
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(Collection.name.ilike(f"%{escaped}%", escape="\\"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    direction = asc if sort_order == "asc" else desc
    if sort_by == "documents":
        count = select(func.count()).where(CollectionDocument.collection_id == Collection.id).correlate(Collection).scalar_subquery()
        order = direction(count)
    else:
        order = direction({"name": Collection.name, "updated_at": Collection.updated_at}.get(sort_by, Collection.created_at))
    items = list(db.scalars(stmt.order_by(order, desc(Collection.id)).offset((page - 1) * page_size).limit(page_size)))
    return collection_view(db, items, user), total


def get_collection(db: Session, user: User, collection_id: int) -> Collection:
    coll, _ = access.get_collection(db, user.id, collection_id)
    return collection_view(db, [coll], user)[0]


def create_collection(db: Session, user: User, name: str, description, color, icon) -> Collection:
    _validate_look(color, icon)
    if _name_taken(db, Collection, user.id, name):
        raise _duplicate("collection")
    coll = Collection(owner_id=user.id, name=name, description=(description or "").strip() or None, color=color, icon=icon)
    db.add(coll)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _duplicate("collection") from exc
    db.refresh(coll)
    return collection_view(db, [coll], user)[0]


def update_collection(db: Session, user: User, collection_id: int, fields: dict) -> Collection:
    coll, _ = access.get_collection(db, user.id, collection_id, need=OWNER)
    _validate_look(fields.get("color"), fields.get("icon"))
    if "name" in fields and fields["name"] is not None:
        if _name_taken(db, Collection, user.id, fields["name"], except_id=coll.id):
            raise _duplicate("collection")
        coll.name = fields["name"]
    if "description" in fields:
        coll.description = (fields["description"] or "").strip() or None
    for key in ("color", "icon"):
        if key in fields:
            setattr(coll, key, fields[key])
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _duplicate("collection") from exc
    db.refresh(coll)
    return collection_view(db, [coll], user)[0]


def delete_collection(db: Session, user: User, collection_id: int) -> None:
    """Removes the collection and its memberships only. The documents themselves are kept."""
    coll, _ = access.get_collection(db, user.id, collection_id, need=OWNER)
    db.delete(coll)
    db.commit()


def _owned_document_ids(db: Session, user: User, ids: list[int]) -> list[int]:
    ids = list(dict.fromkeys(ids))
    found = set(db.scalars(select(Document.id).where(Document.user_id == user.id, Document.id.in_(ids))))
    if len(found) != len(ids):
        raise not_found("Document")
    return ids


def add_documents(db: Session, user: User, collection_id: int, document_ids: list[int], move_from: int | None = None) -> Collection:
    # Owners and editors may add. Only documents the caller owns can be added: sharing a collection never lets a member
    # pull in somebody else's private documents.
    coll, _ = access.get_collection(db, user.id, collection_id, need="editor")
    ids = _owned_document_ids(db, user, document_ids)
    if move_from is not None:
        access.get_collection(db, user.id, move_from, need="editor")
    existing = set(db.scalars(select(CollectionDocument.document_id).where(CollectionDocument.collection_id == coll.id, CollectionDocument.document_id.in_(ids))))
    for doc_id in ids:
        if doc_id not in existing:
            db.add(CollectionDocument(collection_id=coll.id, document_id=doc_id))
    if move_from is not None and move_from != coll.id:  # one transaction: a move never leaves a document in neither place
        db.execute(delete(CollectionDocument).where(CollectionDocument.collection_id == move_from, CollectionDocument.document_id.in_(ids)))
    db.commit()
    db.refresh(coll)
    return collection_view(db, [coll], user)[0]


def remove_document(db: Session, user: User, collection_id: int, document_id: int) -> None:
    coll, _ = access.get_collection(db, user.id, collection_id, need="editor")
    result = db.execute(delete(CollectionDocument).where(CollectionDocument.collection_id == coll.id, CollectionDocument.document_id == document_id))
    if result.rowcount == 0:
        raise not_found("Document in this collection")
    db.commit()


# ------------------------------------------------------------- categories
def list_categories(db: Session, user: User) -> list[Category]:
    cats = list(db.scalars(select(Category).where(Category.owner_id == user.id).order_by(Category.name)))
    counts = dict(db.execute(select(Document.category_id, func.count()).where(Document.user_id == user.id, Document.category_id.is_not(None)).group_by(Document.category_id)).all())
    for c in cats:
        c.document_count = counts.get(c.id, 0)
    return cats


def create_category(db: Session, user: User, name: str, description) -> Category:
    if _name_taken(db, Category, user.id, name):
        raise _duplicate("category")
    cat = Category(owner_id=user.id, name=name, description=(description or "").strip() or None)
    db.add(cat)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _duplicate("category") from exc
    db.refresh(cat)
    cat.document_count = 0
    return cat


def update_category(db: Session, user: User, category_id: int, fields: dict) -> Category:
    cat = _get(db, Category, user.id, category_id, "Category")
    if fields.get("name") is not None:
        if _name_taken(db, Category, user.id, fields["name"], except_id=cat.id):
            raise _duplicate("category")
        cat.name = fields["name"]
    if "description" in fields:
        cat.description = (fields["description"] or "").strip() or None
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _duplicate("category") from exc
    db.refresh(cat)
    cat.document_count = db.scalar(select(func.count()).select_from(Document).where(Document.category_id == cat.id)) or 0
    return cat


def delete_category(db: Session, user: User, category_id: int) -> None:
    """Documents that used the category become uncategorised (the database sets category_id to NULL)."""
    cat = _get(db, Category, user.id, category_id, "Category")
    db.delete(cat)
    db.commit()


# ------------------------------------------------------------------- tags
def list_tags(db: Session, user: User) -> list[Tag]:
    tags = list(db.scalars(select(Tag).where(Tag.owner_id == user.id).order_by(Tag.name)))
    counts = dict(db.execute(select(DocumentTag.tag_id, func.count()).where(DocumentTag.tag_id.in_([t.id for t in tags] or [0])).group_by(DocumentTag.tag_id)).all())
    for t in tags:
        t.document_count = counts.get(t.id, 0)
    return tags


def create_tag(db: Session, user: User, name: str) -> Tag:
    if _name_taken(db, Tag, user.id, name):
        raise _duplicate("tag")
    tag = Tag(owner_id=user.id, name=name)
    db.add(tag)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _duplicate("tag") from exc
    db.refresh(tag)
    tag.document_count = 0
    return tag


def rename_tag(db: Session, user: User, tag_id: int, name: str) -> Tag:
    tag = _get(db, Tag, user.id, tag_id, "Tag")
    if _name_taken(db, Tag, user.id, name, except_id=tag.id):
        raise _duplicate("tag")
    tag.name = name
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _duplicate("tag") from exc
    db.refresh(tag)
    tag.document_count = db.scalar(select(func.count()).select_from(DocumentTag).where(DocumentTag.tag_id == tag.id)) or 0
    return tag


def delete_tag(db: Session, user: User, tag_id: int) -> None:
    tag = _get(db, Tag, user.id, tag_id, "Tag")
    db.delete(tag)
    db.commit()


# ---------------------------------------------------- document assignment
def document_labels(db: Session, doc_ids: list[int], viewer_id: int | None = None) -> dict[int, dict]:
    """Category, tags and collection ids of the given documents. With `viewer_id`, only collections that viewer can
    access are reported, so the existence of other people's collections is not leaked."""
    out = {i: {"category": None, "tags": [], "collection_ids": []} for i in doc_ids}
    if not doc_ids:
        return out
    for doc_id, cat_id, cat_name in db.execute(select(Document.id, Category.id, Category.name).join(Category, Category.id == Document.category_id).where(Document.id.in_(doc_ids))):
        out[doc_id]["category"] = {"id": cat_id, "name": cat_name}
    for doc_id, tag_id, tag_name in db.execute(select(DocumentTag.document_id, Tag.id, Tag.name).join(Tag, Tag.id == DocumentTag.tag_id).where(DocumentTag.document_id.in_(doc_ids)).order_by(Tag.name)):
        out[doc_id]["tags"].append({"id": tag_id, "name": tag_name})
    stmt = select(CollectionDocument.document_id, CollectionDocument.collection_id).where(CollectionDocument.document_id.in_(doc_ids))
    if viewer_id is not None:
        stmt = stmt.where(CollectionDocument.collection_id.in_(access.accessible_collection_ids(viewer_id)))
    for doc_id, coll_id in db.execute(stmt.order_by(CollectionDocument.collection_id)):
        out[doc_id]["collection_ids"].append(coll_id)
    return out


def update_document_metadata(db: Session, user: User, doc: Document, patch: DocumentMetadataPatch) -> None:
    """Edits category/tags/collections without touching the file, chunks or vectors. The caller has already verified
    write access. Categories and tags live in the DOCUMENT OWNER's namespace (an editor labels a shared document with
    the owner's labels); only the document owner may change which collections it is in."""
    sent = patch.model_fields_set
    owner_id = doc.user_id
    if "collection_ids" in sent and patch.collection_ids is not None and user.id != owner_id:
        raise access.forbidden("Only the document's owner can change which collections it belongs to.")
    if "category_id" in sent:
        if patch.category_id is not None:
            _get(db, Category, owner_id, patch.category_id, "Category")
        doc.category_id = patch.category_id
    if "tags" in sent and patch.tags is not None:
        names: dict[str, str] = {}
        for raw in patch.tags:
            name = " ".join(raw.split())
            if not name:
                continue
            if len(name) > 50:
                raise bad_request("TAG_TOO_LONG", "Tags can be at most 50 characters.")
            names.setdefault(name.lower(), name)  # duplicates within the request collapse
        existing = {t.name.lower(): t for t in db.scalars(select(Tag).where(Tag.owner_id == owner_id))}
        wanted: list[Tag] = []
        for key, name in names.items():
            tag = existing.get(key)
            if tag is None:
                tag = Tag(owner_id=owner_id, name=name)
                db.add(tag)
                db.flush()
            wanted.append(tag)
        db.execute(delete(DocumentTag).where(DocumentTag.document_id == doc.id))
        for tag in wanted:
            db.add(DocumentTag(document_id=doc.id, tag_id=tag.id))
    if "collection_ids" in sent and patch.collection_ids is not None:
        ids = list(dict.fromkeys(patch.collection_ids))
        owned = set(db.scalars(select(Collection.id).where(Collection.owner_id == user.id, Collection.id.in_(ids or [0]))))
        if owned != set(ids):
            raise not_found("Collection")
        # Replaces membership in the caller's OWN collections only; memberships in collections owned by others are untouched.
        db.execute(delete(CollectionDocument).where(CollectionDocument.document_id == doc.id, CollectionDocument.collection_id.in_(select(Collection.id).where(Collection.owner_id == user.id))))
        for cid in ids:
            db.add(CollectionDocument(collection_id=cid, document_id=doc.id))
    db.commit()
    db.refresh(doc)
