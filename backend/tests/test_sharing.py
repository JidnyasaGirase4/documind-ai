"""Phase 4: collection sharing, Viewer/Editor roles and backend authorization on every document path
(lists, metadata, PDF, page images, citations, RAG retrieval, processing jobs)."""

from app.services import job_service
from tests.conftest import API, PARENTAL, WARRANTY, ask, new_conversation, new_user, ready_document, upload
from tests.test_jobs import FlakyEmbedder
from tests.test_rag import use_llm

SECRET = "The confidential merger codename is Bluebird and the budget is nine million."


def post(client, h, path, body=None):
    return client.post(f"{API}{path}", json=body or {}, headers=h)


def make_team(client):
    """owner O, editor E, viewer V and outsider X. O shares a collection (with PARENTAL) and keeps a private SECRET doc."""
    o, e, v, x = (new_user(client, f"{n}@example.com") for n in "oevx")
    shared_doc = ready_document(client, o, [PARENTAL], "leave.pdf")
    private_doc = ready_document(client, o, [SECRET], "secret.pdf")
    coll = post(client, o, "/collections", {"name": "Team"}).json()
    assert post(client, o, f"/collections/{coll['id']}/documents", {"document_ids": [shared_doc["id"]]}).status_code == 200
    assert post(client, o, f"/collections/{coll['id']}/members", {"email": "e@example.com", "role": "editor"}).status_code == 201
    assert post(client, o, f"/collections/{coll['id']}/members", {"email": "v@example.com", "role": "viewer"}).status_code == 201
    return dict(o=o, e=e, v=v, x=x, coll=coll, shared=shared_doc, private=private_doc)


def ids(client, h, **params):
    return [d["id"] for d in client.get(f"{API}/documents", params=params, headers=h).json()["items"]]


# --------------------------------------------------------------- membership
def test_owner_manages_members(client):
    t = make_team(client)
    cid = t["coll"]["id"]
    members = client.get(f"{API}/collections/{cid}/members", headers=t["o"]).json()
    assert [(m["email"], m["role"]) for m in members] == [("o@example.com", "owner"), ("e@example.com", "editor"), ("v@example.com", "viewer")]

    assert post(client, t["o"], f"/collections/{cid}/members", {"email": "E@Example.com", "role": "viewer"}).status_code == 409  # duplicate, case-insensitive
    assert post(client, t["o"], f"/collections/{cid}/members", {"email": "o@example.com"}).status_code == 400  # the owner
    assert post(client, t["o"], f"/collections/{cid}/members", {"email": "nobody@example.com"}).status_code == 404
    assert post(client, t["o"], f"/collections/{cid}/members", {"email": "x@example.com", "role": "owner"}).status_code == 422
    assert post(client, t["o"], f"/collections/{cid}/members", {"email": "not-an-email"}).status_code == 422

    e_id = next(m["user_id"] for m in members if m["role"] == "editor")
    r = client.patch(f"{API}/collections/{cid}/members/{e_id}", json={"role": "viewer"}, headers=t["o"])
    assert r.status_code == 200 and r.json()["role"] == "viewer"
    assert client.delete(f"{API}/collections/{cid}/members/{e_id}", headers=t["o"]).status_code == 204
    assert client.delete(f"{API}/collections/{cid}/members/{e_id}", headers=t["o"]).status_code == 404
    assert client.get(f"{API}/collections/{cid}", headers=t["e"]).status_code == 404  # access ended at once


def test_only_the_owner_manages_members_and_settings(client):
    t = make_team(client)
    cid = t["coll"]["id"]
    members = client.get(f"{API}/collections/{cid}/members", headers=t["v"]).json()  # members can see who is in the team
    v_id = next(m["user_id"] for m in members if m["role"] == "viewer")
    o_id = next(m["user_id"] for m in members if m["role"] == "owner")
    for who in ("e", "v"):
        h = t[who]
        assert post(client, h, f"/collections/{cid}/members", {"email": "x@example.com"}).status_code == 403
        assert client.patch(f"{API}/collections/{cid}/members/{v_id}", json={"role": "editor"}, headers=h).status_code == 403
        assert client.delete(f"{API}/collections/{cid}/members/{o_id}", headers=h).status_code == 403
        assert client.patch(f"{API}/collections/{cid}", json={"name": "Hijacked"}, headers=h).status_code == 403
        assert client.delete(f"{API}/collections/{cid}", headers=h).status_code == 403
    # an outsider cannot even tell the collection exists
    x = t["x"]
    assert client.get(f"{API}/collections/{cid}", headers=x).status_code == 404
    assert client.get(f"{API}/collections/{cid}/members", headers=x).status_code == 404
    assert post(client, x, f"/collections/{cid}/members", {"email": "x@example.com"}).status_code == 404
    assert client.delete(f"{API}/collections/{cid}/members/{v_id}", headers=x).status_code == 404
    assert client.get(f"{API}/collections/{cid}", headers=t["o"]).json()["name"] == "Team"


