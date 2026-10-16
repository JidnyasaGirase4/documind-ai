"""Authorization and data-isolation tests.

Two kinds of checks: (1) every route of the API is enumerated, so a newly added endpoint cannot ship without
authentication; (2) user B tries every resource endpoint with ids that belong to user A and must learn nothing."""

import re

import pytest

from app.core.config import settings
from app.main import app
from tests.conftest import API, PARENTAL, WARRANTY, ask, new_conversation, new_user, ready_document, upload
from tests.test_rag import use_llm

PUBLIC = {("POST", "/api/v1/auth/register"), ("POST", "/api/v1/auth/login")}


def _api_routes():
    # The OpenAPI document lists every route regardless of how routers are nested.
    for path, operations in app.openapi()["paths"].items():
        if path.startswith("/api/v1"):
            for method in operations:
                if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                    yield method.upper(), path


def _concrete(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "1", path)


ROUTES = sorted(_api_routes())


def test_route_inventory_is_not_empty():
    assert len(ROUTES) >= 25
    assert PUBLIC <= set(ROUTES)


@pytest.mark.parametrize("method,path", [r for r in ROUTES if r not in PUBLIC], ids=lambda v: str(v))
def test_every_protected_route_rejects_missing_or_invalid_tokens(client, method, path):
    url = _concrete(path)
    kwargs = {"json": {}} if method in {"POST", "PATCH", "PUT"} else {}
    if path.endswith("/documents/upload"):
        kwargs = {"files": {"file": ("a.pdf", b"%PDF-1.4", "application/pdf")}}
    missing = client.request(method, url, **kwargs)
    assert missing.status_code == 401, f"{method} {path} answered {missing.status_code} without a token"
    bogus = client.request(method, url, headers={"Authorization": "Bearer not.a.token"}, **kwargs)
    assert bogus.status_code == 401, f"{method} {path} accepted an invalid token"
    wrong_scheme = client.request(method, url, headers={"Authorization": "Basic abc"}, **kwargs)
    assert wrong_scheme.status_code == 401


