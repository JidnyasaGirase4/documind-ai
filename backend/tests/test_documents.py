from pathlib import Path

from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from app import worker
from app.services import job_service, vector_service
from app.services.embedding_service import EmbeddingError
from tests.conftest import API, PARENTAL, WARRANTY, make_pdf, new_user, ready_document, upload


def _stored_path(doc_id: int) -> Path:
    with engine.connect() as conn:
        return Path(conn.execute(text("SELECT storage_path FROM documents WHERE id=:i"), {"i": doc_id}).scalar_one())


def test_upload_processes_the_pdf_and_marks_it_ready(client):
    h = new_user(client, "a@example.com")
    r = upload(client, h, [PARENTAL, WARRANTY], "handbook.pdf")
    assert r.status_code == 202
    body = r.json()
    assert body["processing_status"] == "queued"  # the response is sent before background processing
    assert body["job"]["status"] == "queued"
    assert body["original_filename"] == "handbook.pdf"
    assert "storage_path" not in body  # internal paths never leave the server

    doc = client.get(f"{API}/documents/{body['id']}", headers=h).json()
    assert doc["processing_status"] == "ready"
    assert doc["total_pages"] == 2
    assert doc["processing_error"] is None

    with engine.connect() as conn:
        pages = [row[0] for row in conn.execute(text("SELECT page_number FROM document_chunks WHERE document_id=:i ORDER BY chunk_index"), {"i": body["id"]})]
        refs = conn.execute(text("SELECT COUNT(*) FROM document_chunks WHERE document_id=:i AND vector_reference IS NOT NULL"), {"i": body["id"]}).scalar()
    assert pages == [1, 2]
    assert refs == 2


def test_preview_streams_the_pdf_to_its_owner_only(client):
    a, b = new_user(client, "a@example.com"), new_user(client, "b@example.com")
    doc = ready_document(client, a, [PARENTAL])
    r = client.get(f"{API}/documents/{doc['id']}/preview", headers=a)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF-")
    assert client.get(f"{API}/documents/{doc['id']}/preview", headers=b).status_code == 404


def test_rejects_wrong_extension_content_type_and_fake_pdfs(client):
    h = new_user(client, "a@example.com")
    pdf = make_pdf([PARENTAL])
    assert upload(client, h, pdf, "notes.txt").status_code == 415
    assert upload(client, h, pdf, "doc.pdf", "text/plain").status_code == 415
    fake = upload(client, h, b"this is not a pdf at all", "doc.pdf")
    assert fake.status_code == 415 and fake.json()["error"]["code"] == "INVALID_PDF"
    broken = upload(client, h, b"%PDF-1.4 truncated garbage", "doc.pdf")
    assert broken.status_code == 415
    assert upload(client, h, b"", "doc.pdf").status_code in (400, 415)
    assert client.get(f"{API}/documents", headers=h).json()["total"] == 0
    assert not list((settings.upload_path).rglob("*.pdf")), "rejected files must not stay on disk"


def test_rejects_files_over_the_size_limit(client, monkeypatch):
    h = new_user(client, "a@example.com")
    monkeypatch.setattr(settings, "max_upload_size_mb", 0)
    r = upload(client, h, [PARENTAL])
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "FILE_TOO_LARGE"
    assert not list(settings.upload_path.rglob("*.pdf"))


def test_filename_is_sanitised_and_storage_name_is_generated(client):
    h = new_user(client, "a@example.com")
    r = upload(client, h, [PARENTAL], "../../etc/evil\\name.pdf")
    assert r.status_code == 202
    assert r.json()["original_filename"] == "name.pdf"
    path = _stored_path(r.json()["id"])
    assert path.parent.parent == settings.upload_path
    assert path.name.endswith(".pdf") and "evil" not in path.name


def test_scanned_pdf_without_text_fails_with_a_clear_message(client):
    h = new_user(client, "a@example.com")
    r = upload(client, h, ["", ""], "scan.pdf")
    doc = client.get(f"{API}/documents/{r.json()['id']}", headers=h).json()
    assert doc["processing_status"] == "failed"
    assert "OCR is not supported" in doc["processing_error"]