def test_member_can_leave_a_collection(client):
    t = make_team(client)
    cid = t["coll"]["id"]
    v_id = next(m["user_id"] for m in client.get(f"{API}/collections/{cid}/members", headers=t["o"]).json() if m["role"] == "viewer")
    assert client.delete(f"{API}/collections/{cid}/members/{v_id}", headers=t["v"]).status_code == 204
    assert client.get(f"{API}/collections/{cid}", headers=t["v"]).status_code == 404


def test_collection_listing_shows_role_and_sharing(client):
    t = make_team(client)
    mine = client.get(f"{API}/collections", headers=t["o"]).json()["items"][0]
    assert mine["role"] == "owner" and mine["is_shared"] is True and mine["member_count"] == 2
    seen = client.get(f"{API}/collections", headers=t["v"]).json()["items"]
    assert [(c["name"], c["role"], c["owner_name"]) for c in seen] == [("Team", "viewer", "Test User")]
    assert client.get(f"{API}/collections", params={"scope": "owned"}, headers=t["v"]).json()["total"] == 0
    assert client.get(f"{API}/collections", params={"scope": "shared"}, headers=t["v"]).json()["total"] == 1
    assert client.get(f"{API}/collections", headers=t["x"]).json()["total"] == 0


# ------------------------------------------------------- documents and roles
def test_shared_documents_are_visible_but_private_ones_are_not(client):
    t = make_team(client)
    for who in ("e", "v"):
        h = t[who]
        assert ids(client, h) == []  # "My documents" stays my own uploads
        assert ids(client, h, scope="shared") == [t["shared"]["id"]]
        assert ids(client, h, scope="all") == [t["shared"]["id"]]
        assert ids(client, h, collection_id=t["coll"]["id"]) == [t["shared"]["id"]]
        got = client.get(f"{API}/documents/{t['shared']['id']}", headers=h).json()
        assert got["is_owner"] is False and got["role"] == {"e": "editor", "v": "viewer"}[who]
        # the private document of the same owner is not discoverable
        assert client.get(f"{API}/documents/{t['private']['id']}", headers=h).status_code == 404
        assert client.get(f"{API}/documents/{t['private']['id']}/preview", headers=h).status_code == 404
    assert ids(client, t["x"], scope="all") == []
    assert sorted(ids(client, t["o"])) == sorted([t["shared"]["id"], t["private"]["id"]])


def test_document_access_does_not_spread_to_other_collections(client):
    t = make_team(client)
    # O puts the private document in a collection nobody else belongs to
    solo = post(client, t["o"], "/collections", {"name": "Solo"}).json()
    post(client, t["o"], f"/collections/{solo['id']}/documents", {"document_ids": [t["private"]["id"]]})
    assert client.get(f"{API}/collections/{solo['id']}", headers=t["v"]).status_code == 404
    assert client.get(f"{API}/documents/{t['private']['id']}", headers=t["v"]).status_code == 404
    # collection_ids on a shared document only mention collections the viewer can see
    post(client, t["o"], f"/collections/{solo['id']}/documents", {"document_ids": [t["shared"]["id"]]})
    assert client.get(f"{API}/documents/{t['shared']['id']}", headers=t["v"]).json()["collection_ids"] == [t["coll"]["id"]]


def test_viewer_is_read_only(client):
    t = make_team(client)
    v, cid, did = t["v"], t["coll"]["id"], t["shared"]["id"]
    own = ready_document(client, v, [WARRANTY], "mine.pdf")
    assert client.patch(f"{API}/documents/{did}/metadata", json={"tags": ["x"]}, headers=v).status_code == 403
    assert client.delete(f"{API}/documents/{did}", headers=v).status_code == 403
    assert post(client, v, f"/documents/{did}/retry").status_code == 403
    assert post(client, v, f"/collections/{cid}/documents", {"document_ids": [own["id"]]}).status_code == 403
    assert client.delete(f"{API}/collections/{cid}/documents/{did}", headers=v).status_code == 403
    assert client.get(f"{API}/documents/{did}/preview", headers=v).status_code == 200
    assert client.get(f"{API}/documents/{did}/pages/1/image", headers=v).status_code == 200
    assert client.get(f"{API}/documents/{did}", headers=t["o"]).json()["tags"] == []  # nothing changed


