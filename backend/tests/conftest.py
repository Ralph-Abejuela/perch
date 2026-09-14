import os
import tempfile
import uuid

# Must run before app.config is imported anywhere.
_TMP = tempfile.mkdtemp(prefix="perch-test-")
os.environ["PERCH_DATABASE_URL"] = f"sqlite:///{_TMP}/perch-test.db"
os.environ["PERCH_REDIS_URL"] = "redis://127.0.0.1:6379/15"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def signup(client: TestClient, email: str, password: str = "correct-horse-battery", tenant: str = "Acme"):
    return client.post(
        "/api/auth/signup",
        json={"tenant_name": tenant, "email": email, "password": password},
    )


def make_site(client: TestClient, name: str = "Blog") -> str:
    """Signup + create a site; returns the public site key."""
    assert signup(client, f"{uuid.uuid4().hex}@example.com").status_code == 201
    r = client.post("/api/sites", json={"name": name})
    assert r.status_code == 201
    return r.json()["key"]
