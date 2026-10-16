from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.search import SearchRequest, SearchResponse
from app.services import search_service
from app.utils.rate_limit import rate_limit

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse, dependencies=[Depends(rate_limit("search", 60, 60))])
def search(body: SearchRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Keyword, semantic or hybrid search across the passages of every document the caller may read (own documents and
    documents in collections shared with them). Authorization is resolved in MySQL before any content is retrieved."""
    return search_service.search(db, user, body)
