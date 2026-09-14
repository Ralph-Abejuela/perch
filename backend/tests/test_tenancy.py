from tests.conftest import signup


def _create_site(client, name):
    r = client.post("/api/sites", json={"name": name})
    assert r.status_code == 201
    return r.json()


def test_site_crud_is_tenant_scoped(client):
    signup(client, "a@example.com", tenant="A")
    site = _create_site(client, "A's blog")

    listed = client.get("/api/sites").json()
    assert [s["id"] for s in listed] == [site["id"]]
    assert site["key"]

    assert client.get(f"/api/sites/{site['id']}").status_code == 200
    assert client.delete(f"/api/sites/{site['id']}").status_code == 204
    assert client.get(f"/api/sites/{site['id']}").status_code == 404


def test_tenant_b_cannot_see_tenant_a_sites(client):
    signup(client, "ten-a@example.com", tenant="A")
    site_a = _create_site(client, "A's site")

    signup(client, "ten-b@example.com", tenant="B")  # same client, new session replaces A's cookie

    assert client.get("/api/sites").json() == []
    assert client.get(f"/api/sites/{site_a['id']}").status_code == 404
    assert client.delete(f"/api/sites/{site_a['id']}").status_code == 404


def test_site_keys_are_unique(client):
    signup(client, "keys@example.com", tenant="Keys")
    client.post("/api/agent/settings/plan", json={"plan": "pro"})
    k1 = _create_site(client, "one")["key"]
    k2 = _create_site(client, "two")["key"]
    assert k1 != k2
