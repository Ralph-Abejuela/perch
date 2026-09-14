from tests.conftest import signup


def test_signup_sets_session_and_me_works(client):
    r = signup(client, "owner@example.com")
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "owner@example.com"
    assert body["is_owner"] is True
    assert body["tenant_plan"] == "free"
    assert any(c.name == "perch_session" for c in client.cookies.jar)

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["tenant_name"] == "Acme"


def test_signup_rejects_short_password(client):
    r = signup(client, "shortpw@example.com", password="short")
    assert r.status_code == 422


def test_signup_duplicate_email_conflicts(client):
    assert signup(client, "dup@example.com").status_code == 201
    assert signup(client, "dup@example.com", tenant="Other").status_code == 409


def test_login_success_and_failure(client):
    signup(client, "login@example.com")

    bad = client.post("/api/auth/login", json={"email": "login@example.com", "password": "wrong-password"})
    assert bad.status_code == 401

    ok = client.post("/api/auth/login", json={"email": "login@example.com", "password": "correct-horse-battery"})
    assert ok.status_code == 200
    assert client.get("/api/auth/me").json()["email"] == "login@example.com"


def test_logout_clears_session(client):
    signup(client, "logout@example.com")
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_me_without_session_is_401(client):
    assert client.get("/api/auth/me").status_code == 401
