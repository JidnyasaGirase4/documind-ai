from tests.conftest import API, PARENTAL, WARRANTY, ask, new_conversation, new_user, ready_document


def _mk(client, h, path, body):
    r = client.post(f"{API}/{path}", json=body, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def test_collection_crud_and_counts(client):
    h = new_user(client, "a@example.com")
    doc = ready_document(client, h, [PARENTAL], "hr.pdf")
    c = _mk(client, h, "collections", {"name": "HR", "description": "People docs", "color": "burgundy", "icon": "users"})
    assert c["document_count"] == 0 and c["color"] == "burgundy"

    r = client.post(f"{API}/collections/{c['id']}/documents", json={"document_ids": [doc["id"]]}, headers=h)
    assert r.status_code == 200 and r.json()["document_count"] == 1
    # adding twice is idempotent
    assert client.post(f"{API}/collections/{c['id']}/documents", json={"document_ids": [doc["id"]]}, headers=h).json()["document_count"] == 1

    r = client.patch(f"{API}/collections/{c['id']}", json={"name": "Human Resources", "description": None}, headers=h)
    assert r.status_code == 200 and r.json()["name"] == "Human Resources" and r.json()["description"] is None

    listing = client.get(f"{API}/collections", params={"search": "human"}, headers=h).json()
    assert listing["total"] == 1 and listing["items"][0]["document_count"] == 1

    # deleting a collection keeps its documents
    assert client.delete(f"{API}/collections/{c['id']}", headers=h).status_code == 204
    assert client.get(f"{API}/documents/{doc['id']}", headers=h).status_code == 200
    assert client.get(f"{API}/documents/{doc['id']}", headers=h).json()["collection_ids"] == []
    assert client.get(f"{API}/collections/{c['id']}", headers=h).status_code == 404


def test_duplicate_names_and_validation(client):
    h = new_user(client, "a@example.com")
    _mk(client, h, "collections", {"name": "Research"})
    assert client.post(f"{API}/collections", json={"name": "research"}, headers=h).status_code == 409
    assert client.post(f"{API}/collections", json={"name": "   "}, headers=h).status_code == 422
    assert client.post(f"{API}/collections", json={"name": "X", "color": "neon"}, headers=h).status_code == 400
    _mk(client, h, "categories", {"name": "Finance"})
    assert client.post(f"{API}/categories", json={"name": "FINANCE"}, headers=h).status_code == 409
    _mk(client, h, "tags", {"name": "q3"})
    assert client.post(f"{API}/tags", json={"name": "Q3"}, headers=h).status_code == 409
    # another user may reuse the same names
    h2 = new_user(client, "b@example.com")
    _mk(client, h2, "collections", {"name": "Research"})
    _mk(client, h2, "tags", {"name": "q3"})


def test_move_documents_between_collections(client):
    h = new_user(client, "a@example.com")
    doc = ready_document(client, h, [PARENTAL])
    a = _mk(client, h, "collections", {"name": "A"})
    b = _mk(client, h, "collections", {"name": "B"})
    client.post(f"{API}/collections/{a['id']}/documents", json={"document_ids": [doc["id"]]}, headers=h)
    r = client.post(f"{API}/collections/{b['id']}/documents", json={"document_ids": [doc["id"]], "move_from_collection_id": a["id"]}, headers=h)
    assert r.json()["document_count"] == 1
    assert client.get(f"{API}/collections/{a['id']}", headers=h).json()["document_count"] == 0
    assert client.get(f"{API}/documents/{doc['id']}", headers=h).json()["collection_ids"] == [b["id"]]
    assert client.delete(f"{API}/collections/{b['id']}/documents/{doc['id']}", headers=h).status_code == 204
    assert client.delete(f"{API}/collections/{b['id']}/documents/{doc['id']}", headers=h).status_code == 404


def test_categories_tags_and_filters(client):
    h = new_user(client, "a@example.com")
    d1 = ready_document(client, h, [PARENTAL], "leave.pdf")
    d2 = ready_document(client, h, [WARRANTY], "warranty.pdf")
    cat = _mk(client, h, "categories", {"name": "HR Policies"})
    coll = _mk(client, h, "collections", {"name": "Policies"})

    r = client.patch(f"{API}/documents/{d1['id']}/metadata", json={"category_id": cat["id"], "tags": ["Leave", "leave", "2026"], "collection_ids": [coll["id"]]}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["category"]["name"] == "HR Policies" and sorted(t["name"] for t in body["tags"]) == ["2026", "Leave"]
    assert body["processing_status"] == "ready"  # metadata edits never reprocess

    leave_tag = next(t for t in body["tags"] if t["name"] == "Leave")

    def ids(**params):
        return [d["id"] for d in client.get(f"{API}/documents", params=params, headers=h).json()["items"]]

    assert ids(category_id=cat["id"]) == [d1["id"]]
    assert ids(category_id=0) == [d2["id"]]
    assert ids(tag_id=leave_tag["id"]) == [d1["id"]]
    assert ids(collection_id=coll["id"]) == [d1["id"]]
    assert ids(collection_id=coll["id"], status="failed") == []

    tags = {t["name"]: t for t in client.get(f"{API}/tags", headers=h).json()}
    assert tags["Leave"]["document_count"] == 1
    assert client.patch(f"{API}/tags/{leave_tag['id']}", json={"name": "2026"}, headers=h).status_code == 409
    assert client.patch(f"{API}/tags/{leave_tag['id']}", json={"name": "Parental"}, headers=h).json()["name"] == "Parental"

    cats = client.get(f"{API}/categories", headers=h).json()
    assert cats[0]["document_count"] == 1
    # deleting a category keeps the document
    assert client.delete(f"{API}/categories/{cat['id']}", headers=h).status_code == 204
    assert client.get(f"{API}/documents/{d1['id']}", headers=h).json()["category"] is None
    assert client.delete(f"{API}/tags/{leave_tag['id']}", headers=h).status_code == 204
    assert [t["name"] for t in client.get(f"{API}/documents/{d1['id']}", headers=h).json()["tags"]] == ["2026"]


def test_cannot_touch_another_users_knowledge_objects(client):
    a = new_user(client, "a@example.com")
    b = new_user(client, "b@example.com")
    doc_a = ready_document(client, a, [PARENTAL])
    coll_a = _mk(client, a, "collections", {"name": "Private"})
    cat_a = _mk(client, a, "categories", {"name": "Secret"})
    tag_a = _mk(client, a, "tags", {"name": "hidden"})
    doc_b = ready_document(client, b, [WARRANTY])
    coll_b = _mk(client, b, "collections", {"name": "Mine"})

    assert client.get(f"{API}/collections/{coll_a['id']}", headers=b).status_code == 404
    assert client.patch(f"{API}/collections/{coll_a['id']}", json={"name": "x"}, headers=b).status_code == 404
    assert client.delete(f"{API}/collections/{coll_a['id']}", headers=b).status_code == 404
    assert client.post(f"{API}/collections/{coll_a['id']}/documents", json={"document_ids": [doc_b["id"]]}, headers=b).status_code == 404
    # b cannot put a's document into b's collection, nor label it
    assert client.post(f"{API}/collections/{coll_b['id']}/documents", json={"document_ids": [doc_a["id"]]}, headers=b).status_code == 404
    assert client.patch(f"{API}/documents/{doc_a['id']}/metadata", json={"tags": ["x"]}, headers=b).status_code == 404
    # b cannot use a's category or collection on b's own document
    assert client.patch(f"{API}/documents/{doc_b['id']}/metadata", json={"category_id": cat_a["id"]}, headers=b).status_code == 404
    assert client.patch(f"{API}/documents/{doc_b['id']}/metadata", json={"collection_ids": [coll_a["id"]]}, headers=b).status_code == 404
    assert client.patch(f"{API}/categories/{cat_a['id']}", json={"name": "x"}, headers=b).status_code == 404
    assert client.delete(f"{API}/tags/{tag_a['id']}", headers=b).status_code == 404
    assert client.get(f"{API}/collections", headers=b).json()["total"] == 1
    assert client.get(f"{API}/tags", headers=b).json() == []
    # filtering by a's collection id is a 404 for b, same as a collection that does not exist
    assert client.get(f"{API}/documents", params={"collection_id": coll_a["id"]}, headers=b).status_code == 404
    assert client.get(f"{API}/collections").status_code == 401


def test_existing_chat_still_works_with_organized_documents(client):
    h = new_user(client, "a@example.com")
    doc = ready_document(client, h, [PARENTAL], "leave.pdf")
    coll = _mk(client, h, "collections", {"name": "HR"})
    client.post(f"{API}/collections/{coll['id']}/documents", json={"document_ids": [doc["id"]]}, headers=h)
    conv = new_conversation(client, h)
    r = ask(client, h, conv["id"], "How many weeks of parental leave?", [doc["id"]])
    assert r.status_code in (200, 201), r.text
