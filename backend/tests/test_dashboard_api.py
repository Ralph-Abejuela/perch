import time
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


def _send(client, site_key, conv_id, body, vid=VID):
    r = client.post(
        f"/api/widget/{site_key}/conversations/{conv_id}/messages",
        json={"visitor_id": vid, "body": body},
    )
    assert r.status_code == 201


def test_message_history_pagination(client):
    key = make_site(client)
    conv_id = _conv(client, key)
    for i in range(55):
        _send(client, key, conv_id, f"msg-{i:02d}")

    page1 = client.get(f"/api/agent/conversations/{conv_id}/messages").json()
    assert len(page1["items"]) == 50
    assert page1["has_more"] is True
    # page 1 = 50 newest, returned oldest → newest
    assert page1["items"][0]["body"] == "msg-05"
    assert page1["items"][-1]["body"] == "msg-54"

    page2 = client.get(f"/api/agent/conversations/{conv_id}/messages", params={"page": 2}).json()
    assert len(page2["items"]) == 5
    assert page2["has_more"] is False
    assert [m["body"] for m in page2["items"]] == [f"msg-{i:02d}" for i in range(5)]


def test_conversation_list_and_status_filter(client):
    key = make_site(client)
    conv_a = _conv(client, key)
    other_vid = str(uuid.uuid4())
    conv_b = client.post(
        f"/api/widget/{key}/conversations", json={"visitor_id": other_vid}
    ).json()["conversation_id"]
    _send(client, key, conv_a, "in A")
    _send(client, key, conv_b, "in B", vid=other_vid)

    inbox = client.get("/api/agent/conversations").json()
    assert len(inbox["items"]) == 2
    assert all(c["last_message"] for c in inbox["items"])

    # Close A over the agent WS, then filter.
    with client.websocket_connect("/api/agent/ws") as agent_ws:
        time.sleep(0.2)
        agent_ws.send_json({"type": "close", "conversation_id": conv_a})
        time.sleep(0.3)

    open_only = client.get("/api/agent/conversations", params={"status": "open"}).json()
    assert [c["id"] for c in open_only["items"]] == [conv_b]

    closed_only = client.get("/api/agent/conversations", params={"status": "closed"}).json()
    assert [c["id"] for c in closed_only["items"]] == [conv_a]
