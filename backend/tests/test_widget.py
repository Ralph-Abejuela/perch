import uuid

import pytest
import redis as redis_sync

from tests.conftest import make_site

VID = str(uuid.uuid4())


@pytest.fixture(scope="module", autouse=True)
def require_redis():
    try:
        r = redis_sync.from_url("redis://127.0.0.1:6379/15")
        r.ping()
        r.flushdb()
    except Exception:
        pytest.skip("Redis not available on localhost:6379/15")


def _conv(client, site_key: str) -> str:
    r = client.post(f"/api/widget/{site_key}/conversations", json={"visitor_id": VID})
    assert r.status_code == 201
    return r.json()["conversation_id"]


def test_widget_flow_rest(client):
    key = make_site(client)

    cfg = client.get(f"/api/widget/{key}/config")
    assert cfg.status_code == 200
    assert cfg.json()["site_name"] == "Blog"

    conv_id = _conv(client, key)

    msg = client.post(
        f"/api/widget/{key}/conversations/{conv_id}/messages",
        json={"visitor_id": VID, "body": "Hello!"},
    )
    assert msg.status_code == 201
    assert msg.json()["sender"] == "visitor"

    history = client.get(
        f"/api/widget/{key}/conversations/{conv_id}/messages", params={"visitor_id": VID}
    )
    assert [m["body"] for m in history.json()] == ["Hello!"]


def test_unknown_site_key_404(client):
    assert client.get("/api/widget/nope/config").status_code == 404


def test_invalid_visitor_id_400(client):
    key = make_site(client)
    r = client.post(f"/api/widget/{key}/conversations", json={"visitor_id": "not-a-uuid"})
    assert r.status_code == 400


def test_visitor_cannot_read_other_conversation(client):
    key = make_site(client)
    conv_a = _conv(client, key)
    other = str(uuid.uuid4())
    client.post(f"/api/widget/{key}/conversations", json={"visitor_id": other})
    r = client.get(
        f"/api/widget/{key}/conversations/{conv_a}/messages", params={"visitor_id": other}
    )
    assert r.status_code == 404


def test_rate_limit(client):
    from app.config import settings

    key = make_site(client)
    conv_id = _conv(client, key)

    last = None
    for _ in range(settings.rate_limit_per_minute):
        last = client.post(
            f"/api/widget/{key}/conversations/{conv_id}/messages",
            json={"visitor_id": VID, "body": "spam"},
        )
        assert last.status_code == 201
    assert (
        client.post(
            f"/api/widget/{key}/conversations/{conv_id}/messages",
            json={"visitor_id": VID, "body": "spam"},
        ).status_code
        == 429
    )


def test_ws_roundtrip(client):
    key = make_site(client)
    conv_id = _conv(client, key)

    with client.websocket_connect(
        f"/api/widget/{key}/ws?visitor_id={VID}&conversation_id={conv_id}"
    ) as ws:
        import time

        time.sleep(0.2)  # let the pubsub subscription settle
        ws.send_json({"type": "message", "body": "hi over ws"})
        event = ws.receive_json()
        assert event["type"] == "message"
        assert event["sender"] == "visitor"
        assert event["body"] == "hi over ws"

        ws.send_json({"type": "identify", "name": "Val", "email": "val@example.com"})
