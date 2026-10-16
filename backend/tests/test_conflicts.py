"""Phase 6b: evidence-based potential-conflict detection. The LLM is replaced by a test double that behaves like a judge
(these tests check OUR pipeline: scope, validation, evidence, versions, permissions; they are not live AI)."""

import json

import pytest
from sqlalchemy import text as sql

from app import worker
from app.core.errors import AppError
from app.db.session import engine
from app.services import conflict_service, vector_service
from app.services.embedding_service import EmbeddingError
from tests.conftest import API, new_user, ready_document
from tests.test_sharing import make_team, post
from tests.test_versions import put_version, versions

SEVEN = "Employee records must be retained for seven years after the employment ends, as required by the retention policy."
THREE = "Employee records must be retained for three years after the employment ends, as required by the retention policy."
HR_ARCHIVE = "Employee records are kept in the HR archive and must be retained for seven years after the employment ends."
FIN_ARCHIVE = "Employee records are kept in the finance archive and must be retained for seven years after the employment ends."
PARKING = "Visitor parking is allowed in the east lot only and must be registered within two days."


class Judge:
    """Records every prompt it receives and answers with `reply(prompt)`."""

    def __init__(self, reply):
        self.reply, self.prompts = reply, []

    def generate(self, system, messages):
        self.prompts.append(messages[-1]["content"])
        out = self.reply(messages[-1]["content"])
        if isinstance(out, Exception):
            raise out
        return out if isinstance(out, str) else json.dumps(out)


def contradiction(prompt):
    if "seven years" in prompt and "three years" in prompt:
        return {"verdict": "conflict", "type": "value_mismatch", "explanation": "Retention is seven years in one and three in the other.",
                "quote_a": "retained for seven years", "quote_b": "retained for three years"}
    return {"verdict": "compatible", "type": "other", "explanation": "Same rule.", "quote_a": "", "quote_b": ""}


def use_judge(monkeypatch, reply=contradiction) -> Judge:
    j = Judge(reply)
    monkeypatch.setattr(conflict_service, "get_llm", lambda: j)
    return j


def analyze(client, h, **scope):
    r = client.post(f"{API}/conflicts/analyze", json=scope, headers=h)
    assert r.status_code == 202, r.text
    report = client.get(f"{API}/conflicts/reports/{r.json()['id']}", headers=h).json()
    return report


def findings(client, h, **params):
    r = client.get(f"{API}/conflicts", params=params, headers=h)
    assert r.status_code == 200, r.text
    return r.json()["items"]


@pytest.fixture
def pair(client):
    h = new_user(client, "a@example.com")
    a = ready_document(client, h, [SEVEN], "retention-2024.pdf")
    b = ready_document(client, h, [THREE], "retention-2020.pdf")
    c = ready_document(client, h, [PARKING], "parking.pdf")
    return h, a, b, c


# ---------------------------------------------------------------- detection
def test_a_clear_contradiction_is_reported_with_evidence_from_both_sources(client, pair, monkeypatch):
    h, a, b, c = pair
    judge = use_judge(monkeypatch)
    report = analyze(client, h, document_id=a["id"])
    assert report["status"] == "completed" and report["findings_created"] == 1 and report["passages_examined"] >= 1
    (f,) = findings(client, h)
    assert f["assessment"] == "potential_conflict" and f["review_status"] == "pending" and f["conflict_type"] == "value_mismatch" and f["quotes_verified"] is True
    assert f["kind"] == "cross_document" and f["stale"] is False and f["can_decide"] is True and f["reviewed_by"] is None
    srcs = {s["title"]: s for s in (f["source_a"], f["source_b"])}
    assert set(srcs) == {"retention-2024.pdf", "retention-2020.pdf"}
    assert "seven years" in srcs["retention-2024.pdf"]["excerpt"] and "three years" in srcs["retention-2020.pdf"]["excerpt"]
    for s in srcs.values():
        assert s["version_number"] == 1 and s["is_current_version"] and s["page"] == 1 and s["chunk_id"].startswith("chunk-")
    # the model only ever saw the two passages (never whole documents, never the unrelated parking document)
    assert all("parking" not in p.lower() and "east lot" not in p for p in judge.prompts)
    assert len(judge.prompts) <= 12
    # re-running does not duplicate the same evidence
    again = analyze(client, h, document_id=a["id"])
    assert again["findings_created"] == 0 and len(findings(client, h)) == 1


