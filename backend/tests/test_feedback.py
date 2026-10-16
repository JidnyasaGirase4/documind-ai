"""Thumbs-up/down feedback, the query log behind the quality statistics, and their privacy."""

from sqlalchemy import text

from app.core.errors import AppError
from app.db.session import engine
from app.services import quality_service, rag_service
from tests.conftest import API, PARENTAL, ask, new_conversation, new_user, ready_document
from tests.test_rag import use_llm

Q = "How many weeks of paid parental leave do primary caregivers get?"


def _answered(client, monkeypatch, email="a@example.com"):
    h = new_user(client, email)
    ready_document(client, h, [PARENTAL], "handbook.pdf")
    conv = new_conversation(client, h)
    use_llm(monkeypatch, "Sixteen weeks [S1].")
    r = ask(client, h, conv["id"], Q).json()
    return h, conv, r["user_message"], r["assistant_message"]


def _fb(conv, msg):
    return f"{API}/conversations/{conv['id']}/messages/{msg['id']}/feedback"


def test_thumbs_up_and_down_are_stored_replaced_and_shown_on_the_message(client, monkeypatch):
    h, conv, _, answer = _answered(client, monkeypatch)
    r = client.put(_fb(conv, answer), json={"rating": "up"}, headers=h)
    assert r.status_code == 200 and r.json()["rating"] == "up"

    r = client.put(_fb(conv, answer), json={"rating": "down", "category": "wrong_source", "comment": "  Page was wrong  "}, headers=h)
    assert r.json()["rating"] == "down" and r.json()["category"] == "wrong_source" and r.json()["comment"] == "Page was wrong"
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM message_feedback")).scalar() == 1  # replaced, not duplicated

    detail = client.get(f"{API}/conversations/{conv['id']}", headers=h).json()
    by_role = {m["role"]: m for m in detail["messages"]}
    assert by_role["assistant"]["feedback"]["rating"] == "down" and by_role["assistant"]["feedback"]["comment"] == "Page was wrong"
    assert by_role["user"]["feedback"] is None

    assert client.delete(_fb(conv, answer), headers=h).status_code == 204
    assert client.get(f"{API}/conversations/{conv['id']}", headers=h).json()["messages"][1]["feedback"] is None
    assert client.delete(_fb(conv, answer), headers=h).status_code == 204  # idempotent


def test_a_reason_is_kept_only_for_thumbs_down(client, monkeypatch):
    h, conv, _, answer = _answered(client, monkeypatch)
    r = client.put(_fb(conv, answer), json={"rating": "up", "category": "inaccurate", "comment": "great"}, headers=h).json()
    assert r["category"] is None and r["comment"] == "great"


def test_feedback_input_is_validated(client, monkeypatch):
    h, conv, user_msg, answer = _answered(client, monkeypatch)
    assert client.put(_fb(conv, answer), json={"rating": "meh"}, headers=h).status_code == 422
    assert client.put(_fb(conv, answer), json={"rating": "down", "category": "<script>"}, headers=h).status_code == 422
    assert client.put(_fb(conv, answer), json={"rating": "down", "comment": "x" * 2001}, headers=h).status_code == 422
    assert client.put(_fb(conv, user_msg), json={"rating": "up"}, headers=h).status_code == 400  # not an answer
    assert client.put(f"{API}/conversations/{conv['id']}/messages/99999/feedback", json={"rating": "up"}, headers=h).status_code == 404


def test_feedback_is_private_to_the_conversation_owner(client, monkeypatch):
    a, conv, _, answer = _answered(client, monkeypatch)
    b = new_user(client, "b@example.com")
    assert client.put(_fb(conv, answer), json={"rating": "down", "comment": "spam"}, headers=b).status_code == 404
    assert client.delete(_fb(conv, answer), headers=b).status_code == 404
    assert client.put(_fb(conv, answer), json={"rating": "up"}).status_code == 401
    client.put(_fb(conv, answer), json={"rating": "down", "comment": "private note"}, headers=a)
    assert "private note" not in str(client.get(f"{API}/analytics/feedback", headers=b).json())
    assert client.get(f"{API}/analytics/feedback", headers=b).json()["total"] == 0
    assert client.get(f"{API}/analytics/feedback", headers=a).json()["total"] == 1


def test_feedback_statistics_count_what_was_stored(client, monkeypatch):
    h, conv, _, first = _answered(client, monkeypatch)
    second = ask(client, h, conv["id"], Q).json()["assistant_message"]
    third = ask(client, h, conv["id"], Q).json()["assistant_message"]
    client.put(_fb(conv, first), json={"rating": "up"}, headers=h)
    client.put(_fb(conv, second), json={"rating": "down", "category": "inaccurate", "comment": "wrong number"}, headers=h)
    client.put(_fb(conv, third), json={"rating": "down", "category": "inaccurate"}, headers=h)
    s = client.get(f"{API}/analytics/feedback", headers=h).json()
    assert (s["total"], s["up"], s["down"]) == (3, 1, 2)
    assert s["satisfaction"] == round(1 / 3, 4)
    assert s["down_categories"] == [{"category": "inaccurate", "count": 2}]
    assert [c["comment"] for c in s["recent_comments"]] == ["wrong number"]
    assert sum(d["up"] + d["down"] for d in s["by_day"]) == 3 and len(s["by_day"]) == 30


def test_every_question_is_logged_with_latency_and_outcome(client, monkeypatch):
    h, conv, _, _ = _answered(client, monkeypatch)
    use_llm(monkeypatch, "INSUFFICIENT_EVIDENCE")
    ask(client, h, conv["id"], "What is the airspeed of a swallow?")

    class Boom:
        @staticmethod
        def generate(*_a, **_k):
            raise AppError(503, "LLM_TIMEOUT", "The AI provider took too long to respond.")

    monkeypatch.setattr(rag_service, "get_llm", lambda: Boom())
    assert ask(client, h, conv["id"], Q).status_code == 503

    s = client.get(f"{API}/analytics/queries", headers=h).json()
    assert (s["total_questions"], s["answered"], s["insufficient_evidence"], s["errors"]) == (3, 1, 1, 1)
    assert s["failure_rate"] == round(1 / 3, 4) and s["insufficient_rate"] == round(1 / 3, 4)
    assert s["latency_ms"]["count"] == 2 and s["latency_ms"]["p50"] is not None and s["latency_ms"]["p95"] >= s["latency_ms"]["p50"]
    cats = {c["category"]: c["count"] for c in s["failure_categories"]}
    assert cats == {"insufficient_evidence": 1, "llm_unavailable": 1}
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT outcome, error_code, citation_count FROM query_logs ORDER BY id")).all()
    assert [r[0] for r in rows] == ["answered", "insufficient_evidence", "error"]
    assert rows[2][1] == "LLM_TIMEOUT" and rows[0][2] == 1


def test_query_statistics_are_per_user_and_empty_users_get_nulls(client, monkeypatch):
    _answered(client, monkeypatch)
    other = new_user(client, "b@example.com")
    s = client.get(f"{API}/analytics/queries", headers=other).json()
    assert s["total_questions"] == 0 and s["failure_rate"] is None and s["latency_ms"]["p50"] is None


def test_percentile_uses_the_nearest_rank_method():
    assert quality_service._percentile([10, 20, 30, 40], 0.5) == 20
    assert quality_service._percentile([10, 20, 30, 40], 0.95) == 40
    assert quality_service._percentile([], 0.5) is None
