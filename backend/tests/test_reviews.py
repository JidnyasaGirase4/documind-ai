"""Phase 6a: review schedules, derived status, completion and history, permissions."""

from datetime import date, datetime, timedelta

import pytest

from app import worker
from app.services import review_service
from tests.conftest import API, PARENTAL, WARRANTY, make_pdf, new_user, ready_document
from tests.test_sharing import make_team, post
from tests.test_versions import V1, V2, put_version, versions


def today():
    return review_service.today()


def iso(days):
    return (today() + timedelta(days=days)).isoformat()


def put(client, h, doc_id, **body):
    return client.put(f"{API}/documents/{doc_id}/review", json=body, headers=h)


def complete(client, h, doc_id, **body):
    return client.post(f"{API}/documents/{doc_id}/review/complete", json={"outcome": "approved", **body}, headers=h)


@pytest.fixture
def doc(client):
    h = new_user(client, "a@example.com")
    return h, ready_document(client, h, [V1], "policy.pdf")


# ----------------------------------------------------------- status rules
@pytest.mark.parametrize(
    "next_date,in_review,reviewed,expected",
    [
        (None, False, False, "not_scheduled"),
        (None, False, True, "reviewed"),
        (date(2026, 10, 1), False, False, "overdue"),
        (date(2026, 10, 9), False, False, "overdue"),  # yesterday
        (date(2026, 10, 10), False, False, "due"),  # today
        (date(2026, 10, 24), False, False, "due"),  # exactly at the end of the 14-day window
        (date(2026, 10, 25), False, False, "upcoming"),
        (date(2026, 10, 1), True, False, "in_review"),  # an explicit review in progress wins
    ],
)
def test_status_is_derived_from_dates(next_date, in_review, reviewed, expected):
    assert review_service.derive_status(next_date, in_review, datetime(2026, 1, 1) if reviewed else None, on=date(2026, 10, 10), soon_days=14) == expected


def test_not_scheduled_by_default(client, doc):
    h, d = doc
    r = client.get(f"{API}/documents/{d['id']}/review", headers=h).json()
    assert r["status"] == "not_scheduled" and r["next_review_date"] is None and r["version_number"] == 1 and r["title"] == "policy.pdf"
    assert client.get(f"{API}/reviews", headers=h).json()["total"] == 0  # no row is created by reading


def test_schedule_with_date_interval_and_notes(client, doc):
    h, d = doc
    r = put(client, h, d["id"], next_review_date=iso(40), interval_days=90, notes="  Check with HR  ")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "upcoming" and body["days_until_due"] == 40 and body["interval_days"] == 90 and body["notes"] == "Check with HR"
    assert put(client, h, d["id"], next_review_date=iso(5)).json()["status"] == "due"
    assert put(client, h, d["id"], next_review_date=today().isoformat()).json()["status"] == "due"
    # an interval alone starts counting from today on a document with no date yet
    h2 = new_user(client, "b@example.com")
    d2 = ready_document(client, h2, [WARRANTY], "w.pdf")
    r2 = put(client, h2, d2["id"], interval_days=30).json()
    assert r2["next_review_date"] == iso(30) and r2["status"] == "upcoming"


def test_a_past_date_is_never_stored_so_overdue_comes_from_time_passing(client, doc, monkeypatch):
    h, d = doc
    assert put(client, h, d["id"], next_review_date=iso(-1)).status_code == 422
    put(client, h, d["id"], next_review_date=iso(3))
    later = datetime.utcnow() + timedelta(days=10)  # ten days pass; nothing is updated in the database
    monkeypatch.setattr(review_service, "utcnow", lambda: later)
    r = client.get(f"{API}/documents/{d['id']}/review", headers=h).json()
    assert r["status"] == "overdue" and r["days_until_due"] == -7
    assert [i["document_id"] for i in client.get(f"{API}/reviews/overdue", headers=h).json()["items"]] == [d["id"]]
    assert client.get(f"{API}/reviews/summary", headers=h).json()["overdue"] == 1


def test_validation(client, doc):
    h, d = doc
    for bad in ({"interval_days": 0}, {"interval_days": -5}, {"interval_days": 4000}, {"interval_days": "soon"}, {"next_review_date": "2026-13-45"}, {"next_review_date": "not a date"}, {"notes": "x" * 2001}):
        assert put(client, h, d["id"], **bad).status_code == 422, bad
    assert put(client, h, d["id"], next_review_date=(today() + timedelta(days=365 * 11)).isoformat()).status_code == 422
    assert put(client, h, d["id"]).status_code == 400  # empty body
    assert complete(client, h, d["id"], outcome="great").status_code == 422
    assert complete(client, h, d["id"], next_review_date=iso(-3)).status_code == 422
    assert client.get(f"{API}/reviews", params={"status": "weird"}, headers=h).status_code == 422
    assert client.get(f"{API}/reviews", params={"page_size": 1000}, headers=h).status_code == 422


