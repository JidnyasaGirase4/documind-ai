"""Thumbs up/down and optional written feedback on assistant answers. Owner-only: a message is reachable only through
a conversation the user owns."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, bad_request
from app.models.conversation import Message
from app.models.quality import RATING_DOWN, MessageFeedback
from app.models.user import User
from app.repositories import conversation_repository as conv_repo
from app.utils.time import utcnow


def _assistant_message(db: Session, user: User, conversation_id: int, message_id: int) -> Message:
    conv = conv_repo.get_owned(db, user.id, conversation_id)
    msg = db.get(Message, message_id) if conv else None
    if conv is None or msg is None or msg.conversation_id != conv.id:
        raise AppError(404, "NOT_FOUND", "Message not found.")
    if msg.role != "assistant":
        raise bad_request("NOT_AN_ANSWER", "Feedback can only be given on the assistant's answers.")
    return msg


def for_messages(db: Session, user_id: int, message_ids: list[int]) -> dict[int, MessageFeedback]:
    if not message_ids:
        return {}
    rows = db.scalars(select(MessageFeedback).where(MessageFeedback.user_id == user_id, MessageFeedback.message_id.in_(message_ids)))
    return {f.message_id: f for f in rows}


def set_feedback(db: Session, user: User, conversation_id: int, message_id: int, rating: str, category: str | None, comment: str | None) -> MessageFeedback:
    msg = _assistant_message(db, user, conversation_id, message_id)
    row = db.scalar(select(MessageFeedback).where(MessageFeedback.message_id == msg.id, MessageFeedback.user_id == user.id))
    if row is None:
        row = MessageFeedback(message_id=msg.id, user_id=user.id, rating=rating)
        db.add(row)
    row.rating = rating
    # A reason only makes sense for a thumbs-down.
    row.category = category if rating == RATING_DOWN else None
    row.comment = comment
    row.updated_at = utcnow()
    db.commit()
    db.refresh(row)
    return row


def clear_feedback(db: Session, user: User, conversation_id: int, message_id: int) -> None:
    msg = _assistant_message(db, user, conversation_id, message_id)
    row = db.scalar(select(MessageFeedback).where(MessageFeedback.message_id == msg.id, MessageFeedback.user_id == user.id))
    if row is not None:
        db.delete(row)
        db.commit()
