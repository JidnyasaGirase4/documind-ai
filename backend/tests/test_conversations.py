from tests.conftest import API, PARENTAL, ask, new_conversation, new_user, ready_document


def test_create_list_rename_delete(client):
    h = new_user(client, "a@example.com")
    conv = new_conversation(client, h)
    assert conv["title"] == "New conversation" and conv["message_count"] == 0

    client.post(f"{API}/conversations", json={"title": "Budget questions"}, headers=h)
    listing = client.get(f"{API}/conversations", headers=h).json()
    assert listing["total"] == 2 and listing["pages"] == 1
    assert client.get(f"{API}/conversations", params={"search": "budget"}, headers=h).json()["total"] == 1

    r = client.patch(f"{API}/conversations/{conv['id']}", json={"title": "  Renamed  "}, headers=h)
    assert r.status_code == 200 and r.json()["title"] == "Renamed"
    assert client.patch(f"{API}/conversations/{conv['id']}", json={"title": "   "}, headers=h).status_code == 422

    assert client.delete(f"{API}/conversations/{conv['id']}", headers=h).status_code == 204
    assert client.get(f"{API}/conversations/{conv['id']}", headers=h).status_code == 404


def test_messages_persist_in_chronological_order_with_citations(client):
    h = new_user(client, "a@example.com")
    doc = ready_document(client, h, [PARENTAL])
    conv = new_conversation(client, h)
    first = ask(client, h, conv["id"], "paid parental leave primary caregivers weeks")
    assert first.status_code == 201
    ask(client, h, conv["id"], "secondary caregivers paid leave six weeks")

    detail = client.get(f"{API}/conversations/{conv['id']}", headers=h).json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant", "user", "assistant"]
    ids = [m["id"] for m in detail["messages"]]
    assert ids == sorted(ids)
    assert detail["messages"][1]["citations"][0]["document_id"] == doc["id"]  # citations survive a reload
    assert detail["message_count"] == 4
    assert all(m["created_at"].endswith("Z") for m in detail["messages"])

    row = [c for c in client.get(f"{API}/conversations", headers=h).json()["items"] if c["id"] == conv["id"]][0]
    assert row["message_count"] == 4


def test_title_is_taken_from_the_first_question_and_updated_at_moves(client):
    h = new_user(client, "a@example.com")
    ready_document(client, h, [PARENTAL])
    conv = new_conversation(client, h)
    ask(client, h, conv["id"], "How many weeks of paid parental leave do primary caregivers get?")
    after = client.get(f"{API}/conversations/{conv['id']}", headers=h).json()
    assert after["title"].startswith("How many weeks of paid parental leave")
    assert after["updated_at"] >= conv["updated_at"]


def test_conversations_are_isolated_between_users(client):
    a, b = new_user(client, "a@example.com"), new_user(client, "b@example.com")
    ready_document(client, a, [PARENTAL])
    conv = new_conversation(client, a)
    ask(client, a, conv["id"], "paid parental leave weeks")

    assert client.get(f"{API}/conversations", headers=b).json()["total"] == 0
    assert client.get(f"{API}/conversations/{conv['id']}", headers=b).status_code == 404
    assert client.patch(f"{API}/conversations/{conv['id']}", json={"title": "x"}, headers=b).status_code == 404
    assert client.delete(f"{API}/conversations/{conv['id']}", headers=b).status_code == 404
    assert ask(client, b, conv["id"], "paid parental leave weeks").status_code == 404
    assert len(client.get(f"{API}/conversations/{conv['id']}", headers=a).json()["messages"]) == 2


def test_message_validation(client):
    h = new_user(client, "a@example.com")
    conv = new_conversation(client, h)
    assert ask(client, h, conv["id"], "   ").status_code == 422
    assert ask(client, h, conv["id"], "x" * 4001).status_code == 422