# ------------------------------------------------------ completion / history
def test_completing_a_review_records_history_and_schedules_the_next(client, doc):
    h, d = doc
    put(client, h, d["id"], next_review_date=iso(-0), interval_days=90)
    r = complete(client, h, d["id"], notes="Checked against law", outcome="approved")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "upcoming" and body["next_review_date"] == iso(90) and body["last_outcome"] == "approved"
    assert body["last_reviewed_by"]["name"] == "Test User" and body["last_reviewed_version_number"] == 1 and body["version_changed_since_review"] is False
    hist = client.get(f"{API}/documents/{d['id']}/review/history", headers=h).json()
    assert hist["total"] == 1
    e = hist["items"][0]
    assert e["outcome"] == "approved" and e["notes"] == "Checked against law" and e["version_number"] == 1 and e["reviewer"]["name"] == "Test User"
    assert e["previous_next_review_date"] == iso(0) and e["next_review_date"] == iso(90)
    # explicit date wins; no interval and no date -> "reviewed" with nothing scheduled
    assert complete(client, h, d["id"], next_review_date=iso(200)).json()["next_review_date"] == iso(200)
    put(client, h, d["id"], interval_days=None)
    r = client.delete(f"{API}/documents/{d['id']}/review", headers=h).json()
    assert r["status"] == "reviewed" and r["next_review_date"] is None  # reviewed before, nothing scheduled
    assert client.get(f"{API}/documents/{d['id']}/review/history", headers=h).json()["total"] == 2  # history survives unscheduling


def test_reviewer_cannot_be_impersonated(client):
    t = make_team(client)
    did = t["shared"]["id"]
    # extra fields such as reviewer_id are ignored: the history names the signed-in user
    owner_id = client.get(f"{API}/collections/{t['coll']['id']}/members", headers=t["o"]).json()[0]["user_id"]
    r = client.post(f"{API}/documents/{did}/review/complete", json={"outcome": "approved", "reviewer_id": owner_id, "reviewed_by": owner_id}, headers=t["e"])
    assert r.status_code == 200
    e = client.get(f"{API}/documents/{did}/review/history", headers=t["o"]).json()["items"][0]
    assert e["reviewer"]["id"] != owner_id


def test_in_review_flow_and_assignment(client):
    t = make_team(client)
    did = t["shared"]["id"]
    members = {m["email"]: m["user_id"] for m in client.get(f"{API}/collections/{t['coll']['id']}/members", headers=t["o"]).json()}
    assert put(client, t["o"], did, next_review_date=iso(10), assigned_reviewer_id=members["e@example.com"]).json()["assigned_reviewer"]["name"] == "Test User"
    assert put(client, t["o"], did, assigned_reviewer_id=members["v@example.com"]).status_code == 422  # a viewer cannot be assigned
    assert put(client, t["o"], did, assigned_reviewer_id=99999).status_code == 422
    assert post(client, t["e"], f"/documents/{did}/review/start").json()["status"] == "in_review"
    assert post(client, t["e"], f"/documents/{did}/review/start").status_code == 409
    assert client.get(f"{API}/reviews", params={"status": "in_review"}, headers=t["o"]).json()["total"] == 1
    r = complete(client, t["e"], did, outcome="changes_required", notes="Fix section 2")
    assert r.json()["status"] == "reviewed" and r.json()["last_outcome"] == "changes_required"  # in-review cleared; no interval and no new date were given, so nothing is scheduled


# ------------------------------------------------------------- versions
def test_reviews_record_the_version_and_survive_new_uploads(client, doc):
    h, d = doc
    put(client, h, d["id"], next_review_date=iso(20), interval_days=30)
    complete(client, h, d["id"])
    assert put_version(client, h, d["id"], [V2]).status_code == 202
    r = client.get(f"{API}/documents/{d['id']}/review", headers=h).json()
    assert r["version_number"] == 2 and r["last_reviewed_version_number"] == 1 and r["version_changed_since_review"] is True
    assert r["next_review_date"] == iso(30) and r["status"] == "upcoming"  # uploading did not move or reset the schedule
    complete(client, h, d["id"], notes="re-reviewed v2")
    hist = client.get(f"{API}/documents/{d['id']}/review/history", headers=h).json()["items"]
    assert [e["version_number"] for e in hist] == [2, 1]  # newest first; the old entry still says v1
    assert client.get(f"{API}/documents/{d['id']}", headers=h).json()["version_number"] == 2  # reviews never change the current version


