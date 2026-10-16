"""Phase 3: keyword / semantic / hybrid search, filters, pagination and permission-aware results."""

import json

import pytest
from sqlalchemy import text as sql

from app.db.session import engine
from app.services import search_service, vector_service
from app.services.embedding_service import EmbeddingError
from tests.conftest import API, PARENTAL, WARRANTY, new_user, ready_document
from tests.test_rag import use_llm
from tests.test_sharing import SECRET, make_team, post

RETENTION = "Our document retention policy requires that records be kept for seven years. Retention schedules differ by department."
MODES = ("keyword", "semantic", "hybrid")


def search(client, h, query, **body):
    return client.post(f"{API}/search", json={"query": query, **body}, headers=h)


def titles(r):
    assert r.status_code == 200, r.text
    return [i["title"] for i in r.json()["items"]]


@pytest.fixture
def lib(client):
    h = new_user(client, "a@example.com")
    docs = {
        "leave": ready_document(client, h, [PARENTAL, WARRANTY], "leave.pdf"),
        "retention": ready_document(client, h, [WARRANTY, RETENTION], "records.pdf"),
        "guide": ready_document(client, h, ["Completely unrelated gardening text about soil and compost."], "retention-guide.pdf"),
    }
    return h, docs


# -------------------------------------------------------------- keyword
def test_keyword_single_multiple_and_case_insensitive(client, lib):
    h, docs = lib
    assert titles(search(client, h, "parental", mode="keyword")) == ["leave.pdf"]
    assert titles(search(client, h, "PARENTAL Leave", mode="keyword")) == ["leave.pdf"]
    body = search(client, h, "paid leave", mode="keyword").json()
    assert body["items"][0]["title"] == "leave.pdf" and body["items"][0]["passages"][0]["page_number"] == 1
    assert "parental" in body["items"][0]["passages"][0]["snippet"].lower() or "paid" in body["items"][0]["passages"][0]["snippet"].lower()
    assert body["terms"] == ["paid", "leave"] and body["ranking"]["method"] == "keyword"


def test_exact_phrase_and_word_prefix(client, lib):
    h, _ = lib
    r = search(client, h, '"retention policy"', mode="keyword").json()
    assert r["phrases"] == ["retention policy"]
    assert r["items"][0]["title"] == "records.pdf" and r["items"][0]["passages"][0]["page_number"] == 2
    assert [i["title"] for i in r["items"] if "text" in i["matched_on"]] == ["records.pdf"]
    assert search(client, h, '"policy retention"', mode="keyword").json()["items"] == []  # wrong order is not the phrase
    assert "records.pdf" in titles(search(client, h, "retent", mode="keyword"))  # start-of-word partial match
    assert "records.pdf" not in titles(search(client, h, "tention", mode="keyword"))


def test_phrase_ranks_above_scattered_words(client):
    h = new_user(client, "a@example.com")
    ready_document(client, h, ["The policy was updated. Many records exist. Retention is mentioned later on."], "scattered.pdf")
    ready_document(client, h, ["The retention policy is reviewed yearly."], "exact.pdf")
    assert titles(search(client, h, '"retention policy"', mode="keyword")) == ["exact.pdf"]
    assert titles(search(client, h, "retention policy", mode="keyword"))[0] == "exact.pdf"


def test_title_tag_and_category_matches(client, lib):
    h, docs = lib
    r = search(client, h, "gardening guide", mode="keyword").json()
    assert r["items"][0]["title"] == "retention-guide.pdf"
    cat = client.post(f"{API}/categories", json={"name": "Finance"}, headers=h).json()
    client.patch(f"{API}/documents/{docs['leave']['id']}/metadata", json={"category_id": cat["id"], "tags": ["handbook"]}, headers=h)
    r = search(client, h, "finance", mode="keyword").json()
    assert [(i["title"], i["matched_on"]) for i in r["items"]] == [("leave.pdf", ["category"])] and r["items"][0]["passages"] == []
    assert search(client, h, "handbook", mode="keyword").json()["items"][0]["matched_on"] == ["tag"]


