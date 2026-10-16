"""Statistics, activity and analytics. Every query is scoped to the given user."""

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message
from app.models.document import ALL_STATUSES, Document
from app.models.user import User
from app.utils.time import utcnow

ANALYTICS_DAYS = 30


def stats(db: Session, user: User) -> dict:
    rows = dict(db.execute(select(Document.processing_status, func.count()).where(Document.user_id == user.id).group_by(Document.processing_status)).all())
    return {
        "total_documents": sum(rows.values()),
        "ready_documents": rows.get("ready", 0),
        "processing_documents": rows.get("uploaded", 0) + rows.get("queued", 0) + rows.get("processing", 0),
        "failed_documents": rows.get("failed", 0),
    }


def activity(db: Session, user: User, limit: int = 10) -> list[dict]:
    uploads = db.execute(
        select(Document.original_filename, Document.created_at).where(Document.user_id == user.id).order_by(Document.created_at.desc()).limit(limit)
    ).all()
    questions = db.execute(
        select(Conversation.title, Message.created_at)
        .join(Message, Message.conversation_id == Conversation.id)
        .where(Conversation.user_id == user.id, Message.role == "user")
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(limit)
    ).all()
    items = [{"type": "upload", "title": f"Uploaded {name}", "timestamp": ts} for name, ts in uploads]
    items += [{"type": "question", "title": f'Asked a question in "{title}"', "timestamp": ts} for title, ts in questions]
    items.sort(key=lambda i: i["timestamp"], reverse=True)
    return items[:limit]


def _daily_series(rows, days: int) -> list[dict]:
    counts = {str(d): n for d, n in rows}
    today = utcnow().date()
    return [{"date": str(day), "count": counts.get(str(day), 0)} for day in (today - timedelta(days=i) for i in range(days - 1, -1, -1))]


def analytics(db: Session, user: User) -> dict:
    since = (utcnow() - timedelta(days=ANALYTICS_DAYS - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    uploads = db.execute(
        select(func.date(Document.created_at), func.count()).where(Document.user_id == user.id, Document.created_at >= since).group_by(func.date(Document.created_at))
    ).all()
    questions = db.execute(
        select(func.date(Message.created_at), func.count())
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Conversation.user_id == user.id, Message.role == "user", Message.created_at >= since)
        .group_by(func.date(Message.created_at))
    ).all()
    by_status = dict(db.execute(select(Document.processing_status, func.count()).where(Document.user_id == user.id).group_by(Document.processing_status)).all())
    return {
        "uploads_over_time": _daily_series(uploads, ANALYTICS_DAYS),
        "status_distribution": [{"status": s, "count": by_status.get(s, 0)} for s in ALL_STATUSES],
        "question_activity": _daily_series(questions, ANALYTICS_DAYS),
    }
