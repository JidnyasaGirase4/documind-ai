"""Test setup.

Tests run against an isolated MySQL/MariaDB schema (`documind_ai_test`, created in XAMPP), built with the
real Alembic migrations, plus temporary upload/Chroma folders. The environment is configured BEFORE the
app is imported. The embedder is the tiny deterministic `hashing` provider and LLM calls are faked, so
no model download or API key is needed; none of that pretends to be live AI."""

import os
import shutil
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="documind-tests-"))
os.environ.update(
    {
        "APP_ENV": "test",
        "DATABASE_URL": "mysql+pymysql://root:@127.0.0.1:3306/documind_ai_test?charset=utf8mb4",
        "JWT_SECRET_KEY": "test-secret-key-that-is-long-enough-for-hs256-signing",
        "EMBEDDING_PROVIDER": "hashing",
        "LLM_PROVIDER": "mock",
        "UPLOAD_DIRECTORY": str(_TMP / "uploads"),
        "CHROMA_PERSIST_DIRECTORY": str(_TMP / "chroma"),
        "RETRIEVAL_MIN_SIMILARITY": "0.2",
        "RATE_LIMIT_ENABLED": "false",
        "FRONTEND_ORIGIN": "http://localhost:5173",
    }
)

import pymupdf  # noqa: E402
import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.config import BACKEND_DIR  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services import vector_service  # noqa: E402
from app.utils import rate_limit  # noqa: E402

API = "/api/v1"
TABLES_IN_DELETE_ORDER = ["messages", "conversations", "processing_jobs", "document_chunks", "documents", "users"]


@pytest.fixture(scope="session", autouse=True)
def database():
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    command.downgrade(cfg, "base")  # start from a clean schema, then prove the migrations build it
    command.upgrade(cfg, "head")
    yield
    command.downgrade(cfg, "base")
    engine.dispose()
    shutil.rmtree(_TMP, ignore_errors=True)


@pytest.fixture(autouse=True)
def clean_state():
    """Every test starts with empty tables, an empty vector index and no upload files."""
    rate_limit.reset()
    with engine.begin() as conn:
        for table in TABLES_IN_DELETE_ORDER:
            conn.execute(text(f"DELETE FROM {table}"))
    col = vector_service._collection()
    ids = col.get()["ids"]
    if ids:
        col.delete(ids=ids)
    shutil.rmtree(_TMP / "uploads", ignore_errors=True)
    yield


@pytest.fixture
def client():
    return TestClient(app)


# ----------------------------------------------------------------- helpers
def make_pdf(pages: list[str]) -> bytes:
    """A real PDF with one text page per entry (an empty string gives a page with no text)."""
    doc = pymupdf.open()
    for body in pages:
        page = doc.new_page()
        if body:
            page.insert_textbox(pymupdf.Rect(50, 50, 545, 790), body, fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


def register(client: TestClient, email: str, password: str = "Passw0rdOK", name: str = "Test User") -> dict:
    r = client.post(f"{API}/auth/register", json={"name": name, "email": email, "password": password})
    assert r.status_code == 201, r.text
    return r.json()


def login_headers(client: TestClient, email: str, password: str = "Passw0rdOK") -> dict:
    r = client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def new_user(client: TestClient, email: str) -> dict:
    register(client, email)
    return login_headers(client, email)


def upload(client: TestClient, headers: dict, pages: list[str] | bytes, filename: str = "doc.pdf", content_type: str = "application/pdf"):
    data = pages if isinstance(pages, bytes) else make_pdf(pages)
    return client.post(f"{API}/documents/upload", files={"file": (filename, data, content_type)}, headers=headers)


def ready_document(client: TestClient, headers: dict, pages: list[str], filename: str = "doc.pdf") -> dict:
    r = upload(client, headers, pages, filename)
    assert r.status_code == 202, r.text
    doc = client.get(f"{API}/documents/{r.json()['id']}", headers=headers).json()
    assert doc["processing_status"] == "ready", doc
    return doc


def new_conversation(client: TestClient, headers: dict) -> dict:
    r = client.post(f"{API}/conversations", json={}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def ask(client: TestClient, headers: dict, conversation_id: int, question: str, document_ids: list[int] | None = None):
    body = {"content": question}
    if document_ids is not None:
        body["document_ids"] = document_ids
    return client.post(f"{API}/conversations/{conversation_id}/messages", json=body, headers=headers)


PARENTAL = "Primary caregivers are entitled to sixteen weeks of paid parental leave. Secondary caregivers receive six weeks of paid leave."
WARRANTY = "The warranty covers manufacturing defects for twenty four months from the date of purchase."
