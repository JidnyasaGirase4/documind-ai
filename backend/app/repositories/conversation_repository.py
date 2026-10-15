"""Every query takes a user_id: conversations are never fetched without the owner filter."""

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message


def get_owned(db: Session, user_id: int, conversation_id: int) -> Conversation | None:
    return db.scalar(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id))


def list_owned(db: Session, user_id: int, *, page: int, page_size: int, search: str | None = None) -> tuple[list[Conversation], int]:
    stmt = select(Conversation).where(Conversation.user_id == user_id)
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(Conversation.title.ilike(f"%{escaped}%", escape="\\"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.order_by(desc(Conversation.updated_at), desc(Conversation.id)).offset((page - 1) * page_size).limit(page_size)
    return list(db.scalars(stmt)), total


def message_counts(db: Session, conversation_ids: list[int]) -> dict[int, int]:
    if not conversation_ids:
        return {}
    rows = db.execute(
        select(Message.conversation_id, func.count()).where(Message.conversation_id.in_(conversation_ids)).group_by(Message.conversation_id)
    )
    return {cid: n for cid, n in rows}


def recent_messages(db: Session, conversation_id: int, limit: int) -> list[Message]:
    rows = list(db.scalars(select(Message).where(Message.conversation_id == conversation_id).order_by(desc(Message.id)).limit(limit)))
    return list(reversed(rows))
