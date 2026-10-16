from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import page_of
from app.schemas.knowledge import (
    CategoryOut,
    CategoryPatch,
    CollectionDocumentsIn,
    CollectionIn,
    CollectionOut,
    CollectionPatch,
    InviteIn,
    MemberOut,
    NamedIn,
    RoleIn,
    TagIn,
    TagOut,
)
from app.services import knowledge_service as svc
from app.services import sharing_service
from app.utils.rate_limit import rate_limit

router = APIRouter(tags=["knowledge"])


# ------------------------------------------------------------ collections
@router.get("/collections")
def list_collections(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    search: str | None = Query(None, max_length=100),
    sort_by: Literal["name", "created_at", "updated_at", "documents"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    scope: Literal["all", "owned", "shared"] = "all",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = svc.list_collections(db, user, page=page, page_size=page_size, search=search, sort_by=sort_by, sort_order=sort_order, scope=scope)
    return page_of([CollectionOut.model_validate(c) for c in items], total, page, page_size)


@router.post("/collections", response_model=CollectionOut, status_code=201)
def create_collection(body: CollectionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.create_collection(db, user, body.name, body.description, body.color, body.icon)


@router.get("/collections/{collection_id}", response_model=CollectionOut)
def get_collection(collection_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.get_collection(db, user, collection_id)


@router.patch("/collections/{collection_id}", response_model=CollectionOut)
def update_collection(collection_id: int, body: CollectionPatch, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.update_collection(db, user, collection_id, body.model_dump(exclude_unset=True))


@router.delete("/collections/{collection_id}", status_code=204)
def delete_collection(collection_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Deletes the collection only; its documents are kept (they just leave this collection)."""
    svc.delete_collection(db, user, collection_id)
    return Response(status_code=204)


@router.post("/collections/{collection_id}/documents", response_model=CollectionOut)
def add_documents(collection_id: int, body: CollectionDocumentsIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.add_documents(db, user, collection_id, body.document_ids, body.move_from_collection_id)


@router.delete("/collections/{collection_id}/documents/{document_id}", status_code=204)
def remove_document(collection_id: int, document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    svc.remove_document(db, user, collection_id, document_id)
    return Response(status_code=204)


# ---------------------------------------------------------------- members
@router.get("/collections/{collection_id}/members", response_model=list[MemberOut])
def list_members(collection_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return sharing_service.list_members(db, user, collection_id)


@router.post("/collections/{collection_id}/members", response_model=MemberOut, status_code=201, dependencies=[Depends(rate_limit("invite", 30, 60))])
def invite_member(collection_id: int, body: InviteIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Owner only: share the collection with a registered user by account email."""
    return sharing_service.invite(db, user, collection_id, body.email, body.role)


@router.patch("/collections/{collection_id}/members/{member_user_id}", response_model=MemberOut)
def change_member_role(collection_id: int, member_user_id: int, body: RoleIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return sharing_service.change_role(db, user, collection_id, member_user_id, body.role)


@router.delete("/collections/{collection_id}/members/{member_user_id}", status_code=204)
def remove_member(collection_id: int, member_user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Owner revokes a member's access (or a member leaves by removing themselves). Takes effect immediately."""
    sharing_service.remove(db, user, collection_id, member_user_id)
    return Response(status_code=204)


# ------------------------------------------------------------- categories
@router.get("/categories", response_model=list[CategoryOut])
def list_categories(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.list_categories(db, user)


@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(body: NamedIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.create_category(db, user, body.name, body.description)


@router.patch("/categories/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, body: CategoryPatch, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.update_category(db, user, category_id, body.model_dump(exclude_unset=True))


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Documents in the category are kept and become uncategorised."""
    svc.delete_category(db, user, category_id)
    return Response(status_code=204)


# ------------------------------------------------------------------- tags
@router.get("/tags", response_model=list[TagOut])
def list_tags(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.list_tags(db, user)


@router.post("/tags", response_model=TagOut, status_code=201)
def create_tag(body: TagIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.create_tag(db, user, body.name)


@router.patch("/tags/{tag_id}", response_model=TagOut)
def rename_tag(tag_id: int, body: TagIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.rename_tag(db, user, tag_id, body.name)


@router.delete("/tags/{tag_id}", status_code=204)
def delete_tag(tag_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    svc.delete_tag(db, user, tag_id)
    return Response(status_code=204)
