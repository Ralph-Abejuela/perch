import uuid

from tests.conftest import signup


def _new_client_session():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


def _mk(email, tenant):
    c = _new_client_session()
    assert signup(c, email, tenant=tenant).status_code == 201
    return c


def test_free_plan_blocks_second_site():
    c = _mk(f"{uuid.uuid4().hex}@x.com", "Solo")
    assert c.post("/api/sites", json={"name": "one"}).status_code == 201
    r = c.post("/api/sites", json={"name": "two"})
    assert r.status_code == 403
    assert "Plan limit reached" in r.json()["detail"]
    assert "Upgrade to Pro" in r.json()["detail"]


def test_free_plan_blocks_third_agent():
    c = _mk(f"{uuid.uuid4().hex}@x.com", "Small")
    email = f"{uuid.uuid4().hex}@x.com"
    assert c.post("/api/agent/agents", json={"email": email, "password": "longenough1"}).status_code == 201
    r = c.post("/api/agent/agents", json={"email": f"{uuid.uuid4().hex}@x.com", "password": "longenough1"})
    assert r.status_code == 403
    assert "2 agents" in r.json()["detail"]


def test_upgrade_to_pro_removes_limits():
    c = _mk(f"{uuid.uuid4().hex}@x.com", "Grower")
    assert c.post("/api/sites", json={"name": "one"}).status_code == 201
    assert c.post("/api/sites", json={"name": "two"}).status_code == 403

    r = c.post("/api/agent/settings/plan", json={"plan": "pro"})
    assert r.status_code == 200
    assert c.post("/api/sites", json={"name": "two"}).status_code == 201
    assert c.post("/api/sites", json={"name": "three"}).status_code == 201


def test_settings_shows_plan_usage():
    c = _mk(f"{uuid.uuid4().hex}@x.com", "Metrics")
    assert c.post("/api/sites", json={"name": "one"}).status_code == 201
    s = c.get("/api/agent/settings").json()
    assert s["plan"] == "free"
    assert s["max_sites"] == 1
    assert s["site_count"] == 1
    assert s["agent_count"] == 1


def test_non_owner_cannot_manage_plan_or_team():
    c = _mk(f"{uuid.uuid4().hex}@x.com", "Team")
    email = f"{uuid.uuid4().hex}@x.com"
    c.post("/api/agent/agents", json={"email": email, "password": "longenough1"})

    # Sign in as the non-owner agent.
    member = _new_client_session()
    assert member.post("/api/auth/login", json={"email": email, "password": "longenough1"}).status_code == 200

    assert member.post("/api/agent/settings/plan", json={"plan": "pro"}).status_code == 403
    assert member.post("/api/agent/agents", json={"email": f"{uuid.uuid4().hex}@x.com", "password": "longenough1"}).status_code == 403
    assert member.get("/api/agent/agents").status_code == 200  # viewing is fine
