import pytest
from pydantic import ValidationError

from app.core.config import Settings
from tests.conftest import API


def test_health_reports_database_status(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "ok"}


def test_error_responses_share_one_shape(client):
    missing = client.get(f"{API}/nope")
    assert missing.status_code == 404
    assert set(missing.json()["error"]) == {"code", "message", "details"}

    invalid = client.post(f"{API}/auth/login", json={"email": "bad"})
    assert invalid.status_code == 422
    body = invalid.json()["error"]
    assert body["code"] == "VALIDATION_ERROR" and body["details"]


def test_cors_only_allows_the_configured_frontend_origin(client):
    ok = client.options(f"{API}/auth/login", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    other = client.options(f"{API}/auth/login", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in other.headers


def test_api_docs_are_available_in_development(client):
    assert client.get("/docs").status_code == 200
    assert "/api/v1/documents/upload" in client.get("/openapi.json").json()["paths"]


def _base(**over):
    values = {"database_url": "mysql+pymysql://u:p@127.0.0.1/db", "jwt_secret_key": "x" * 40}
    values.update(over)
    return values


def test_settings_require_secrets_and_reject_unsafe_production_config(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="mysql+pymysql://u:p@h/db")  # no JWT secret
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(_env_file=None, **_base(app_env="production", jwt_secret_key="replace_with_a_long_random_secret", llm_provider="anthropic"))
    with pytest.raises(ValidationError, match="mock"):
        Settings(_env_file=None, **_base(app_env="production", llm_provider="mock"))
    with pytest.raises(ValidationError, match="CHUNK_OVERLAP"):
        Settings(_env_file=None, **_base(chunk_size=100, chunk_overlap=100))
    ok = Settings(_env_file=None, **_base(app_env="production", llm_provider="anthropic", embedding_provider="sentence_transformers"))
    assert ok.app_env == "production"
