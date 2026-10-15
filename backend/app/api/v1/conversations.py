from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.repositories import conversation_repository as repo
from app.schemas.common import page_of
from app.schemas.conversations import ConversationCreate, ConversationDetail, ConversationOut, ConversationUpdate, MessageOut
from app.services import conversation_service

router = APIRouter(prefix="/conversations", tags=["conversations"])


def message_out(m: Message) -> MessageOut:
    return MessageOut(id=m.id, role=m.role, content=m.content, citations=m.citation_metadata or [], created_at=m.created_at)


def conversation_out(c: Conversation, message_count: int) -> ConversationOut:
    return ConversationOut(id=c.id, title=c.title, created_at=c.created_at, updated_at=c.updated_at, message_count=message_count)


@router.post("", response_model=ConversationOut, status_code=201)
def create_conversation(body: ConversationCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return conversation_out(conversation_service.create(db, user, body.title), 0)


@router.get("")
def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str | None = Query(None, max_length=255),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = repo.list_owned(db, user.id, page=page, page_size=page_size, search=search)
    counts = repo.message_counts(db, [c.id for c in items])
    return page_of([conversation_out(c, counts.get(c.id, 0)) for c in items], total, page, page_size)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = conversation_service.get_or_404(db, user, conversation_id)
    messages = [message_out(m) for m in conv.messages]  # ordered by id, i.e. chronologically
    return ConversationDetail(
        id=conv.id, title=conv.title, created_at=conv.created_at, updated_at=conv.updated_at, message_count=len(messages), messages=messages
    )


@router.patch("/{conversation_id}", response_model=ConversationOut)
def rename_conversation(conversation_id: int, body: ConversationUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = conversation_service.rename(db, user, conversation_id, body.title)
    return conversation_out(conv, repo.message_counts(db, [conv.id]).get(conv.id, 0))


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation_service.delete(db, user, conversation_id)
    return Response(status_code=204)