def test_similar_but_compatible_passages_are_not_reported(client, monkeypatch):
    h = new_user(client, "a@example.com")
    a = ready_document(client, h, [HR_ARCHIVE], "hr.pdf")
    ready_document(client, h, [FIN_ARCHIVE], "finance.pdf")
    use_judge(monkeypatch, lambda p: {"verdict": "compatible", "type": "other", "explanation": "Different archives, same period.", "quote_a": "", "quote_b": ""})
    report = analyze(client, h, document_id=a["id"])
    assert report["status"] == "completed" and report["findings_created"] == 0 and report["pairs_compatible"] >= 1
    assert findings(client, h) == []


def test_similarity_alone_never_creates_a_finding(client, monkeypatch):
    h = new_user(client, "a@example.com")
    a = ready_document(client, h, [HR_ARCHIVE], "hr.pdf")
    ready_document(client, h, [FIN_ARCHIVE], "finance.pdf")
    judge = use_judge(monkeypatch, lambda p: "compatible")  # not even JSON
    report = analyze(client, h, document_id=a["id"])
    assert judge.prompts and report["findings_created"] == 0 and report["pairs_unparsed"] >= 1 and findings(client, h) == []


def test_insufficient_or_unverifiable_evidence_needs_human_review(client, pair, monkeypatch):
    h, a, b, c = pair
    use_judge(monkeypatch, lambda p: {"verdict": "unclear", "type": "other", "explanation": "Cannot tell whether the scopes match.", "quote_a": "", "quote_b": ""})
    analyze(client, h, document_id=a["id"])
    (f,) = findings(client, h)
    assert f["assessment"] == "needs_review" and f["review_status"] == "pending" and f["quotes_verified"] is False
    # a "conflict" whose quotes are invented is downgraded, not trusted
    with engine.begin() as conn:
        conn.execute(sql("DELETE FROM conflict_decisions"))
        conn.execute(sql("DELETE FROM document_conflicts"))
    use_judge(monkeypatch, lambda p: {"verdict": "conflict", "type": "value_mismatch", "explanation": "They differ.", "quote_a": "twelve decades of storage", "quote_b": "never keep anything"})
    analyze(client, h, document_id=a["id"])
    (f,) = findings(client, h)
    assert f["assessment"] == "needs_review" and f["quotes_verified"] is False and "human review" in f["explanation"]


@pytest.mark.parametrize("reply", ["I believe these conflict.", "{not json}", '{"verdict": "maybe"}', '{"explanation": "no verdict"}', "", '["conflict"]'])
def test_malformed_model_output_is_counted_and_never_stored(client, pair, monkeypatch, reply):
    h, a, b, c = pair
    use_judge(monkeypatch, lambda p: reply)
    report = analyze(client, h, document_id=a["id"])
    assert report["status"] == "completed" and report["findings_created"] == 0 and report["pairs_unparsed"] >= 1
    assert findings(client, h) == []


def test_unknown_conflict_type_is_coerced_and_long_text_is_rejected_safely(client, pair, monkeypatch):
    h, a, b, c = pair
    use_judge(monkeypatch, lambda p: {"verdict": "conflict", "type": "made_up_type", "explanation": "Retention differs.", "quote_a": "retained for seven years", "quote_b": "retained for three years"})
    analyze(client, h, document_id=a["id"])
    assert findings(client, h)[0]["conflict_type"] == "other"
    assert conflict_service.parse_judgement(json.dumps({"verdict": "conflict", "explanation": "x" * 5000})) is None


