"""Phase 5: document version history - upload, activation, retrieval isolation, restore, comparison, citations, permissions."""

import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text as sql
from sqlalchemy.exc import IntegrityError

from app import worker
from app.core.config import settings
from app.db.session import engine
from app.main import app
from app.services import job_service, vector_service
from tests.conftest import API, make_pdf, new_conversation, new_user, ready_document, upload, ask
from tests.test_jobs import FlakyEmbedder
from tests.test_rag import use_llm
from tests.test_sharing import make_team, post

V1 = "Primary caregivers are entitled to sixteen weeks of paid parental leave. Secondary caregivers receive six weeks of paid leave."
V2 = "Primary caregivers are entitled to eighteen weeks of paid parental leave. Secondary caregivers receive six weeks of paid leave. Adoption leave is also covered."


def put_version(client, h, doc_id, pages, filename="doc.pdf", note=None, run_worker=True, content_type="application/pdf"):
    data = pages if isinstance(pages, bytes) else make_pdf(pages)
    r = client.post(f"{API}/documents/{doc_id}/versions", files={"file": (filename, data, content_type)}, data={"change_note": note} if note else {}, headers=h)
    if run_worker:
        worker.drain()
    return r


def versions(client, h, doc_id):
    r = client.get(f"{API}/documents/{doc_id}/versions", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def search(client, h, q, mode="keyword"):
    r = client.post(f"{API}/search", json={"query": q, "mode": mode}, headers=h)
    assert r.status_code == 200, r.text
    return [i["document_id"] for i in r.json()["items"] if i["passages"]]


def two_versions(client):
    h = new_user(client, "a@example.com")
    doc = ready_document(client, h, [V1], "policy.pdf")
    r = put_version(client, h, doc["id"], [V2], "policy-v2.pdf", note="Updated leave")
    assert r.status_code == 202, r.text
    return h, doc


# ------------------------------------------------------------ data model
def test_new_documents_start_at_version_one(client):
    h = new_user(client, "a@example.com")
    doc = ready_document(client, h, [V1], "policy.pdf")
    vs = versions(client, h, doc["id"])
    assert len(vs) == 1 and vs[0]["version_number"] == 1 and vs[0]["is_current"] and vs[0]["processing_status"] == "ready"
    assert len(vs[0]["checksum_sha256"]) == 64 and vs[0]["uploaded_by"]["name"] == "Test User" and vs[0]["total_pages"] == 1
    assert client.get(f"{API}/documents/{doc['id']}", headers=h).json()["version_number"] == 1
    assert "storage_path" not in str(vs) and "uploads" not in str(vs)


def test_version_numbers_are_unique_per_document(client):
    h = new_user(client, "a@example.com")
    doc = ready_document(client, h, [V1])
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(sql("INSERT INTO document_versions (document_id, version_number, original_filename, storage_path, file_size, mime_type, processing_status, created_at) VALUES (:d, 1, 'x.pdf', 'x', 1, 'application/pdf', 'ready', NOW())"), {"d": doc["id"]})


# ---------------------------------------------------- upload and activation
def test_new_version_becomes_current_only_after_processing(client):
    h = new_user(client, "a@example.com")
    doc = ready_document(client, h, [V1], "policy.pdf")
    r = put_version(client, h, doc["id"], [V2], "policy-v2.pdf", note="Updated leave", run_worker=False)
    assert r.status_code == 202
    body = r.json()
    assert body["version_number"] == 2 and body["is_current"] is False and body["processing_status"] == "queued" and body["change_note"] == "Updated leave"
    # while it waits: v1 is still current, the document is still ready, v2 text is not searchable
    d = client.get(f"{API}/documents/{doc['id']}", headers=h).json()
    assert d["version_number"] == 1 and d["processing_status"] == "ready"
    assert search(client, h, "eighteen") == [] and search(client, h, "sixteen") == [doc["id"]]
    worker.drain()
    vs = versions(client, h, doc["id"])
    assert [(v["version_number"], v["is_current"], v["processing_status"]) for v in vs] == [(2, True, "ready"), (1, False, "ready")]
    d = client.get(f"{API}/documents/{doc['id']}", headers=h).json()
    assert d["version_number"] == 2 and d["id"] == doc["id"]  # same logical document, no duplicate
    assert client.get(f"{API}/documents", headers=h).json()["total"] == 1


def test_files_are_stored_separately_and_downloadable_per_version(client):
    h, doc = two_versions(client)
    v1, v2 = sorted(versions(client, h, doc["id"]), key=lambda v: v["version_number"])
    f1 = client.get(f"{API}/documents/{doc['id']}/versions/{v1['id']}/download", headers=h)
    f2 = client.get(f"{API}/documents/{doc['id']}/versions/{v2['id']}/download", headers=h)
    assert f1.status_code == f2.status_code == 200 and f1.content != f2.content and f1.content.startswith(b"%PDF-")
    assert "attachment" in f1.headers["content-disposition"] and "-v1.pdf" in f1.headers["content-disposition"]
    inline = client.get(f"{API}/documents/{doc['id']}/versions/{v1['id']}/download", params={"inline": "true"}, headers=h)
    assert "inline" in inline.headers["content-disposition"]
    assert client.get(f"{API}/documents/{doc['id']}/preview", headers=h).content == f2.content  # "current" = v2
    assert client.get(f"{API}/documents/{doc['id']}/preview", params={"version_id": v1["id"]}, headers=h).content == f1.content
    assert v1["checksum_sha256"] != v2["checksum_sha256"]


def test_identical_file_is_rejected_gracefully(client):
    h = new_user(client, "a@example.com")
    data = make_pdf([V1])
    doc = upload(client, h, data).json()
    before = sorted(p.name for p in (settings.upload_path).rglob("*.pdf"))
    r = put_version(client, h, doc["id"], data)
    assert r.status_code == 409 and r.json()["error"]["code"] == "DUPLICATE_VERSION"
    assert len(versions(client, h, doc["id"])) == 1
    assert sorted(p.name for p in settings.upload_path.rglob("*.pdf")) == before  # the rejected copy was not kept


def test_invalid_uploads_are_rejected(client, monkeypatch):
    h = new_user(client, "a@example.com")
    doc = ready_document(client, h, [V1])
    assert put_version(client, h, doc["id"], b"just text", "notes.txt", content_type="text/plain").status_code == 415
    assert put_version(client, h, doc["id"], b"not a pdf at all", "fake.pdf").status_code == 415
    assert put_version(client, h, doc["id"], make_pdf([V2]), "x.pdf", content_type="image/png").status_code == 415
    monkeypatch.setattr(settings, "max_upload_size_mb", 0)
    assert put_version(client, h, doc["id"], make_pdf([V2])).status_code == 413
    assert len(versions(client, h, doc["id"])) == 1


def test_failed_processing_keeps_previous_version_active_and_retry_targets_the_version(client, monkeypatch):
    h = new_user(client, "a@example.com")
    doc = ready_document(client, h, [V1], "policy.pdf")
    monkeypatch.setattr(job_service, "get_embedder", lambda: FlakyEmbedder(None, failures=99))
    r = put_version(client, h, doc["id"], [V2])
    assert r.status_code == 202
    vs = versions(client, h, doc["id"])
    assert vs[0]["version_number"] == 2 and vs[0]["processing_status"] == "failed" and vs[0]["is_current"] is False and "embedding" in vs[0]["processing_error"]
    d = client.get(f"{API}/documents/{doc['id']}", headers=h).json()
    assert d["processing_status"] == "ready" and d["version_number"] == 1  # the active document is untouched
    assert search(client, h, "sixteen") == [doc["id"]] and search(client, h, "eighteen") == []
    assert client.get(f"{API}/documents/{doc['id']}/preview", headers=h).status_code == 200
    # the failed version leaves no passages or vectors behind
    with engine.connect() as conn:
        assert conn.execute(sql("SELECT COUNT(*) FROM document_chunks WHERE version_id=:v"), {"v": vs[0]["id"]}).scalar() == 0

    monkeypatch.undo()
    assert client.post(f"{API}/documents/{doc['id']}/retry", headers=h).status_code == 409  # the CURRENT version is not failed
    r = client.post(f"{API}/documents/{doc['id']}/versions/{vs[0]['id']}/retry", headers=h)
    assert r.status_code == 202
    worker.drain()
    vs = versions(client, h, doc["id"])
    assert vs[0]["is_current"] and vs[0]["processing_status"] == "ready"
    assert search(client, h, "eighteen") == [doc["id"]]


def test_concurrent_uploads_cannot_create_duplicate_numbers(client):
    h = new_user(client, "a@example.com")
    doc = ready_document(client, h, [V1])
    barrier = threading.Barrier(4)
    pdfs = [make_pdf([f"Concurrent upload number {i} with distinct words {i * 7919}."]) for i in range(4)]

    def go(i):
        c = TestClient(app)
        barrier.wait()
        return c.post(f"{API}/documents/{doc['id']}/versions", files={"file": (f"c{i}.pdf", pdfs[i], "application/pdf")}, headers=h).status_code

    with ThreadPoolExecutor(4) as pool:
        codes = list(pool.map(go, range(4)))
    assert codes.count(202) == 1 and codes.count(409) == 3, codes
    worker.drain()
    numbers = [v["version_number"] for v in versions(client, h, doc["id"])]
    assert sorted(numbers) == [1, 2]
    assert len(list(settings.upload_path.rglob("*.pdf"))) == 2  # rejected uploads were cleaned up


# ------------------------------------------------- retrieval and citations
def test_only_the_current_version_is_searchable_and_old_vectors_are_removed(client):
    h, doc = two_versions(client)
    for mode in ("keyword", "semantic", "hybrid"):
        assert search(client, h, "eighteen weeks paid parental leave", mode) == [doc["id"]], mode
    for mode in ("keyword", "hybrid"):
        assert search(client, h, "sixteen", mode) == [], mode  # superseded text never appears
    r = client.post(f"{API}/search", json={"query": "sixteen weeks of paid parental leave", "mode": "semantic"}, headers=h).json()
    assert all("sixteen" not in p["snippet"] for i in r["items"] for p in i["passages"])
    v1, v2 = sorted(versions(client, h, doc["id"]), key=lambda v: v["version_number"])
    got = vector_service._collection().get(where={"document_id": doc["id"]}, include=["metadatas"])
    assert got["ids"] and {m["version_id"] for m in got["metadatas"]} == {v2["id"]}
    with engine.connect() as conn:  # history is kept in MySQL
        assert conn.execute(sql("SELECT COUNT(*) FROM document_chunks WHERE version_id=:v"), {"v": v1["id"]}).scalar() >= 1


def test_rag_uses_only_current_version_and_citations_name_it(client, monkeypatch):
    h = new_user(client, "a@example.com")
    doc = ready_document(client, h, [V1], "policy.pdf")
    fake = use_llm(monkeypatch, "Primary caregivers get sixteen weeks of paid leave [S1].")
    conv = new_conversation(client, h)
    old = ask(client, h, conv["id"], "How many weeks of paid parental leave do primary caregivers get?").json()["assistant_message"]
    assert old["citations"][0]["version_number"] == 1
    v1_id = old["citations"][0]["version_id"]
    put_version(client, h, doc["id"], [V2])
    fake.calls.clear()
    fake.reply = "Primary caregivers get eighteen weeks of paid leave [S1]."
    new = ask(client, h, conv["id"], "How many weeks of paid parental leave do primary caregivers get?").json()["assistant_message"]
    sent = str(fake.calls[-1][1][-1]["content"])
    assert "eighteen" in sent and "sixteen" not in sent  # the model never sees superseded text
    assert new["citations"][0]["version_number"] == 2 and new["citations"][0]["version_id"] != v1_id
    # the old answer is untouched and now flagged as coming from a superseded version
    hist = client.get(f"{API}/conversations/{conv['id']}", headers=h).json()["messages"]
    first, last = [m for m in hist if m["role"] == "assistant"]
    assert first["content"] == old["content"] and first["citations"][0]["version_is_current"] is False and last["citations"][0]["version_is_current"] is True
    # ... and still opens the exact historical file and page
    c = first["citations"][0]
    hl = client.get(f"{API}/documents/{doc['id']}/highlights", params={"chunk_id": c["chunk_id"]}, headers=h)
    assert hl.status_code == 200 and hl.json()["reliable"] is True
    img_old = client.get(f"{API}/documents/{doc['id']}/pages/1/image", params={"version_id": c["version_id"]}, headers=h)
    img_cur = client.get(f"{API}/documents/{doc['id']}/pages/1/image", headers=h)
    assert img_old.status_code == img_cur.status_code == 200 and img_old.content != img_cur.content


def test_restore_creates_a_new_version_and_updates_retrieval(client):
    h, doc = two_versions(client)
    v1 = next(v for v in versions(client, h, doc["id"]) if v["version_number"] == 1)
    r = client.post(f"{API}/documents/{doc['id']}/versions/{v1['id']}/restore", json={}, headers=h)
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["version_number"] == 3 and body["restored_from_version_number"] == 1 and body["change_note"] == "Restored from version 1" and not body["is_current"]
    # a duplicate submission while it is processing is refused, and the old current version stays searchable
    assert client.post(f"{API}/documents/{doc['id']}/versions/{v1['id']}/restore", json={}, headers=h).status_code == 409
    assert search(client, h, "eighteen") == [doc["id"]]
    worker.drain()
    vs = versions(client, h, doc["id"])
    assert [(v["version_number"], v["is_current"]) for v in vs] == [(3, True), (2, False), (1, False)]
    assert search(client, h, "sixteen") == [doc["id"]] and search(client, h, "eighteen") == []
    got = vector_service._collection().get(where={"document_id": doc["id"]}, include=["metadatas"])
    assert {m["version_id"] for m in got["metadatas"]} == {vs[0]["id"]}
    # history files are all still there and distinct files
    assert len({Path(p).name for p in [str(x) for x in settings.upload_path.rglob("*.pdf")]}) == 3
    # restoring the current version, or an unfinished one, is refused
    assert client.post(f"{API}/documents/{doc['id']}/versions/{vs[0]['id']}/restore", json={}, headers=h).status_code == 409
    again = client.post(f"{API}/documents/{doc['id']}/versions/{vs[1]['id']}/restore", json={"change_note": "Back to 18 weeks"}, headers=h)
    assert again.status_code == 202 and again.json()["version_number"] == 4 and again.json()["change_note"] == "Back to 18 weeks"


def test_restore_failure_leaves_current_version_usable(client, monkeypatch):
    h, doc = two_versions(client)
    v1 = next(v for v in versions(client, h, doc["id"]) if v["version_number"] == 1)
    monkeypatch.setattr(job_service, "get_embedder", lambda: FlakyEmbedder(None, failures=99))
    assert client.post(f"{API}/documents/{doc['id']}/versions/{v1['id']}/restore", json={}, headers=h).status_code == 202
    worker.drain()
    vs = versions(client, h, doc["id"])
    assert vs[0]["version_number"] == 3 and vs[0]["processing_status"] == "failed" and vs[1]["is_current"]
    assert search(client, h, "eighteen") == [doc["id"]]
    assert client.post(f"{API}/documents/{doc['id']}/versions/{vs[0]['id']}/restore", json={}, headers=h).status_code == 409  # a failed version cannot be a source


# ----------------------------------------------------------- comparison
def test_compare_reports_added_removed_and_changed_text(client):
    h, doc = two_versions(client)
    v1, v2 = sorted(versions(client, h, doc["id"]), key=lambda v: v["version_number"])
    r = client.get(f"{API}/documents/{doc['id']}/versions/compare", params={"from": v1["id"], "to": v2["id"]}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["comparable"] and body["from_version"]["version_number"] == 1 and body["to_version"]["version_number"] == 2 and body["to_version"]["is_current"]
    assert body["stats"] == {"added": 1, "removed": 0, "changed": 1, "unchanged": 1, "identical": False}
    kinds = [b["type"] for b in body["blocks"]]
    assert "changed" in kinds and "added" in kinds
    changed = next(b for b in body["blocks"] if b["type"] == "changed")
    assert [s["text"] for s in changed["inline"] if s["op"] == "del"] == ["sixteen"] and [s["text"] for s in changed["inline"] if s["op"] == "ins"] == ["eighteen"]
    assert next(b for b in body["blocks"] if b["type"] == "added")["new"][0]["text"].startswith("Adoption leave")
    assert "layout" in body["notice"]
    rev = client.get(f"{API}/documents/{doc['id']}/versions/compare", params={"from": v2["id"], "to": v1["id"]}, headers=h).json()
    assert rev["stats"]["removed"] == 1 and rev["stats"]["added"] == 0  # direction matters


def test_compare_edge_cases(client, monkeypatch):
    h, doc = two_versions(client)
    v1, v2 = sorted(versions(client, h, doc["id"]), key=lambda v: v["version_number"])
    url = f"{API}/documents/{doc['id']}/versions/compare"
    assert client.get(url, params={"from": v1["id"], "to": v1["id"]}, headers=h).status_code == 400
    assert client.get(url, params={"from": v1["id"]}, headers=h).status_code == 422
    assert client.get(url, params={"from": v1["id"], "to": 999999}, headers=h).status_code == 404
    other = ready_document(client, h, ["Something else entirely about gardening."], "other.pdf")
    ov = versions(client, h, other["id"])[0]
    assert client.get(url, params={"from": v1["id"], "to": ov["id"]}, headers=h).status_code == 404  # a version of another document
    # identical text -> reported as identical
    same = put_version(client, h, doc["id"], make_pdf([V2]) + b"\n%padding so the checksum differs\n")
    assert same.status_code == 202
    v3 = versions(client, h, doc["id"])[0]
    r = client.get(url, params={"from": v2["id"], "to": v3["id"]}, headers=h).json()
    assert r["comparable"] and r["stats"]["identical"] is True
    # missing file / failed version / no text degrade to comparable=false, not an error
    with engine.begin() as conn:
        path = conn.execute(sql("SELECT storage_path FROM document_versions WHERE id=:i"), {"i": v1["id"]}).scalar()
    Path(path).rename(path + ".gone")
    gone = client.get(url, params={"from": v1["id"], "to": v2["id"]}, headers=h).json()
    assert gone["comparable"] is False and "no longer available" in gone["reason"] and gone["blocks"] == []
    Path(path + ".gone").rename(path)
    with engine.begin() as conn:
        conn.execute(sql("UPDATE document_versions SET processing_status='failed' WHERE id=:i"), {"i": v1["id"]})
    failed = client.get(url, params={"from": v1["id"], "to": v2["id"]}, headers=h).json()
    assert failed["comparable"] is False and "failed" in failed["reason"]


# ----------------------------------------------------------- permissions
def test_roles_for_version_operations(client):
    t = make_team(client)
    did = t["shared"]["id"]
    v1 = versions(client, t["o"], did)[0]
    base = f"{API}/documents/{did}/versions"
    pdf = make_pdf([V2])
    # viewers: read-only, but they can inspect history, download and compare
    v = t["v"]
    assert len(versions(client, v, did)) == 1
    assert client.get(f"{base}/{v1['id']}", headers=v).status_code == 200
    assert client.get(f"{base}/{v1['id']}/download", headers=v).status_code == 200
    assert client.post(base, files={"file": ("n.pdf", pdf, "application/pdf")}, headers=v).status_code == 403
    assert client.post(f"{base}/{v1['id']}/restore", json={}, headers=v).status_code == 403
    assert client.post(f"{base}/{v1['id']}/retry", headers=v).status_code == 403
    # outsiders cannot tell anything exists
    x = t["x"]
    for call in (lambda: client.get(base, headers=x), lambda: client.get(f"{base}/{v1['id']}", headers=x), lambda: client.get(f"{base}/{v1['id']}/download", headers=x),
                 lambda: client.get(f"{base}/compare", params={"from": 1, "to": 2}, headers=x), lambda: client.post(base, files={"file": ("n.pdf", pdf, "application/pdf")}, headers=x),
                 lambda: client.post(f"{base}/{v1['id']}/restore", json={}, headers=x)):
        assert call().status_code == 404
    # the private document's versions are unreachable through the shared one
    pv = versions(client, t["o"], t["private"]["id"])[0]
    assert client.get(f"{base}/{pv['id']}", headers=t["e"]).status_code == 404
    assert client.get(f"{API}/documents/{t['private']['id']}/versions", headers=t["e"]).status_code == 404
    # editors and owners may upload; the uploader of the file remains the owner
    assert client.post(base, files={"file": ("n.pdf", pdf, "application/pdf")}, headers=t["e"]).status_code == 202
    worker.drain()
    vs = versions(client, t["o"], did)
    assert [x["version_number"] for x in vs] == [2, 1] and vs[0]["uploaded_by"]["name"] == "Test User"
    assert client.post(f"{base}/{vs[1]['id']}/restore", json={}, headers=t["o"]).status_code == 202
    assert client.delete(f"{API}/documents/{did}", headers=t["e"]).status_code == 403  # editors still cannot delete the file


def test_revoked_member_loses_versions_and_historical_citations(client, monkeypatch):
    t = make_team(client)
    did, cid = t["shared"]["id"], t["coll"]["id"]
    use_llm(monkeypatch, "Primary caregivers get sixteen weeks of paid leave [S1].")
    conv = new_conversation(client, t["v"])
    cite = ask(client, t["v"], conv["id"], "How many weeks of paid parental leave do primary caregivers get?").json()["assistant_message"]["citations"][0]
    v1 = versions(client, t["o"], did)[0]
    v_id = next(m["user_id"] for m in client.get(f"{API}/collections/{cid}/members", headers=t["o"]).json() if m["role"] == "viewer")
    client.delete(f"{API}/collections/{cid}/members/{v_id}", headers=t["o"])
    base = f"{API}/documents/{did}"
    assert client.get(f"{base}/versions", headers=t["v"]).status_code == 404
    assert client.get(f"{base}/versions/{v1['id']}/download", headers=t["v"]).status_code == 404
    assert client.get(f"{base}/pages/1/image", params={"version_id": v1["id"]}, headers=t["v"]).status_code == 404
    assert client.get(f"{base}/preview", params={"version_id": v1["id"]}, headers=t["v"]).status_code == 404
    assert client.get(f"{base}/highlights", params={"chunk_id": cite["chunk_id"]}, headers=t["v"]).status_code == 404
    old = client.get(f"{API}/conversations/{conv['id']}", headers=t["v"]).json()["messages"][-1]["citations"][0]
    assert old["excerpt"] is None and old["version_id"] is None and old["chunk_id"] is None and "leave.pdf" not in str(old)


def test_deleting_a_document_removes_every_version_file_and_vector(client):
    h, doc = two_versions(client)
    assert len(list(settings.upload_path.rglob("*.pdf"))) == 2
    assert client.delete(f"{API}/documents/{doc['id']}", headers=h).status_code == 204
    assert list(settings.upload_path.rglob("*.pdf")) == []
    assert vector_service._collection().get(where={"document_id": doc["id"]})["ids"] == []
    with engine.connect() as conn:
        assert conn.execute(sql("SELECT COUNT(*) FROM document_versions WHERE document_id=:d"), {"d": doc["id"]}).scalar() == 0
