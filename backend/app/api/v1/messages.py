from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.v1.conversations import message_out
from app.db.session import get_db
from app.models.user import User
from app.schemas.conversations import FeedbackIn, FeedbackOut, MessageCreate, SendMessageResponse
from app.services import conversation_service, feedback_service
from app.utils.rate_limit import rate_limit

router = APIRouter(prefix="/conversations", tags=["messages"])


@router.post(
    "/{conversation_id}/messages",
    response_model=SendMessageResponse,
    status_code=201,
    dependencies=[Depends(rate_limit("messages", 30, 60))],
)
def send_message(conversation_id: int, body: MessageCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Ask a question. The answer is generated from the user's own documents and carries validated citations."""
    user_msg, assistant_msg = conversation_service.send_message(db, user, conversation_id, body.content, body.document_ids)
    return SendMessageResponse(user_message=message_out(user_msg), assistant_message=message_out(assistant_msg))


@router.put("/{conversation_id}/messages/{message_id}/feedback", response_model=FeedbackOut)
def set_feedback(conversation_id: int, message_id: int, body: FeedbackIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Thumbs up/down (with an optional category and note) on one of the assistant's answers. Sending it again replaces it."""
    return feedback_service.set_feedback(db, user, conversation_id, message_id, body.rating, body.category, body.comment)


@router.delete("/{conversation_id}/messages/{message_id}/feedback", status_code=204)
def clear_feedback(conversation_id: int, message_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    feedback_service.clear_feedback(db, user, conversation_id, message_id)
    return Response(status_code=204)