def test_retry_after_failure_reindexes_without_duplicates(client, monkeypatch):
    h = new_user(client, "a@example.com")

    class Broken:
        def embed(self, texts):
            raise EmbeddingError("model offline")

    original = job_service.get_embedder
    monkeypatch.setattr(job_service, "get_embedder", lambda: Broken())
    r = upload(client, h, [PARENTAL])
    doc_id = r.json()["id"]
    failed = client.get(f"{API}/documents/{doc_id}", headers=h).json()
    assert failed["processing_status"] == "failed"
    assert "embedding" in failed["processing_error"].lower()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM document_chunks WHERE document_id=:i"), {"i": doc_id}).scalar() == 0

    monkeypatch.setattr(job_service, "get_embedder", original)
    retry = client.post(f"{API}/documents/{doc_id}/retry", headers=h)
    assert retry.status_code == 202
    assert retry.json()["processing_status"] == "queued"
    worker.drain()
    ok = client.get(f"{API}/documents/{doc_id}", headers=h).json()
    assert ok["processing_status"] == "ready" and ok["processing_error"] is None
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM document_chunks WHERE document_id=:i"), {"i": doc_id}).scalar() == 1
        assert conn.execute(text("SELECT MAX(retry_count) FROM processing_jobs WHERE document_id=:i"), {"i": doc_id}).scalar() == 1
    assert len(vector_service._collection().get(where={"document_id": doc_id})["ids"]) == 1

    # Only failed documents can be retried.
    assert client.post(f"{API}/documents/{doc_id}/retry", headers=h).status_code == 409


def test_delete_removes_database_rows_vectors_and_file(client):
    h = new_user(client, "a@example.com")
    doc = ready_document(client, h, [PARENTAL, WARRANTY])
    path = _stored_path(doc["id"])
    assert path.is_file()
    assert vector_service._collection().get(where={"document_id": doc["id"]})["ids"]

    assert client.delete(f"{API}/documents/{doc['id']}", headers=h).status_code == 204
    assert client.get(f"{API}/documents/{doc['id']}", headers=h).status_code == 404
    assert not path.exists()
    assert vector_service._collection().get(where={"document_id": doc["id"]})["ids"] == []
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM document_chunks WHERE document_id=:i"), {"i": doc["id"]}).scalar() == 0
        assert conn.execute(text("SELECT COUNT(*) FROM processing_jobs WHERE document_id=:i"), {"i": doc["id"]}).scalar() == 0


def test_documents_are_isolated_between_users(client):
    a, b = new_user(client, "a@example.com"), new_user(client, "b@example.com")
    doc = ready_document(client, a, [PARENTAL])
    assert client.get(f"{API}/documents", headers=b).json()["total"] == 0
    assert client.get(f"{API}/documents/{doc['id']}", headers=b).status_code == 404
    assert client.delete(f"{API}/documents/{doc['id']}", headers=b).status_code == 404
    assert client.post(f"{API}/documents/{doc['id']}/retry", headers=b).status_code == 404
    # ...and the owner is unaffected.
    assert client.get(f"{API}/documents/{doc['id']}", headers=a).status_code == 200


def test_list_supports_search_status_sort_and_pagination(client):
    h = new_user(client, "a@example.com")
    for name in ["alpha.pdf", "bravo.pdf", "charlie.pdf"]:
        ready_document(client, h, [PARENTAL], name)
    upload(client, h, ["", ""], "scan.pdf")  # fails

    listing = client.get(f"{API}/documents", params={"page_size": 2, "sort_by": "name", "sort_order": "asc"}, headers=h).json()
    assert listing["total"] == 4 and listing["pages"] == 2 and listing["page"] == 1
    assert [d["original_filename"] for d in listing["items"]] == ["alpha.pdf", "bravo.pdf"]

    page2 = client.get(f"{API}/documents", params={"page": 2, "page_size": 2, "sort_by": "name", "sort_order": "asc"}, headers=h).json()
    assert [d["original_filename"] for d in page2["items"]] == ["charlie.pdf", "scan.pdf"]

    assert client.get(f"{API}/documents", params={"search": "brav"}, headers=h).json()["total"] == 1
    assert client.get(f"{API}/documents", params={"search": "%"}, headers=h).json()["total"] == 0  # wildcards are escaped
    failed = client.get(f"{API}/documents", params={"status": "failed"}, headers=h).json()
    assert [d["original_filename"] for d in failed["items"]] == ["scan.pdf"]
    assert client.get(f"{API}/documents", params={"status": "bogus"}, headers=h).status_code == 422