def test_llm_and_embedding_failures_fail_the_report_cleanly(client, pair, monkeypatch):
    h, a, b, c = pair
    use_judge(monkeypatch, lambda p: AppError(503, "LLM_TIMEOUT", "The AI provider took too long to respond. Please try again."))
    report = analyze(client, h, document_id=a["id"])
    assert report["status"] == "failed" and report["error_code"] == "LLM_TIMEOUT" and "Traceback" not in str(report)
    assert findings(client, h) == []

    def broken(*a, **k):
        raise EmbeddingError("model offline")

    monkeypatch.setattr(conflict_service, "get_embedder", lambda: type("E", (), {"embed": broken})())
    report = analyze(client, h, document_id=a["id"])
    assert report["status"] == "failed" and report["error_code"] == "EMBEDDING_UNAVAILABLE" and "offline" not in str(report)


def test_unready_or_unscoped_requests_are_rejected(client, pair):
    h, a, b, c = pair
    assert client.post(f"{API}/conflicts/analyze", json={}, headers=h).status_code == 422
    assert client.post(f"{API}/conflicts/analyze", json={"document_id": a["id"], "collection_id": 1}, headers=h).status_code == 422
    assert client.post(f"{API}/conflicts/analyze", json={"document_id": 999999}, headers=h).status_code == 404
    assert client.post(f"{API}/conflicts/analyze", json={"collection_id": 999999}, headers=h).status_code == 404


def test_collection_scope_compares_documents_inside_the_collection(client, pair, monkeypatch):
    h, a, b, c = pair
    outside = ready_document(client, h, ["Employee records must be retained for ten years after the employment ends, as required by the retention policy."], "outside.pdf")
    coll = post(client, h, "/collections", {"name": "Policies"}).json()
    post(client, h, f"/collections/{coll['id']}/documents", {"document_ids": [a["id"], b["id"], c["id"]]})
    judge = use_judge(monkeypatch)
    report = analyze(client, h, collection_id=coll["id"])
    assert report["status"] == "completed" and report["findings_created"] == 1
    assert not any("ten years" in p for p in judge.prompts)  # a document outside the collection is not part of its analysis
    assert len(findings(client, h, collection_id=coll["id"])) == 1 and findings(client, h, document_id=outside["id"]) == []


# ---------------------------------------------------- versions and evidence
def test_evidence_is_pinned_to_versions_and_goes_stale_when_a_source_changes(client, pair, monkeypatch):
    h, a, b, c = pair
    use_judge(monkeypatch)
    analyze(client, h, document_id=a["id"])
    (f,) = findings(client, h)
    old_chunk_ids = {f["source_a"]["chunk_id"], f["source_b"]["chunk_id"]}
    assert put_version(client, h, b["id"], ["Employee records must be retained for seven years after the employment ends, as required by the retention policy. Updated."]).status_code == 202
    (f2,) = findings(client, h)
    assert f2["stale"] is True and findings(client, h, stale="true") != [] and findings(client, h, stale="false") == []
    src = next(s for s in (f2["source_a"], f2["source_b"]) if s["title"] == "retention-2020.pdf")
    assert src["version_number"] == 1 and src["is_current_version"] is False and "three years" in src["excerpt"]  # history is not rewritten
    # the old evidence still opens the historical file and page (chunk of version 1 is kept in MySQL)
    hl = client.get(f"{API}/documents/{b['id']}/highlights", params={"chunk_id": src["chunk_id"]}, headers=h)
    assert hl.status_code == 200
    # a fresh analysis only uses current versions (now both say seven years -> nothing to report) and keeps the old finding
    report = analyze(client, h, document_id=a["id"])
    assert report["findings_created"] == 0
    assert {f2["source_a"]["chunk_id"], f2["source_b"]["chunk_id"]} == old_chunk_ids


def test_versions_of_one_document_can_conflict(client, monkeypatch):
    h = new_user(client, "a@example.com")
    d = ready_document(client, h, [SEVEN], "policy.pdf")
    put_version(client, h, d["id"], [THREE])
    use_judge(monkeypatch)
    report = analyze(client, h, document_id=d["id"])
    assert report["findings_created"] == 1
    (f,) = findings(client, h)
    assert f["kind"] == "cross_version" and f["stale"] is False
    sides = sorted([f["source_a"], f["source_b"]], key=lambda s: s["version_number"])
    assert [s["version_number"] for s in sides] == [1, 2] and sides[0]["is_current_version"] is False and sides[1]["is_current_version"] is True
    assert "seven years" in sides[0]["excerpt"] and "three years" in sides[1]["excerpt"]


