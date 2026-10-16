import time

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.conversation import DEFAULT_CONVERSATION_TITLE, Conversation, Message
from app.models.quality import OUTCOME_ANSWERED, OUTCOME_ERROR, OUTCOME_INSUFFICIENT, QueryLog
from app.models.user import User
from app.repositories import conversation_repository as repo
from app.services import rag_service
from app.utils.time import utcnow


def get_or_404(db: Session, user: User, conversation_id: int) -> Conversation:
    # Another user's conversation is reported as "not found" so ids cannot be probed.
    conv = repo.get_owned(db, user.id, conversation_id)
    if conv is None:
        raise AppError(404, "NOT_FOUND", "Conversation not found.")
    return conv


def create(db: Session, user: User, title: str | None) -> Conversation:
    conv = Conversation(user_id=user.id, title=(title or "").strip() or DEFAULT_CONVERSATION_TITLE)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def rename(db: Session, user: User, conversation_id: int, title: str) -> Conversation:
    conv = get_or_404(db, user, conversation_id)
    conv.title = title
    db.commit()
    db.refresh(conv)
    return conv


def delete(db: Session, user: User, conversation_id: int) -> None:
    conv = get_or_404(db, user, conversation_id)
    db.delete(conv)
    db.commit()


def _title_from(question: str) -> str:
    text = " ".join(question.split())
    return text if len(text) <= 60 else text[:57].rstrip() + "..."


def send_message(db: Session, user: User, conversation_id: int, content: str, document_ids: list[int] | None) -> tuple[Message, Message]:
    """Answers a question. Both messages are saved together only if answering succeeded, so a failed
    LLM call never leaves a dangling question behind (the user can simply retry)."""
    conv = get_or_404(db, user, conversation_id)
    started = time.perf_counter()
    try:
        answer = rag_service.answer_question(db, user, conv, content, document_ids)
    except AppError as exc:
        _log_failure(db, user, conv, started, exc.code)
        raise
    except Exception:
        _log_failure(db, user, conv, started, "UNEXPECTED_ERROR")
        raise
    latency_ms = int((time.perf_counter() - started) * 1000)

    now = utcnow()
    user_msg = Message(conversation_id=conv.id, role="user", content=content, created_at=now)
    assistant_msg = Message(conversation_id=conv.id, role="assistant", content=answer.content, citation_metadata=answer.citations or None, created_at=now)
    db.add_all([user_msg, assistant_msg])
    db.flush()
    db.add(
        QueryLog(
            user_id=user.id,
            conversation_id=conv.id,
            message_id=assistant_msg.id,
            outcome=OUTCOME_ANSWERED if answer.citations else OUTCOME_INSUFFICIENT,
            latency_ms=latency_ms,
            document_count=answer.document_count,
            source_count=answer.source_count,
            citation_count=len(answer.citations),
            created_at=now,
        )
    )
    if conv.title == DEFAULT_CONVERSATION_TITLE:
        conv.title = _title_from(content)
    conv.updated_at = now
    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)
    return user_msg, assistant_msg


def _log_failure(db: Session, user: User, conv: Conversation, started: float, code: str) -> None:
    """Failed questions leave no messages, but they still count in the failure statistics."""
    try:
        db.rollback()
        db.add(
            QueryLog(user_id=user.id, conversation_id=conv.id, outcome=OUTCOME_ERROR, error_code=code[:50], latency_ms=int((time.perf_counter() - started) * 1000))
        )
        db.commit()
    except Exception:
        db.rollback()
