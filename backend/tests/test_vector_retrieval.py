from sqlalchemy import text

from app.db.session import engine
from app.services import vector_service
from app.services.embedding_service import get_embedder
from tests.conftest import PARENTAL, WARRANTY, new_user, ready_document


def _doc_owner(doc_id):
    with engine.connect() as conn:
        return conn.execute(text("SELECT user_id FROM documents WHERE id=:i"), {"i": doc_id}).scalar_one()


def test_indexed_vectors_carry_owner_document_and_page_metadata(client):
    a = new_user(client, "a@example.com")
    doc = ready_document(client, a, [PARENTAL, WARRANTY])
    got = vector_service._collection().get(where={"document_id": doc["id"]}, include=["metadatas"])
    assert len(got["ids"]) == 2
    pages = sorted(m["page_number"] for m in got["metadatas"])
    assert pages == [1, 2]
    assert {m["user_id"] for m in got["metadatas"]} == {_doc_owner(doc["id"])}


def test_retrieval_finds_the_relevant_page(client):
    a = new_user(client, "a@example.com")
    doc = ready_document(client, a, [PARENTAL, WARRANTY])
    emb = get_embedder().embed(["how many weeks of paid parental leave"])[0]
    hits = vector_service.query(embedding=emb, user_id=_doc_owner(doc["id"]), document_ids=[doc["id"]], k=2)
    assert hits[0].page_number == 1
    assert hits[0].document_id == doc["id"]
    assert hits[0].similarity > hits[1].similarity


def test_retrieval_never_returns_another_users_chunks(client):
    a, b = new_user(client, "a@example.com"), new_user(client, "b@example.com")
    doc_a = ready_document(client, a, [PARENTAL])
    doc_b = ready_document(client, b, [WARRANTY])
    owner_a, owner_b = _doc_owner(doc_a["id"]), _doc_owner(doc_b["id"])
    emb = get_embedder().embed(["paid parental leave weeks"])[0]

    # B asking about A's document id gets nothing, even though the text matches strongly.
    assert vector_service.query(embedding=emb, user_id=owner_b, document_ids=[doc_a["id"]], k=5) == []
    # B searching only their own documents never sees A's chunk either.
    own = vector_service.query(embedding=emb, user_id=owner_b, document_ids=[doc_b["id"]], k=5)
    assert {h.document_id for h in own} <= {doc_b["id"]}
    # And A can still find their own.
    assert vector_service.query(embedding=emb, user_id=owner_a, document_ids=[doc_a["id"]], k=5)


def test_empty_document_scope_returns_nothing():
    emb = get_embedder().embed(["anything"])[0]
    assert vector_service.query(embedding=emb, user_id=1, document_ids=[], k=5) == []