# ----------------------------------------------------------- dashboard
def test_list_filters_summary_and_search(client):
    h = new_user(client, "a@example.com")
    ids = {}
    for name, days in (("overdue.pdf", 1), ("soon.pdf", 7), ("later.pdf", 60)):
        ids[name] = ready_document(client, h, [f"Unique content {name} {days * 31}"], name)["id"]
        put(client, h, ids[name], next_review_date=iso(days))
    ready_document(client, h, ["Never scheduled document text"], "none.pdf")
    from app.db.session import engine
    from sqlalchemy import text as sql

    with engine.begin() as c:  # make one overdue by moving the stored date back (as time passing would)
        c.execute(sql("UPDATE document_reviews SET next_review_date=:d WHERE document_id=:i"), {"d": today() - timedelta(days=2), "i": ids["overdue.pdf"]})
    s = client.get(f"{API}/reviews/summary", headers=h).json()
    assert (s["scheduled"], s["overdue"], s["due"], s["upcoming"], s["in_review"], s["completed_last_30_days"]) == (3, 1, 1, 1, 0, 0) and s["due_soon_days"] == 14
    titles = lambda **p: [i["title"] for i in client.get(f"{API}/reviews", params=p, headers=h).json()["items"]]  # noqa: E731
    assert titles() == ["overdue.pdf", "soon.pdf", "later.pdf"]
    assert titles(status="overdue") == ["overdue.pdf"] and titles(status="due") == ["soon.pdf"] and titles(status="upcoming") == ["later.pdf"]
    assert titles(search="LATER") == ["later.pdf"] and titles(sort="title") == ["later.pdf", "overdue.pdf", "soon.pdf"]
    assert titles(due_before=iso(10)) == ["overdue.pdf", "soon.pdf"] and titles(due_after=iso(10)) == ["later.pdf"]
    complete(client, h, ids["soon.pdf"])
    s = client.get(f"{API}/reviews/summary", headers=h).json()
    assert s["completed_last_30_days"] == 1 and s["recent"][0]["title"] == "soon.pdf" and s["recent"][0]["reviewer"]["name"] == "Test User"
    # pagination
    p = client.get(f"{API}/reviews", params={"page_size": 2, "page": 2}, headers=h).json()
    assert p["total"] == 3 and len(p["items"]) == 1 and p["pages"] == 2
    coll = post(client, h, "/collections", {"name": "C"}).json()
    post(client, h, f"/collections/{coll['id']}/documents", {"document_ids": [ids["later.pdf"]]})
    assert titles(collection_id=coll["id"]) == ["later.pdf"]
    assert client.get(f"{API}/reviews", params={"collection_id": 99999}, headers=h).status_code == 404


# ----------------------------------------------------------- permissions
def test_roles_and_isolation(client):
    t = make_team(client)
    did, pid = t["shared"]["id"], t["private"]["id"]
    put(client, t["o"], did, next_review_date=iso(5))
    put(client, t["o"], pid, next_review_date=iso(5))
    # viewers read only
    v = t["v"]
    assert client.get(f"{API}/documents/{did}/review", headers=v).json()["status"] == "due"
    assert client.get(f"{API}/documents/{did}/review/history", headers=v).status_code == 200
    assert put(client, v, did, next_review_date=iso(9)).status_code == 403
    assert complete(client, v, did).status_code == 403
    assert post(client, v, f"/documents/{did}/review/start").status_code == 403
    assert client.delete(f"{API}/documents/{did}/review", headers=v).status_code == 403
    # editors manage
    assert put(client, t["e"], did, next_review_date=iso(8)).status_code == 200 and complete(client, t["e"], did).status_code == 200
    # the private document and everything about it stays invisible to team members and outsiders
    for who in ("e", "v", "x"):
        assert client.get(f"{API}/documents/{pid}/review", headers=t[who]).status_code == 404
        assert client.get(f"{API}/documents/{pid}/review/history", headers=t[who]).status_code == 404
        assert put(client, t[who], pid, next_review_date=iso(9)).status_code == 404
    assert [i["title"] for i in client.get(f"{API}/reviews", headers=t["v"]).json()["items"]] == ["leave.pdf"]
    assert client.get(f"{API}/reviews", headers=t["x"]).json()["total"] == 0
    assert "secret.pdf" not in str(client.get(f"{API}/reviews/summary", headers=t["v"]).json())
    assert client.get(f"{API}/reviews/summary", headers=t["x"]).json()["scheduled"] == 0
    assert client.get(f"{API}/documents/{did}/review", headers=t["x"]).status_code == 404


def test_revoked_members_lose_review_data_at_once(client):
    t = make_team(client)
    did, cid = t["shared"]["id"], t["coll"]["id"]
    put(client, t["o"], did, next_review_date=iso(5))
    complete(client, t["o"], did, notes="private notes")
    assert client.get(f"{API}/reviews", headers=t["v"]).json()["total"] == 1
    v_id = next(m["user_id"] for m in client.get(f"{API}/collections/{cid}/members", headers=t["o"]).json() if m["role"] == "viewer")
    client.delete(f"{API}/collections/{cid}/members/{v_id}", headers=t["o"])
    assert client.get(f"{API}/reviews", headers=t["v"]).json()["total"] == 0
    assert client.get(f"{API}/documents/{did}/review", headers=t["v"]).status_code == 404
    assert client.get(f"{API}/documents/{did}/review/history", headers=t["v"]).status_code == 404
    s = client.get(f"{API}/reviews/summary", headers=t["v"]).json()
    assert s["scheduled"] == 0 and s["recent"] == []


def test_routes_require_authentication(client):
    for method, path in (("get", "/reviews"), ("get", "/reviews/summary"), ("get", "/reviews/overdue"), ("get", "/documents/1/review"), ("put", "/documents/1/review"), ("post", "/documents/1/review/complete")):
        assert getattr(client, method)(f"{API}{path}").status_code == 401
