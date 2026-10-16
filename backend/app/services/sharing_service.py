"""Collection membership: list, invite, change role, revoke/leave. Only the collection owner manages members."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError, bad_request, not_found
from app.models.knowledge import MEMBER_ROLES, CollectionMember
from app.models.user import User
from app.services import access_service as access
from app.services.access_service import OWNER


def _row(user: User, role: str, added_at) -> dict:
    return {"user_id": user.id, "name": user.name, "email": user.email, "role": role, "added_at": added_at}


def _check_role(role: str) -> None:
    if role not in MEMBER_ROLES:
        raise bad_request("INVALID_ROLE", f"Role must be one of: {', '.join(MEMBER_ROLES)}.")


def list_members(db: Session, user: User, collection_id: int) -> list[dict]:
    """Owner first, then members by name. Any member may see who the collection is shared with."""
    coll, _ = access.get_collection(db, user.id, collection_id)
    owner = db.get(User, coll.owner_id)
    out = [_row(owner, OWNER, coll.created_at)]
    rows = db.execute(select(User, CollectionMember).join(CollectionMember, CollectionMember.user_id == User.id).where(CollectionMember.collection_id == coll.id).order_by(User.name, User.id))
    out += [_row(u, m.role, m.created_at) for u, m in rows]
    return out


def invite(db: Session, user: User, collection_id: int, email: str, role: str) -> dict:
    """Owner only. Shares with an existing, active account; the share is effective immediately (no pending state)."""
    coll, _ = access.get_collection(db, user.id, collection_id, need=OWNER)
    _check_role(role)
    target = db.scalar(select(User).where(func.lower(User.email) == email.strip().lower(), User.is_active.is_(True)))
    if target is None:
        raise AppError(404, "USER_NOT_FOUND", "No registered user has that email address.")
    if target.id == coll.owner_id:
        raise bad_request("ALREADY_OWNER", "That user already owns this collection.")
    if db.scalar(select(CollectionMember.id).where(CollectionMember.collection_id == coll.id, CollectionMember.user_id == target.id)):
        raise AppError(409, "ALREADY_MEMBER", "That user is already a member of this collection.")
    member = CollectionMember(collection_id=coll.id, user_id=target.id, role=role, invited_by=user.id)
    db.add(member)
    try:
        db.commit()
    except IntegrityError as exc:  # two simultaneous invitations
        db.rollback()
        raise AppError(409, "ALREADY_MEMBER", "That user is already a member of this collection.") from exc
    db.refresh(member)
    return _row(target, member.role, member.created_at)


def _member(db: Session, collection_id: int, member_user_id: int) -> CollectionMember:
    m = db.scalar(select(CollectionMember).where(CollectionMember.collection_id == collection_id, CollectionMember.user_id == member_user_id))
    if m is None:
        raise not_found("Member")
    return m


def change_role(db: Session, user: User, collection_id: int, member_user_id: int, role: str) -> dict:
    coll, _ = access.get_collection(db, user.id, collection_id, need=OWNER)
    _check_role(role)
    m = _member(db, coll.id, member_user_id)
    m.role = role
    db.commit()
    db.refresh(m)
    return _row(db.get(User, m.user_id), m.role, m.created_at)


def remove(db: Session, user: User, collection_id: int, member_user_id: int) -> None:
    """The owner can revoke anyone; a member can remove themselves (leave). Access ends immediately."""
    coll, role = access.get_collection(db, user.id, collection_id)
    if role != OWNER and member_user_id != user.id:
        raise access.forbidden("Only the collection owner can remove other members.")
    db.delete(_member(db, coll.id, member_user_id))
    db.commit()
