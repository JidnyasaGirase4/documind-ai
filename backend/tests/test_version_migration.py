"""Migration 0007: existing documents become version 1 without losing anything, and the migration can be rolled back.

Runs against the isolated test schema only (documind_ai_test): it steps that schema down to 0006, inserts "legacy" rows the
way the old application stored them, upgrades, checks the result, rolls back again and finally returns to head."""

import hashlib
from datetime import datetime

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text as sql

from app.core.config import BACKEND_DIR
from app.db.session import engine


def _cfg() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return cfg


def _q(conn, query, **params):
    return conn.execute(sql(query), params)


@pytest.fixture
def legacy_world(tmp_path):
    cfg = _cfg()
    engine.dispose()
    command.downgrade(cfg, "0006")
    f1 = tmp_path / "a.pdf"
    f1.write_bytes(b"%PDF-1.4 legacy file one")
    now = datetime(2026, 1, 2, 3, 4, 5)
    ids = {}
    with engine.begin() as c:
        _q(c, "INSERT INTO users (name, email, password_hash, is_active, created_at, updated_at) VALUES ('Old', 'old@example.com', 'x', 1, :n, :n)", n=now)
        uid = ids["user"] = _q(c, "SELECT id FROM users WHERE email='old@example.com'").scalar()
        for key, path, status in (("d1", str(f1), "ready"), ("d2", str(tmp_path / "missing.pdf"), "failed")):
            _q(c, "INSERT INTO documents (user_id, original_filename, storage_path, file_size, mime_type, processing_status, total_pages, created_at, updated_at) "
                  "VALUES (:u, :n, :p, 24, 'application/pdf', :s, 2, :c, :c)", u=uid, n=f"{key}.pdf", p=path, s=status, c=now)
            ids[key] = _q(c, "SELECT id FROM documents WHERE original_filename=:n", n=f"{key}.pdf").scalar()
        _q(c, "INSERT INTO document_chunks (document_id, chunk_index, page_number, extracted_text, vector_reference, created_at) VALUES (:d, 0, 1, 'legacy text', 'chunk-1', :n)", d=ids["d1"], n=now)
        ids["chunk"] = _q(c, "SELECT id FROM document_chunks WHERE document_id=:d", d=ids["d1"]).scalar()
        _q(c, "INSERT INTO processing_jobs (document_id, status, progress, retry_count, attempts, max_attempts, created_at) VALUES (:d, 'completed', 100, 0, 1, 3, :n)", d=ids["d1"], n=now)
        ids["job"] = _q(c, "SELECT id FROM processing_jobs WHERE document_id=:d", d=ids["d1"]).scalar()
    ids["sha"] = hashlib.sha256(f1.read_bytes()).hexdigest()
    ids["when"] = now
    yield cfg, ids
    engine.dispose()
    command.upgrade(cfg, "head")
    with engine.begin() as c:  # leave the schema empty for the next test
        for table in ("processing_jobs", "document_chunks", "document_versions", "documents", "users"):
            _q(c, f"DELETE FROM {table}")


def test_existing_documents_become_version_one_and_keep_their_data(legacy_world):
    cfg, ids = legacy_world
    engine.dispose()
    command.upgrade(cfg, "head")
    with engine.connect() as c:
        v = _q(c, "SELECT * FROM document_versions WHERE document_id=:d", d=ids["d1"]).mappings().all()
        assert len(v) == 1 and v[0]["version_number"] == 1 and v[0]["checksum_sha256"] == ids["sha"]
        assert v[0]["original_filename"] == "d1.pdf" and v[0]["processing_status"] == "ready" and v[0]["created_by"] == ids["user"] and v[0]["created_at"] == ids["when"]
        doc = _q(c, "SELECT current_version_id, original_filename, processing_status, total_pages FROM documents WHERE id=:d", d=ids["d1"]).mappings().one()
        assert doc["current_version_id"] == v[0]["id"] and doc["original_filename"] == "d1.pdf" and doc["processing_status"] == "ready" and doc["total_pages"] == 2
        assert _q(c, "SELECT version_id FROM document_chunks WHERE id=:i", i=ids["chunk"]).scalar() == v[0]["id"]
        assert _q(c, "SELECT version_id FROM processing_jobs WHERE id=:i", i=ids["job"]).scalar() == v[0]["id"]
        # a document whose file is missing still gets a version; only its checksum is unknown
        v2 = _q(c, "SELECT checksum_sha256, processing_status FROM document_versions WHERE document_id=:d", d=ids["d2"]).mappings().one()
        assert v2["checksum_sha256"] is None and v2["processing_status"] == "failed"
        assert _q(c, "SELECT COUNT(*) FROM documents").scalar() == 2 and _q(c, "SELECT COUNT(*) FROM document_chunks").scalar() == 1


def test_rollback_keeps_documents_and_current_passages(legacy_world):
    cfg, ids = legacy_world
    engine.dispose()
    command.upgrade(cfg, "head")
    with engine.begin() as c:  # pretend a second version existed: its passages must not leak into the old schema
        v1 = _q(c, "SELECT id FROM document_versions WHERE document_id=:d", d=ids["d1"]).scalar()
        _q(c, "INSERT INTO document_versions (document_id, version_number, original_filename, storage_path, file_size, mime_type, processing_status, created_at) VALUES (:d, 2, 'n.pdf', 'p', 1, 'application/pdf', 'ready', NOW())", d=ids["d1"])
        v2 = _q(c, "SELECT id FROM document_versions WHERE document_id=:d AND version_number=2", d=ids["d1"]).scalar()
        _q(c, "INSERT INTO document_chunks (document_id, version_id, chunk_index, page_number, extracted_text, created_at) VALUES (:d, :v, 0, 1, 'second version text', NOW())", d=ids["d1"], v=v2)
        _q(c, "UPDATE documents SET current_version_id=:v WHERE id=:d", v=v1, d=ids["d1"])
    engine.dispose()
    command.downgrade(cfg, "0006")
    with engine.connect() as c:
        assert _q(c, "SELECT COUNT(*) FROM documents").scalar() == 2
        assert [r[0] for r in _q(c, "SELECT extracted_text FROM document_chunks")] == ["legacy text"]
        assert _q(c, "SELECT original_filename FROM documents WHERE id=:d", d=ids["d1"]).scalar() == "d1.pdf"
        assert _q(c, "SHOW TABLES LIKE 'document_versions'").first() is None