def test_invalid_empty_and_hostile_input(client, lib):
    h, _ = lib
    for bad in ("", "   ", "***", '""', "!!! ???"):
        assert search(client, h, bad).status_code == 422, bad
    assert client.post(f"{API}/search", json={"query": "x" * 301}, headers=h).status_code == 422
    assert client.post(f"{API}/search", json={"query": "a", "mode": "fuzzy"}, headers=h).status_code == 422
    assert client.post(f"{API}/search", json={"query": "a", "page_size": 500}, headers=h).status_code == 422
    for nasty in ("'; DROP TABLE users; --", "+-><()~*\"@", "%_\\", "a OR 1=1 /*", "\x00weird"):
        for mode in MODES:
            assert search(client, h, nasty + " retention", mode=mode).status_code == 200, (nasty, mode)
    assert client.get(f"{API}/documents", headers=h).json()["total"] == 3  # nothing was harmed


def test_no_results_and_short_words(client, lib):
    h, _ = lib
    r = search(client, h, "xylophone", mode="keyword").json()
    assert r["items"] == [] and r["total"] == 0 and r["pages"] == 1
    assert titles(search(client, h, "of", mode="keyword"))  # stop/short words still work (bounded LIKE fallback)


def test_all_terms_first_then_relaxed_to_any(client, lib):
    h, _ = lib
    r = search(client, h, "parental zebra", mode="keyword").json()
    assert [i["title"] for i in r["items"]] == ["leave.pdf"] and r["warnings"] == ["relaxed_to_any_term"]
    assert search(client, h, "parental leave", mode="keyword").json()["warnings"] == []


def test_pagination_and_sorting(client):
    h = new_user(client, "a@example.com")
    for name in ("charlie.pdf", "alpha.pdf", "bravo.pdf"):
        ready_document(client, h, [f"Quarterly budget report for {name[:-4]} division."], name)
    p1 = search(client, h, "budget", mode="keyword", sort_by="title", page_size=2).json()
    p2 = search(client, h, "budget", mode="keyword", sort_by="title", page_size=2, page=2).json()
    assert [i["title"] for i in p1["items"]] == ["alpha.pdf", "bravo.pdf"] and [i["title"] for i in p2["items"]] == ["charlie.pdf"]
    assert p1["total"] == p2["total"] == 3 and p1["pages"] == 2 and p1["total_exact"] is True
    assert titles(search(client, h, "budget", mode="keyword", sort_by="newest")) == ["bravo.pdf", "alpha.pdf", "charlie.pdf"]
    assert search(client, h, "budget", mode="keyword", page=9).json()["items"] == []


# ------------------------------------------------------------- semantic
def test_semantic_finds_relevant_passage_and_not_unrelated_ones(client, lib):
    h, _ = lib
    r = search(client, h, "weeks of paid parental leave for caregivers", mode="semantic").json()
    top = r["items"][0]
    assert top["title"] == "leave.pdf" and top["passages"][0]["page_number"] == 1
    p = top["passages"][0]
    assert p["semantic_rank"] == 1 and 0 < p["semantic_similarity"] <= 1 and p["keyword_rank"] is None
    assert r["ranking"]["score_type"] == "embedding_cosine_similarity"
    assert search(client, h, "zebra quantum submarine", mode="semantic").json()["items"] == []


def test_semantic_failures_degrade_gracefully(client, lib, monkeypatch):
    h, _ = lib

    def broken(*a, **k):
        raise EmbeddingError("offline")

    monkeypatch.setattr(search_service, "get_embedder", lambda: type("E", (), {"embed": broken})())
    r = search(client, h, "parental leave", mode="semantic")
    assert r.status_code == 503 and r.json()["error"]["code"] == "SEMANTIC_SEARCH_UNAVAILABLE" and "offline" not in r.text
    hybrid = search(client, h, "parental leave", mode="hybrid").json()
    assert hybrid["warnings"] == ["semantic_unavailable"] and hybrid["items"][0]["title"] == "leave.pdf" and hybrid["ranking"]["method"] == "keyword"
    monkeypatch.undo()

    def chroma_down(**k):
        raise RuntimeError("index corrupted at /secret/path")

    monkeypatch.setattr(vector_service, "query", chroma_down)
    r = search(client, h, "parental leave", mode="semantic")
    assert r.status_code == 503 and "/secret/path" not in r.text
    assert search(client, h, "parental leave", mode="keyword").status_code == 200


