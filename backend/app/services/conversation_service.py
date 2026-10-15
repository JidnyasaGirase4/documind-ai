from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.conversation import DEFAULT_CONVERSATION_TITLE, Conversation, Message
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
    answer = rag_service.answer_question(db, user, conv, content, document_ids)

    now = utcnow()
    user_msg = Message(conversation_id=conv.id, role="user", content=content, created_at=now)
    assistant_msg = Message(conversation_id=conv.id, role="assistant", content=answer.content, citation_metadata=answer.citations or None, created_at=now)
    db.add_all([user_msg, assistant_msg])
    if conv.title == DEFAULT_CONVERSATION_TITLE:
        conv.title = _title_from(content)
    conv.updated_at = now
    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)
    return user_msg, assistant_msg
