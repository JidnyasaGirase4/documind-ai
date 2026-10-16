"""Evaluation metrics are checked against hand-computed values; the runner is exercised end to end with the test
embedder and a scripted LLM (so the numbers here verify the scoring code, not model quality)."""

from sqlalchemy import text

from app.db.session import SessionLocal, engine
from app.services import eval_service, rag_service
from tests.conftest import API, new_user
from tests.test_rag import use_llm


def test_precision_and_recall_at_k_match_hand_calculation():
    rel = [("a.pdf", 1), ("b.pdf", 2)]
    ranked = [("a.pdf", 1), ("c.pdf", 1), ("b.pdf", 2), ("a.pdf", 1)]
    assert eval_service.precision_recall(ranked, rel, 3) == (round(2 / 3, 4), 1.0)
    assert eval_service.precision_recall(ranked, rel, 1) == (1.0, 0.5)
    assert eval_service.precision_recall([], rel, 5) == (0.0, 0.0)
    assert eval_service.precision_recall(ranked, [], 5) == (None, None)


def test_citation_correctness_and_faithfulness():
    rel = [("a.pdf", 1)]
    assert eval_service.citation_correctness([("a.pdf", 1), ("a.pdf", 2)], rel) == 0.5
    assert eval_service.citation_correctness([], rel) is None
    supported = eval_service.lexical_faithfulness("Employees accrue twenty annual leave days [S1]", ["Employees accrue twenty days of annual leave."])
    invented = eval_service.lexical_faithfulness("Employees receive unlimited sabbaticals every quarter", ["Employees accrue twenty days of annual leave."])
    assert supported == 1.0 and invented < 0.5


def test_full_run_stores_labelled_metrics_and_cleans_up(client, monkeypatch):
    def reply(messages):
        q = messages[-1]["content"]
        return "INSUFFICIENT_EVIDENCE" if ("pets" in q or "bonus" in q) else "According to the sources [S1]."

    use_llm(monkeypatch, reply)
    with SessionLocal() as db:
        run = eval_service.run_evaluation(db, k=3, answers=True)
        assert run.status == "completed", run.error
        m = run.metrics
    assert run.dataset_version == "1.0" and len(run.dataset_hash) == 64 and run.mode == "full"
    assert m["questions"] == 12 and m["answerable_questions"] == 10
    assert m["precision_at_k"]["kind"] == "measured" and 0 <= m["precision_at_k"]["value"] <= 1
    assert m["recall_at_k"]["value"] > 0  # the hashing embedder still matches shared words
    assert m["faithfulness"]["kind"] == "automated_estimate"
    assert m["correct_abstention_rate"]["value"] == 1.0 and m["correct_abstention_rate"]["n"] == 2
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM eval_results WHERE run_id=:r"), {"r": run.id}).scalar() == 12
        assert conn.execute(text("SELECT COUNT(*) FROM documents")).scalar() == 0  # corpus removed again
    assert rag_service.vector_service._collection().count() == 0


def test_retrieval_only_run_reports_no_answer_metrics(client):
    with SessionLocal() as db:
        run = eval_service.run_evaluation(db, k=3, answers=False)
    assert run.status == "completed" and run.mode == "retrieval_only" and run.judge == "none"
    assert "faithfulness" not in run.metrics and "precision_at_k" in run.metrics


def test_evaluation_endpoints_require_login_and_expose_runs(client):
    assert client.get(f"{API}/analytics/evaluations").status_code == 401
    h = new_user(client, "a@example.com")
    assert client.get(f"{API}/analytics/evaluations", headers=h).json() == {"latest": None, "history": []}
    with SessionLocal() as db:
        run = eval_service.run_evaluation(db, k=3, answers=False)
    body = client.get(f"{API}/analytics/evaluations", headers=h).json()
    assert body["latest"]["id"] == run.id and body["latest"]["metrics"]["precision_at_k"]["kind"] == "measured"
    detail = client.get(f"{API}/analytics/evaluations/{run.id}", headers=h).json()
    assert len(detail["results"]) == 12 and detail["results"][0]["question_id"] == "q01"
    assert client.get(f"{API}/analytics/evaluations/999999", headers=h).status_code == 404