def test_semantic_hit_without_mysql_chunk_is_dropped(client, lib):
    h, docs = lib
    with engine.begin() as conn:
        conn.execute(sql("DELETE FROM document_chunks WHERE document_id=:d"), {"d": docs["leave"]["id"]})
    assert vector_service._collection().get(where={"document_id": docs["leave"]["id"]})["ids"]  # orphan vectors remain
    r = search(client, h, "weeks of paid parental leave for caregivers", mode="semantic")
    assert r.status_code == 200 and "leave.pdf" not in titles(r)


def test_missing_vector_index_for_empty_library(client):
    h = new_user(client, "a@example.com")
    for mode in MODES:
        r = search(client, h, "anything", mode=mode)
        assert r.status_code == 200 and r.json()["items"] == []


# --------------------------------------------------------------- hybrid
def test_hybrid_merges_duplicates_and_is_deterministic(client, lib):
    h, _ = lib
    body = dict(mode="hybrid")
    a = search(client, h, "paid parental leave weeks", **body).json()
    b = search(client, h, "paid parental leave weeks", **body).json()
    assert a == b
    assert [i["document_id"] for i in a["items"]].count(a["items"][0]["document_id"]) == 1  # one card per document
    top = a["items"][0]
    assert top["title"] == "leave.pdf"
    p = top["passages"][0]
    assert p["keyword_rank"] == 1 and p["semantic_rank"] == 1  # same passage, found by both, shown once
    assert len({(x["page_number"], x["snippet"]) for x in top["passages"]}) == len(top["passages"])
    assert a["ranking"]["method"] == "rrf" and a["ranking"]["rrf_k"] == 60
    from app.core.config import settings

    assert top["score"] == pytest.approx(2 / (settings.search_rrf_k + 1), abs=1e-5)


def test_hybrid_keyword_weight_is_configurable(client, lib, monkeypatch):
    from app.core.config import settings

    h, _ = lib
    monkeypatch.setattr(settings, "search_keyword_weight", 3.0)
    top = search(client, h, "paid parental leave weeks", mode="hybrid").json()["items"][0]
    assert top["score"] == pytest.approx(4 / (settings.search_rrf_k + 1), abs=1e-5)


@pytest.mark.parametrize("mode", MODES)
def test_filters_work_in_every_mode(client, mode):
    h = new_user(client, "a@example.com")
    d1 = ready_document(client, h, [PARENTAL], "one.pdf")
    d2 = ready_document(client, h, [PARENTAL + " Extra."], "two.pdf")
    cat = client.post(f"{API}/categories", json={"name": "HR"}, headers=h).json()
    coll = client.post(f"{API}/collections", json={"name": "People"}, headers=h).json()
    client.patch(f"{API}/documents/{d1['id']}/metadata", json={"category_id": cat["id"], "tags": ["leave"], "collection_ids": [coll["id"]]}, headers=h)
    tag = client.get(f"{API}/tags", headers=h).json()[0]
    q = "paid parental leave"
    assert sorted(titles(search(client, h, q, mode=mode))) == ["one.pdf", "two.pdf"]
    assert titles(search(client, h, q, mode=mode, category_id=cat["id"])) == ["one.pdf"]
    assert titles(search(client, h, q, mode=mode, category_id=0)) == ["two.pdf"]
    assert titles(search(client, h, q, mode=mode, tag_id=tag["id"])) == ["one.pdf"]
    assert titles(search(client, h, q, mode=mode, collection_id=coll["id"])) == ["one.pdf"]
    assert sorted(titles(search(client, h, q, mode=mode, file_type="pdf"))) == ["one.pdf", "two.pdf"]
    assert titles(search(client, h, q, mode=mode, collection_id=coll["id"], category_id=0)) == []
    assert search(client, h, q, mode=mode, file_type="docx").status_code == 422
    one = search(client, h, q, mode=mode, collection_id=coll["id"]).json()["items"][0]
    assert one["category"]["name"] == "HR" and [t["name"] for t in one["tags"]] == ["leave"] and [c["name"] for c in one["collections"]] == ["People"]


