from app.core.config import settings
from app.core.security import create_access_token
from tests.conftest import API, login_headers, register


def test_register_returns_user_without_password(client):
    r = client.post(f"{API}/auth/register", json={"name": "Ada", "email": "Ada@Example.com", "password": "Passw0rdOK"})
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "ada@example.com"  # emails are normalised
    assert body["name"] == "Ada"
    assert "password" not in body and "password_hash" not in body
    assert body["created_at"].endswith("Z")


def test_duplicate_email_is_rejected(client):
    register(client, "dup@example.com")
    r = client.post(f"{API}/auth/register", json={"name": "Other", "email": "DUP@example.com", "password": "Passw0rdOK"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


def test_weak_password_and_bad_email_are_rejected(client):
    r = client.post(f"{API}/auth/register", json={"name": "A", "email": "a@example.com", "password": "short"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    r = client.post(f"{API}/auth/register", json={"name": "A", "email": "not-an-email", "password": "Passw0rdOK"})
    assert r.status_code == 422


def test_login_and_me(client):
    register(client, "me@example.com")
    headers = login_headers(client, "me@example.com")
    r = client.get(f"{API}/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "me@example.com"


def test_invalid_credentials_do_not_reveal_which_part_was_wrong(client):
    register(client, "who@example.com")
    wrong_password = client.post(f"{API}/auth/login", json={"email": "who@example.com", "password": "WrongPass1"})
    unknown_email = client.post(f"{API}/auth/login", json={"email": "nobody@example.com", "password": "WrongPass1"})
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()
    assert wrong_password.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_protected_routes_need_a_token(client):
    for path in ["/auth/me", "/documents", "/conversations", "/dashboard/stats", "/analytics/overview", "/settings/profile"]:
        r = client.get(f"{API}{path}")
        assert r.status_code == 401, path
        assert r.json()["error"]["code"] == "NOT_AUTHENTICATED"


def test_expired_and_tampered_tokens_are_rejected(client):
    user = register(client, "tok@example.com")
    expired = create_access_token(user["id"], expires_minutes=-1)
    r = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "TOKEN_EXPIRED"

    good = create_access_token(user["id"])
    r = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {good}x"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "INVALID_TOKEN"


def test_token_for_a_deleted_user_is_rejected(client):
    token = create_access_token(999999)
    r = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_login_is_rate_limited(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    register(client, "rl@example.com")
    codes = [client.post(f"{API}/auth/login", json={"email": "rl@example.com", "password": "WrongPass1"}).status_code for _ in range(12)]
    assert 429 in codes
    assert codes[0] == 401