def test_expired_and_foreign_signed_tokens_are_rejected(client):
    import time

    import jwt

    new_user(client, "a@example.com")
    now = int(time.time())
    expired = jwt.encode({"sub": "1", "iat": now - 7200, "exp": now - 3600}, settings.jwt_secret_key, algorithm="HS256")
    forged = jwt.encode({"sub": "1", "iat": now, "exp": now + 3600}, "some-other-secret-that-is-long-enough-1234", algorithm="HS256")
    unsigned = jwt.encode({"sub": "1", "exp": now + 3600}, key=None, algorithm="none")
    for token in (expired, forged, unsigned):
        r = client.get(f"{API}/documents", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401


@pytest.fixture
def world(client, monkeypatch):
    """User A owns a document, a conversation with an answer, and a processing job."""
    a, b = new_user(client, "a@example.com"), new_user(client, "b@example.com")
    doc = ready_document(client, a, [PARENTAL, WARRANTY], "secret-handbook.pdf")
    conv = new_conversation(client, a)
    use_llm(monkeypatch, "Primary caregivers get sixteen weeks of paid leave [S1].")
    answer = ask(client, a, conv["id"], "How many weeks of paid parental leave do primary caregivers get?").json()["assistant_message"]
    return {"a": a, "b": b, "doc": doc, "conv": conv, "answer": answer, "job": doc["job"]["id"], "cite": answer["citations"][0]}


def test_user_b_cannot_touch_user_a_resources(client, world):
    b, doc, conv = world["b"], world["doc"], world["conv"]
    d, c = f"{API}/documents/{doc['id']}", f"{API}/conversations/{conv['id']}"
    attempts = [
        ("GET", d, None),
        ("GET", f"{d}/preview", None),
        ("GET", f"{d}/pages/1/image", None),
        ("GET", f"{d}/highlights?chunk_id={world['cite']['chunk_id']}", None),
        ("POST", f"{d}/retry", None),
        ("DELETE", d, None),
        ("GET", c, None),
        ("PATCH", c, {"title": "hijacked"}),
        ("DELETE", c, None),
        ("POST", f"{c}/messages", {"content": "What does the handbook say?"}),
        ("GET", f"{API}/jobs/{world['job']}", None),
        ("POST", f"{API}/jobs/{world['job']}/retry", None),
    ]
    for method, url, body in attempts:
        r = client.request(method, url, headers=b, json=body) if body else client.request(method, url, headers=b)
        assert r.status_code == 404, f"{method} {url} -> {r.status_code}: {r.text[:200]}"
        assert "secret-handbook" not in r.text and "sixteen weeks" not in r.text

    # Listings never include A's data.
    assert client.get(f"{API}/documents", headers=b).json()["total"] == 0
    assert client.get(f"{API}/conversations", headers=b).json()["total"] == 0
    assert client.get(f"{API}/jobs", headers=b).json()["total"] == 0
    # ... and nothing was changed by the attempts above.
    still = client.get(d, headers=world["a"])
    assert still.status_code == 200 and still.json()["processing_status"] == "ready"
    assert client.get(c, headers=world["a"]).json()["title"] != "hijacked"


def test_b_cannot_search_a_documents_even_by_selecting_them(client, world, monkeypatch):
    b = world["b"]
    conv_b = new_conversation(client, b)
    fake = use_llm(monkeypatch, "Primary caregivers get sixteen weeks [S1].")
    r = ask(client, b, conv_b["id"], "paid parental leave caregivers weeks", [world["doc"]["id"]])
    assert r.status_code == 404
    # B has no documents of their own, so the unscoped question is refused rather than answered from A's files.
    r = ask(client, b, conv_b["id"], "paid parental leave caregivers weeks")
    assert r.status_code == 400 and r.json()["error"]["code"] == "NO_READY_DOCUMENTS"
    assert not fake.calls


def test_retrieval_only_returns_the_askers_own_chunks_when_content_is_identical(client, monkeypatch):
    a, b = new_user(client, "a@example.com"), new_user(client, "b@example.com")
    doc_a = ready_document(client, a, [PARENTAL], "a-copy.pdf")
    doc_b = ready_document(client, b, [PARENTAL], "b-copy.pdf")
    fake = use_llm(monkeypatch, "Sixteen weeks [S1].")
    conv = new_conversation(client, b)
    cites = ask(client, b, conv["id"], "paid parental leave weeks primary caregivers").json()["assistant_message"]["citations"]
    assert {c["document_id"] for c in cites} == {doc_b["id"]}
    prompt = fake.calls[0][1][-1]["content"]
    assert "a-copy.pdf" not in prompt and "b-copy.pdf" in prompt
    assert doc_a["id"] != doc_b["id"]


def test_b_cannot_read_a_citation_or_message_through_the_api(client, world):
    # Messages are only reachable through the owner's conversation, and citations carry no file path or URL.
    cite = world["cite"]
    assert set(cite) == {"document_id", "document_name", "page_number", "excerpt", "chunk_id", "version_id", "version_number", "version_is_current"}
    assert client.get(f"{API}/conversations/{world['conv']['id']}", headers=world["b"]).status_code == 404
    serialized = str(client.get(f"{API}/documents/{world['doc']['id']}", headers=world["a"]).json())
    assert "storage_path" not in serialized and ".pdf" not in serialized.replace("secret-handbook.pdf", "")


def test_security_headers_and_no_store_on_api_responses(client):
    h = new_user(client, "a@example.com")
    r = client.get(f"{API}/documents", headers=h)
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["cache-control"] == "no-store"


def test_upload_validation_covers_type_magic_bytes_size_and_page_limit(client, monkeypatch):
    h = new_user(client, "a@example.com")
    assert upload(client, h, b"MZ\x90\x00 executable pretending to be a pdf", "evil.pdf").status_code == 415
    assert upload(client, h, b"<html><script>alert(1)</script></html>", "page.pdf", "text/html").status_code == 415
    assert upload(client, h, [PARENTAL], "photo.png", "image/png").status_code == 415
    monkeypatch.setattr(settings, "max_pdf_pages", 1)
    r = upload(client, h, [PARENTAL, WARRANTY], "long.pdf")
    assert r.status_code == 415 and r.json()["error"]["code"] == "TOO_MANY_PAGES"
    assert client.get(f"{API}/documents", headers=h).json()["total"] == 0


def test_error_responses_do_not_leak_internals(client):
    h = new_user(client, "a@example.com")
    for url in (f"{API}/documents/999999", f"{API}/jobs/999999", f"{API}/conversations/999999"):
        r = client.get(url, headers=h)
        assert r.status_code == 404
        body = r.text
        assert "Traceback" not in body and "sqlalchemy" not in body.lower() and "C:\\" not in body


def test_secrets_are_not_hardcoded_or_committed():
    from pathlib import Path

    backend = Path(__file__).resolve().parents[1]
    for path in (backend / "app").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"(sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|password\s*=\s*['\"][^'\"]{6,}['\"])", text), f"possible secret in {path}"
    example = (backend / ".env.example").read_text(encoding="utf-8")
    assert "replace_with_a_long_random_secret" in example and "LLM_API_KEY=\n" in example
    gitignore = (backend / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore.split()