def test_editor_can_contribute_but_not_administer(client):
    t = make_team(client)
    e, o, cid, did = t["e"], t["o"], t["coll"]["id"], t["shared"]["id"]
    own = ready_document(client, e, [WARRANTY], "warranty.pdf")
    # adds their own document; cannot add someone else's private document
    assert post(client, e, f"/collections/{cid}/documents", {"document_ids": [own["id"]]}).json()["document_count"] == 2
    assert post(client, e, f"/collections/{cid}/documents", {"document_ids": [t["private"]["id"]]}).status_code == 404
    assert sorted(ids(client, t["v"], scope="all")) == sorted([did, own["id"]])
    # labels the owner's document (in the owner's namespace) but cannot move it between collections
    r = client.patch(f"{API}/documents/{did}/metadata", json={"tags": ["hr"]}, headers=e)
    assert r.status_code == 200 and [x["name"] for x in r.json()["tags"]] == ["hr"]
    assert [x["name"] for x in client.get(f"{API}/tags", headers=o).json()] == ["hr"]
    assert client.patch(f"{API}/documents/{did}/metadata", json={"collection_ids": []}, headers=e).status_code == 403
    # may remove a document from the shared collection, which then stops being shared
    assert client.delete(f"{API}/collections/{cid}/documents/{did}", headers=e).status_code == 204
    assert client.get(f"{API}/documents/{did}", headers=t["v"]).status_code == 404
    assert client.get(f"{API}/documents/{did}", headers=o).status_code == 200  # the file still belongs to its owner
    assert client.delete(f"{API}/documents/{own['id']}", headers=o).status_code == 403  # O can read E's file here but never owned it


def test_pdf_page_and_citation_access_follow_membership(client, monkeypatch):
    t = make_team(client)
    did, cid = t["shared"]["id"], t["coll"]["id"]
    use_llm(monkeypatch, "Primary caregivers get sixteen weeks of paid leave [S1].")
    conv = new_conversation(client, t["v"])
    cite = ask(client, t["v"], conv["id"], "How many weeks of paid parental leave do primary caregivers get?").json()["assistant_message"]["citations"][0]
    assert cite["document_id"] == did
    url = f"{API}/documents/{did}"
    assert client.get(f"{url}/highlights", params={"chunk_id": cite["chunk_id"]}, headers=t["v"]).status_code == 200
    assert client.get(f"{url}/highlights", params={"chunk_id": cite["chunk_id"]}, headers=t["x"]).status_code == 404

    v_id = next(m["user_id"] for m in client.get(f"{API}/collections/{cid}/members", headers=t["o"]).json() if m["role"] == "viewer")
    client.delete(f"{API}/collections/{cid}/members/{v_id}", headers=t["o"])
    for path in (f"{url}", f"{url}/preview", f"{url}/pages/1/image"):
        assert client.get(path, headers=t["v"]).status_code == 404, path
    assert client.get(f"{url}/highlights", params={"chunk_id": cite["chunk_id"]}, headers=t["v"]).status_code == 404
    # the old conversation keeps its answer but no longer shows the revoked document's name or excerpt
    old = client.get(f"{API}/conversations/{conv['id']}", headers=t["v"]).json()["messages"][-1]["citations"][0]
    assert old["excerpt"] is None and old["chunk_id"] is None and "leave.pdf" not in str(old)


# ----------------------------------------------------------------------- RAG
def test_rag_only_retrieves_authorized_documents(client, monkeypatch):
    t = make_team(client)
    fake = use_llm(monkeypatch, "Primary caregivers get sixteen weeks of paid leave [S1].")
    conv = new_conversation(client, t["v"])
    r = ask(client, t["v"], conv["id"], "How many weeks of paid parental leave?")  # no document_ids: all authorized ones
    assert r.status_code == 201 and r.json()["assistant_message"]["citations"][0]["document_id"] == t["shared"]["id"]
    # the private document is not selectable, and its text never reaches the model
    assert ask(client, t["v"], conv["id"], "What is the merger codename?", [t["private"]["id"]]).status_code == 404
    ask(client, t["v"], conv["id"], "What is the confidential merger codename Bluebird budget?")
    assert not any("Bluebird" in str(call) for call in fake.calls)
    # outsider has nothing to search at all
    cx = new_conversation(client, t["x"])
    assert ask(client, t["x"], cx["id"], "parental leave?").status_code == 400
    assert ask(client, t["x"], cx["id"], "parental leave?", [t["shared"]["id"]]).status_code == 404


