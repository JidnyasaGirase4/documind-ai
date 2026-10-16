"""Background processing: queue states, real progress, automatic and manual retries, duplicate prevention, recovery
from lost workers, corrupted files and job-level authorization."""

from datetime import timedelta
from pathlib import Path

from sqlalchemy import text

from app import worker
from app.db.session import SessionLocal, engine
from app.models.document import ProcessingJob
from app.services import job_service, vector_service
from app.services.embedding_service import EmbeddingError
from app.utils.time import utcnow
from tests.conftest import API, PARENTAL, WARRANTY, make_pdf, new_user, ready_document, upload


def _job(doc_id: int) -> dict:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM processing_jobs WHERE document_id=:i ORDER BY id DESC LIMIT 1"), {"i": doc_id}).mappings().one()
    return dict(row)


def _chunks(doc_id: int) -> int:
    with engine.connect() as conn:
        return conn.execute(text("SELECT COUNT(*) FROM document_chunks WHERE document_id=:i"), {"i": doc_id}).scalar()


def _get(client, h, doc_id):
    return client.get(f"{API}/documents/{doc_id}", headers=h).json()


class FlakyEmbedder:
    """Fails the first `failures` calls, then behaves like the real (hashing) embedder."""

    def __init__(self, real, failures):
        self.real, self.failures, self.calls = real, failures, 0

    def embed(self, texts):
        self.calls += 1
        if self.calls <= self.failures:
            raise EmbeddingError("model offline")
        return self.real.embed(texts)


def test_upload_returns_immediately_and_the_job_waits_in_the_queue(client):
    h = new_user(client, "a@example.com")
    r = upload(client, h, [PARENTAL], run_worker=False)
    assert r.status_code == 202
    body = r.json()
    assert body["processing_status"] == "queued"
    assert body["job"]["status"] == "queued" and body["job"]["progress"] == 0 and body["job"]["attempts"] == 0
    assert _chunks(body["id"]) == 0  # nothing has been processed yet

    assert worker.drain() == 1
    done = _get(client, h, body["id"])
    assert done["processing_status"] == "ready"
    assert done["job"]["status"] == "completed" and done["job"]["progress"] == 100 and done["job"]["attempts"] == 1


def test_progress_is_reported_per_stage_while_the_job_runs(client, monkeypatch):
    h = new_user(client, "a@example.com")
    seen = []
    real = job_service.get_embedder()

    class Watching:
        def embed(self, texts):
            seen.append(_job(doc_id)["progress"])
            seen.append(_job(doc_id)["stage"])
            return real.embed(texts)

    monkeypatch.setattr(job_service, "get_embedder", lambda: Watching())
    doc_id = upload(client, h, [PARENTAL, WARRANTY], run_worker=False).json()["id"]
    worker.drain()
    progress, stage = seen[0], seen[1]
    assert stage == "embedding" or stage == "chunking"
    assert 25 <= progress < 100  # past extraction, not yet finished: a real intermediate value
    assert _job(doc_id)["progress"] == 100


def test_transient_failure_is_retried_automatically_without_duplicates(client, monkeypatch):
    h = new_user(client, "a@example.com")
    flaky = FlakyEmbedder(job_service.get_embedder(), failures=1)
    monkeypatch.setattr(job_service, "get_embedder", lambda: flaky)
    doc_id = upload(client, h, [PARENTAL, WARRANTY]).json()["id"]  # drain keeps going: the retry is due immediately in tests
    doc = _get(client, h, doc_id)
    assert doc["processing_status"] == "ready"
    assert doc["job"]["attempts"] == 2 and doc["job"]["status"] == "completed"
    assert _chunks(doc_id) == 2
    assert len(vector_service._collection().get(where={"document_id": doc_id})["ids"]) == 2


def test_backoff_delays_the_next_attempt(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "job_retry_base_seconds", 3600.0)
    h = new_user(client, "a@example.com")
    monkeypatch.setattr(job_service, "get_embedder", lambda: FlakyEmbedder(None, failures=99))
    doc_id = upload(client, h, [PARENTAL]).json()["id"]
    doc = _get(client, h, doc_id)
    assert doc["processing_status"] == "queued"  # waiting for its backoff, not failed yet
    assert doc["job"]["status"] == "queued" and doc["job"]["attempts"] == 1
    assert doc["job"]["next_run_at"] is not None and "Retrying automatically" in doc["job"]["error_message"]
    assert worker.drain() == 0  # not due yet


def test_job_fails_after_the_last_attempt_and_can_be_retried_manually(client, monkeypatch):
    h = new_user(client, "a@example.com")
    monkeypatch.setattr(job_service, "get_embedder", lambda: FlakyEmbedder(None, failures=99))
    doc_id = upload(client, h, [PARENTAL]).json()["id"]
    doc = _get(client, h, doc_id)
    assert doc["processing_status"] == "failed"
    assert doc["job"]["status"] == "failed" and doc["job"]["attempts"] == doc["job"]["max_attempts"] == 3
    assert "embedding model is unavailable" in doc["processing_error"]
    assert "model offline" not in str(doc)  # internal detail is not exposed
    assert _chunks(doc_id) == 0

    monkeypatch.undo()
    r = client.post(f"{API}/documents/{doc_id}/retry", headers=h)
    assert r.status_code == 202 and r.json()["processing_status"] == "queued" and r.json()["job"]["retry_count"] == 1
    worker.drain()
    assert _get(client, h, doc_id)["processing_status"] == "ready"
    assert _chunks(doc_id) == 1