# ---------------------------------------------------------- permissions
@pytest.mark.parametrize("mode", MODES)
def test_members_search_shared_documents_but_never_private_ones(client, monkeypatch, mode):
    fake = use_llm(monkeypatch, "should never be called")
    t = make_team(client)
    for who in ("e", "v"):
        r = search(client, t[who], "parental leave paid", mode=mode)
        assert titles(r) == ["leave.pdf"], (who, mode)
        assert r.json()["items"][0]["role"] == {"e": "editor", "v": "viewer"}[who]
    for probe in ("confidential merger Bluebird budget", "secret", "nine million"):
        r = search(client, t["v"], probe, mode=mode)
        raw = json.dumps(r.json()["items"])  # the response echoes the caller's own query; everything else must be clean
        assert r.status_code == 200 and "Bluebird" not in raw and "secret.pdf" not in raw and str(t["private"]["id"]) not in json.dumps([i["document_id"] for i in r.json()["items"]])
        assert r.json()["total"] == 0 or all(i["title"] == "leave.pdf" for i in r.json()["items"])
    assert fake.calls == []  # search never involves the LLM
    assert titles(search(client, t["o"], "confidential merger Bluebird", mode=mode)) == ["secret.pdf"]
    assert search(client, t["x"], "parental leave", mode=mode).json() == {**search(client, t["x"], "parental leave", mode=mode).json()}
    assert search(client, t["x"], "parental leave", mode=mode).json()["total"] == 0


@pytest.mark.parametrize("mode", MODES)
def test_revoked_access_removes_results_at_once(client, mode):
    t = make_team(client)
    cid = t["coll"]["id"]
    assert titles(search(client, t["v"], "parental leave", mode=mode)) == ["leave.pdf"]
    v_id = next(m["user_id"] for m in client.get(f"{API}/collections/{cid}/members", headers=t["o"]).json() if m["role"] == "viewer")
    client.delete(f"{API}/collections/{cid}/members/{v_id}", headers=t["o"])
    r = search(client, t["v"], "parental leave", mode=mode)
    assert r.status_code == 200 and r.json()["items"] == [] and r.json()["total"] == 0
    # removing the document from the collection has the same effect for the remaining members
    client.delete(f"{API}/collections/{cid}/documents/{t['shared']['id']}", headers=t["o"])
    assert search(client, t["e"], "parental leave", mode=mode).json()["items"] == []


def test_filters_cannot_be_used_to_bypass_authorization(client):
    t = make_team(client)
    solo = post(client, t["o"], "/collections", {"name": "Solo"}).json()
    post(client, t["o"], f"/collections/{solo['id']}/documents", {"document_ids": [t["private"]["id"]]})
    cat = client.post(f"{API}/categories", json={"name": "Hidden"}, headers=t["o"]).json()
    client.patch(f"{API}/documents/{t['private']['id']}/metadata", json={"category_id": cat["id"], "tags": ["conf"]}, headers=t["o"])
    tag = client.get(f"{API}/tags", headers=t["o"]).json()[0]
    v = t["v"]
    assert search(client, v, "confidential", collection_id=solo["id"]).status_code == 404  # same as a missing collection
    for kw in (dict(category_id=cat["id"]), dict(tag_id=tag["id"])):
        for mode in MODES:
            r = search(client, v, "confidential merger Bluebird", mode=mode, **kw)
            assert r.status_code == 200 and r.json()["items"] == [] and r.json()["total"] == 0
    assert search(client, v, "x", collection_id=99999).status_code == 404


def test_search_requires_authentication(client):
    assert client.post(f"{API}/search", json={"query": "a"}).status_code == 401
    assert SECRET  # shared fixture text is imported for the permission tests above