def test_revoked_member_immediately_loses_rag_access(client, monkeypatch):
    t = make_team(client)
    use_llm(monkeypatch, "Primary caregivers get sixteen weeks of paid leave [S1].")
    conv = new_conversation(client, t["e"])
    assert ask(client, t["e"], conv["id"], "How many weeks of paid parental leave?", [t["shared"]["id"]]).status_code == 201
    e_id = next(m["user_id"] for m in client.get(f"{API}/collections/{t['coll']['id']}/members", headers=t["o"]).json() if m["role"] == "editor")
    client.delete(f"{API}/collections/{t['coll']['id']}/members/{e_id}", headers=t["o"])
    assert ask(client, t["e"], conv["id"], "How many weeks of paid parental leave?", [t["shared"]["id"]]).status_code == 404
    assert ask(client, t["e"], conv["id"], "How many weeks of paid parental leave?").status_code == 400


def test_chunks_of_a_document_removed_from_the_collection_are_not_retrieved(client, monkeypatch):
    t = make_team(client)
    use_llm(monkeypatch, "Primary caregivers get sixteen weeks of paid leave [S1].")
    client.delete(f"{API}/collections/{t['coll']['id']}/documents/{t['shared']['id']}", headers=t["o"])
    conv = new_conversation(client, t["v"])
    assert ask(client, t["v"], conv["id"], "How many weeks of paid parental leave?").status_code == 400


# ---------------------------------------------------------------------- jobs
def test_job_status_and_retry_follow_roles(client, monkeypatch):
    o, e, v, x = (new_user(client, f"{n}@example.com") for n in "oevx")
    monkeypatch.setattr(job_service, "get_embedder", lambda: FlakyEmbedder(None, failures=99))
    doc_id = upload(client, o, [PARENTAL]).json()["id"]
    assert client.get(f"{API}/documents/{doc_id}", headers=o).json()["processing_status"] == "failed"
    monkeypatch.undo()
    coll = post(client, o, "/collections", {"name": "T"}).json()
    post(client, o, f"/collections/{coll['id']}/documents", {"document_ids": [doc_id]})
    post(client, o, f"/collections/{coll['id']}/members", {"email": "e@example.com", "role": "editor"})
    post(client, o, f"/collections/{coll['id']}/members", {"email": "v@example.com", "role": "viewer"})
    job_id = client.get(f"{API}/documents/{doc_id}", headers=o).json()["job"]["id"]

    for h in (o, e, v):
        assert client.get(f"{API}/jobs/{job_id}", headers=h).status_code == 200
        assert [j["id"] for j in client.get(f"{API}/jobs", headers=h).json()["items"]] == [job_id]
    assert client.get(f"{API}/jobs/{job_id}", headers=x).status_code == 404
    assert client.get(f"{API}/jobs", headers=x).json()["items"] == []
    assert post(client, v, f"/jobs/{job_id}/retry").status_code == 403
    assert post(client, v, f"/documents/{doc_id}/retry").status_code == 403
    assert post(client, x, f"/jobs/{job_id}/retry").status_code == 404
    assert post(client, e, f"/jobs/{job_id}/retry").status_code == 202  # an editor may restart processing


# ---------------------------------------------------------------- regression
def test_private_documents_and_upload_still_work_without_any_sharing(client, monkeypatch):
    a, b = new_user(client, "a@example.com"), new_user(client, "b@example.com")
    doc = ready_document(client, a, [PARENTAL])
    assert client.get(f"{API}/documents/{doc['id']}", headers=b).status_code == 404
    assert ids(client, b, scope="all") == []
    assert client.get(f"{API}/documents/{doc['id']}", headers=a).json()["is_owner"] is True
    use_llm(monkeypatch, "Primary caregivers get sixteen weeks of paid leave [S1].")
    conv = new_conversation(client, a)
    assert ask(client, a, conv["id"], "How many weeks of paid parental leave?").status_code == 201