def test_corrupted_or_empty_pdfs_fail_at_once_without_pointless_retries(client):
    h = new_user(client, "a@example.com")
    scan = upload(client, h, [""]).json()["id"]  # a valid PDF whose page has no text
    job = _get(client, h, scan)["job"]
    assert job["status"] == "failed" and job["attempts"] == 1 and job["error_code"] == "NO_EXTRACTABLE_TEXT"

    good = upload(client, h, [PARENTAL], run_worker=False).json()["id"]
    with engine.connect() as conn:
        path = Path(conn.execute(text("SELECT storage_path FROM documents WHERE id=:i"), {"i": good}).scalar_one())
    path.write_bytes(b"%PDF-1.4\nthis was corrupted after the upload check")
    worker.drain()
    doc = _get(client, h, good)
    assert doc["processing_status"] == "failed" and doc["job"]["error_code"] == "INVALID_PDF" and doc["job"]["attempts"] == 1
    assert _chunks(good) == 0

    path.unlink()
    assert client.post(f"{API}/documents/{good}/retry", headers=h).status_code == 400  # file is gone: explained, not queued


def test_a_document_cannot_have_two_active_jobs(client):
    h = new_user(client, "a@example.com")
    doc_id = upload(client, h, [PARENTAL], run_worker=False).json()["id"]
    assert client.post(f"{API}/documents/{doc_id}/retry", headers=h).status_code == 409  # not failed
    with SessionLocal() as db:
        from app.models.document import Document

        doc = db.get(Document, doc_id)
        try:
            job_service.enqueue(db, doc)
            raised = None
        except Exception as exc:  # noqa: BLE001
            raised = exc
    assert raised is not None and getattr(raised, "code", "") == "JOB_ALREADY_ACTIVE"
    assert worker.drain() == 1
    assert _get(client, h, doc_id)["processing_status"] == "ready"


def test_a_job_is_claimed_by_exactly_one_worker(client):
    h = new_user(client, "a@example.com")
    upload(client, h, [PARENTAL], run_worker=False)
    first = job_service.claim_next("worker-a")
    second = job_service.claim_next("worker-b")
    assert first is not None and second is None
    # A worker that does not own the job cannot run it.
    job_service.run_job(first, "worker-b")
    assert _job_status(first) == "processing"
    job_service.run_job(first, "worker-a")
    assert _job_status(first) == "completed"


def _job_status(job_id):
    with engine.connect() as conn:
        return conn.execute(text("SELECT status FROM processing_jobs WHERE id=:i"), {"i": job_id}).scalar_one()


def test_a_job_abandoned_by_a_dead_worker_is_recovered(client):
    h = new_user(client, "a@example.com")
    doc_id = upload(client, h, [PARENTAL], run_worker=False).json()["id"]
    job_id = job_service.claim_next("dead-worker")
    assert job_service.recover_stale() == 0  # heartbeat is fresh
    with SessionLocal() as db:
        db.get(ProcessingJob, job_id).heartbeat_at = utcnow() - timedelta(hours=2)
        db.commit()
    assert job_service.recover_stale() == 1
    assert _get(client, h, doc_id)["job"]["status"] == "queued"
    worker.drain()
    doc = _get(client, h, doc_id)
    assert doc["processing_status"] == "ready" and doc["job"]["attempts"] == 2


def test_deleting_a_document_mid_processing_leaves_no_orphans(client, monkeypatch):
    h = new_user(client, "a@example.com")
    real = job_service.get_embedder()

    class DeletesWhileRunning:
        def embed(self, texts):
            client.delete(f"{API}/documents/{doc_id}", headers=h)
            return real.embed(texts)

    monkeypatch.setattr(job_service, "get_embedder", lambda: DeletesWhileRunning())
    doc_id = upload(client, h, [PARENTAL], run_worker=False).json()["id"]
    worker.drain()
    assert client.get(f"{API}/documents/{doc_id}", headers=h).status_code == 404
    assert vector_service._collection().get(where={"document_id": doc_id})["ids"] == []
    assert _chunks(doc_id) == 0


def test_job_endpoints_are_owner_only(client):
    a, b = new_user(client, "a@example.com"), new_user(client, "b@example.com")
    doc = ready_document(client, a, [PARENTAL])
    job_id = doc["job"]["id"]
    assert client.get(f"{API}/jobs/{job_id}", headers=a).json()["status"] == "completed"
    listing = client.get(f"{API}/jobs", headers=a).json()
    assert listing["total"] == 1 and listing["items"][0]["document_id"] == doc["id"]
    assert "error_detail" not in listing["items"][0]

    assert client.get(f"{API}/jobs/{job_id}", headers=b).status_code == 404
    assert client.post(f"{API}/jobs/{job_id}/retry", headers=b).status_code == 404
    assert client.get(f"{API}/jobs", headers=b).json()["total"] == 0
    assert client.get(f"{API}/jobs/{job_id}").status_code == 401
    assert client.get(f"{API}/jobs").status_code == 401


def test_jobs_page_filters_by_status_and_retry_endpoint_requeues(client, monkeypatch):
    h = new_user(client, "a@example.com")
    monkeypatch.setattr(job_service, "get_embedder", lambda: FlakyEmbedder(None, failures=99))
    doc_id = upload(client, h, [PARENTAL]).json()["id"]
    failed = client.get(f"{API}/jobs", params={"status": "failed"}, headers=h).json()
    assert failed["total"] == 1
    monkeypatch.undo()
    r = client.post(f"{API}/jobs/{failed['items'][0]['id']}/retry", headers=h)
    assert r.status_code == 202 and r.json()["id"] == doc_id
    worker.drain()
    assert client.get(f"{API}/jobs", params={"status": "completed"}, headers=h).json()["total"] == 1
    assert client.get(f"{API}/jobs", params={"status": "bogus"}, headers=h).status_code == 422


def test_pdf_helper_makes_real_pdfs():
    assert make_pdf(["x"]).startswith(b"%PDF-")
