from datetime import datetime, timezone

from tests.conftest import API, PARENTAL, ask, new_conversation, new_user, ready_document, upload


def test_stats_are_real_and_scoped_to_the_user(client):
    a, b = new_user(client, "a@example.com"), new_user(client, "b@example.com")
    ready_document(client, a, [PARENTAL])
    ready_document(client, a, [PARENTAL])
    upload(client, a, ["", ""], "scan.pdf")  # failed
    ready_document(client, b, [PARENTAL])

    assert client.get(f"{API}/dashboard/stats", headers=a).json() == {
        "total_documents": 3,
        "ready_documents": 2,
        "processing_documents": 0,
        "failed_documents": 1,
    }
    assert client.get(f"{API}/dashboard/stats", headers=b).json()["total_documents"] == 1


def test_stats_are_zero_for_a_new_user(client):
    h = new_user(client, "new@example.com")
    assert client.get(f"{API}/dashboard/stats", headers=h).json() == {
        "total_documents": 0,
        "ready_documents": 0,
        "processing_documents": 0,
        "failed_documents": 0,
    }
    assert client.get(f"{API}/dashboard/activity", headers=h).json() == []


def test_analytics_overview_counts_only_the_users_own_activity(client):
    a, b = new_user(client, "a@example.com"), new_user(client, "b@example.com")
    ready_document(client, a, [PARENTAL])
    ready_document(client, a, [PARENTAL])
    conv = new_conversation(client, a)
    ask(client, a, conv["id"], "paid parental leave weeks")
    ready_document(client, b, [PARENTAL])

    data = client.get(f"{API}/analytics/overview", headers=a).json()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    assert len(data["uploads_over_time"]) == 30 and len(data["question_activity"]) == 30
    assert data["uploads_over_time"][-1] == {"date": today, "count": 2}
    assert data["question_activity"][-1] == {"date": today, "count": 1}
    assert sum(p["count"] for p in data["uploads_over_time"]) == 2
    status = {s["status"]: s["count"] for s in data["status_distribution"]}
    assert status == {"uploaded": 0, "processing": 0, "ready": 2, "failed": 0}

    other = client.get(f"{API}/analytics/overview", headers=b).json()
    assert sum(p["count"] for p in other["question_activity"]) == 0


def test_activity_lists_recent_uploads_and_questions(client):
    h = new_user(client, "a@example.com")
    ready_document(client, h, [PARENTAL], "handbook.pdf")
    conv = new_conversation(client, h)
    ask(client, h, conv["id"], "paid parental leave weeks")
    items = client.get(f"{API}/dashboard/activity", headers=h).json()
    kinds = {i["type"] for i in items}
    assert kinds == {"upload", "question"}
    assert any("handbook.pdf" in i["title"] for i in items)
    assert all(i["timestamp"].endswith("Z") for i in items)


def test_profile_can_be_read_and_the_name_updated(client):
    h = new_user(client, "a@example.com")
    profile = client.get(f"{API}/settings/profile", headers=h).json()
    assert profile["email"] == "a@example.com" and "password_hash" not in profile
    r = client.patch(f"{API}/settings/profile", json={"name": "  New Name  "}, headers=h)
    assert r.status_code == 200 and r.json()["name"] == "New Name"
    assert client.get(f"{API}/auth/me", headers=h).json()["name"] == "New Name"


def test_profile_rejects_unsupported_fields_and_blank_names(client):
    h = new_user(client, "a@example.com")
    r = client.patch(f"{API}/settings/profile", json={"name": "Ok", "email": "evil@example.com"}, headers=h)
    assert r.status_code == 422
    assert client.get(f"{API}/settings/profile", headers=h).json()["email"] == "a@example.com"
    assert client.patch(f"{API}/settings/profile", json={"name": "   "}, headers=h).status_code == 422