def test_missing_source_passage_keeps_the_stored_evidence(client, pair, monkeypatch):
    h, a, b, c = pair
    use_judge(monkeypatch)
    analyze(client, h, document_id=a["id"])
    with engine.begin() as conn:
        conn.execute(sql("DELETE FROM document_chunks WHERE document_id=:d"), {"d": b["id"]})
    (f,) = findings(client, h)
    src = next(s for s in (f["source_a"], f["source_b"]) if s["title"] == "retention-2020.pdf")
    assert src["chunk_id"] is None and "three years" in src["excerpt"]


# ------------------------------------------------------------- decisions
def test_reviewer_decisions_are_recorded_and_never_automatic(client, pair, monkeypatch):
    h, a, b, c = pair
    use_judge(monkeypatch)
    analyze(client, h, document_id=a["id"])
    (f,) = findings(client, h)
    assert f["review_status"] == "pending"
    base = f"{API}/conflicts/{f['id']}"
    assert client.patch(f"{base}/decision", json={"decision": "maybe"}, headers=h).status_code == 422
    assert client.patch(f"{base}/decision", json={"decision": "pending"}, headers=h).status_code == 422
    r = client.patch(f"{base}/decision", json={"decision": "confirmed", "note": "Legal says seven years."}, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["review_status"] == "confirmed" and body["reviewed_by"]["name"] == "Test User" and body["review_note"] == "Legal says seven years." and body["reviewed_at"]
    assert body["assessment"] == "potential_conflict"  # the AI's own label is untouched
    client.patch(f"{base}/decision", json={"decision": "not_conflict", "note": "Different scope."}, headers=h)
    hist = client.get(f"{base}/decisions", headers=h).json()
    assert [d["decision"] for d in hist] == ["not_conflict", "confirmed"] and hist[0]["decided_by"]["name"] == "Test User"
    assert [f["review_status"] for f in findings(client, h, review_status="not_conflict")] == ["not_conflict"] and findings(client, h, review_status="pending") == []
    assert client.get(f"{API}/conflicts", params={"review_status": "bogus"}, headers=h).status_code == 422


# ------------------------------------------------------------ permissions
def test_roles_and_scope_of_analysis(client, monkeypatch):
    t = make_team(client)
    did, cid = t["shared"]["id"], t["coll"]["id"]
    judge = use_judge(monkeypatch, lambda p: {"verdict": "conflict", "type": "value_mismatch", "explanation": "Leave periods differ.", "quote_a": "sixteen weeks", "quote_b": "sixteen weeks"})
    # viewers and outsiders cannot start analyses; outsiders cannot even tell the document exists
    assert client.post(f"{API}/conflicts/analyze", json={"document_id": did}, headers=t["v"]).status_code == 403
    assert client.post(f"{API}/conflicts/analyze", json={"collection_id": cid}, headers=t["v"]).status_code == 403
    assert client.post(f"{API}/conflicts/analyze", json={"document_id": did}, headers=t["x"]).status_code == 404
    assert client.post(f"{API}/conflicts/analyze", json={"document_id": t["private"]["id"]}, headers=t["e"]).status_code == 404
    # an editor analyses the shared document: the owner's PRIVATE document is not in the pool and never reaches the model
    report = analyze(client, t["e"], document_id=did)
    assert report["status"] == "completed"
    assert not any("Bluebird" in p or "merger" in p for p in judge.prompts)
    # reports are private to the person who ran them
    assert client.get(f"{API}/conflicts/reports/{report['id']}", headers=t["o"]).status_code == 404
    assert client.get(f"{API}/conflicts/reports", headers=t["o"]).json()["total"] == 0 and client.get(f"{API}/conflicts/reports", headers=t["e"]).json()["total"] == 1


def test_findings_follow_document_access_and_revocation(client, monkeypatch):
    t = make_team(client)
    o, v, e = t["o"], t["v"], t["e"]
    cid = t["coll"]["id"]
    a = ready_document(client, o, [SEVEN], "retention-a.pdf")
    p = ready_document(client, o, [THREE], "private-retention.pdf")  # NOT shared
    post(client, o, f"/collections/{cid}/documents", {"document_ids": [a["id"]]})
    use_judge(monkeypatch)
    analyze(client, o, document_id=a["id"])
    (f,) = findings(client, o)
    assert f["can_decide"] is True
    # the viewer can read only one of the two sources: the finding, its explanation and both excerpts are hidden entirely
    assert findings(client, v) == [] and client.get(f"{API}/conflicts/{f['id']}", headers=v).status_code == 404
    assert client.get(f"{API}/conflicts/{f['id']}/decisions", headers=v).status_code == 404
    assert client.patch(f"{API}/conflicts/{f['id']}/decision", json={"decision": "confirmed"}, headers=v).status_code == 404
    assert "private-retention" not in str(client.get(f"{API}/conflicts", headers=v).json())
    # sharing the second document makes the finding visible; viewers inspect but cannot decide
    post(client, o, f"/collections/{cid}/documents", {"document_ids": [p["id"]]})
    (fv,) = findings(client, v)
    assert fv["id"] == f["id"] and fv["can_decide"] is False and "three years" in str(fv)
    assert client.patch(f"{API}/conflicts/{f['id']}/decision", json={"decision": "confirmed"}, headers=v).status_code == 403
    ed = client.patch(f"{API}/conflicts/{f['id']}/decision", json={"decision": "needs_review", "note": "Ask legal"}, headers=e)
    assert ed.status_code == 200 and ed.json()["reviewed_by"]["id"] != fv["id"] and ed.json()["can_decide"] is True  # an editor of both documents may decide
    # removing one source from the shared collection hides the finding from the viewer at once
    client.delete(f"{API}/collections/{cid}/documents/{p['id']}", headers=o)
    assert findings(client, v) == [] and client.get(f"{API}/conflicts/{f['id']}", headers=v).status_code == 404
    assert findings(client, e) == []  # the editor can no longer read the private document either
    assert len(findings(client, o)) == 1
    # revoking the viewer's membership hides everything, including the decision history
    post(client, o, f"/collections/{cid}/documents", {"document_ids": [p["id"]]})
    assert len(findings(client, v)) == 1
    v_id = next(m["user_id"] for m in client.get(f"{API}/collections/{cid}/members", headers=o).json() if m["role"] == "viewer")
    client.delete(f"{API}/collections/{cid}/members/{v_id}", headers=o)
    assert findings(client, v) == [] and client.get(f"{API}/conflicts/{f['id']}/decisions", headers=v).status_code == 404


def test_unauthorized_text_never_reaches_the_model_when_access_is_lost_before_analysis_runs(client, monkeypatch):
    t = make_team(client)
    judge = use_judge(monkeypatch)
    did, cid = t["shared"]["id"], t["coll"]["id"]
    e_id = next(m["user_id"] for m in client.get(f"{API}/collections/{cid}/members", headers=t["o"]).json() if m["role"] == "editor")
    r = client.post(f"{API}/conflicts/analyze", json={"document_id": did}, headers=t["e"])
    assert r.status_code == 202
    client.delete(f"{API}/collections/{cid}/members/{e_id}", headers=t["o"])
    # re-running the background job now (as if it had been delayed) must fail: authorization is re-checked at run time
    from app.db.session import SessionLocal
    from app.models.review import ConflictReport

    with SessionLocal() as db:
        rep = db.get(ConflictReport, r.json()["id"])
        rep.status, rep.completed_at = "running", None
        db.commit()
    conflict_service.run_report(r.json()["id"])
    with SessionLocal() as db:
        rep = db.get(ConflictReport, r.json()["id"])
        assert rep.status == "failed" and rep.error_code in ("NOT_FOUND", "FORBIDDEN")
    assert all("Bluebird" not in p for p in judge.prompts)
