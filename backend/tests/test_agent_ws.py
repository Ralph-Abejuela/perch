import time
import uuid

import pytest
import redis as redis_sync

from tests.conftest import make_site, signup

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


def _vis_ws(client, site_key: str, conv_id: str):
    return client.websocket_connect(
        f"/api/widget/{site_key}/ws?visitor_id={VID}&conversation_id={conv_id}"
    )


def recv_message(ws):
    """Receive events until a chat message arrives (skips presence etc.)."""
    while True:
        e = ws.receive_json()
        if e.get("type") == "message":
            return e


def test_agent_receives_visitor_message_and_replies(client):
    key = make_site(client)
    conv_id = _conv(client, key)

    with client.websocket_connect("/api/agent/ws") as agent_ws:
        import time

        time.sleep(0.2)
        with _vis_ws(client, key, conv_id) as vis_ws:
            time.sleep(0.2)
            vis_ws.send_json({"type": "message", "body": "need help"})
            # Agent receives it over the tenant channel.
            event = recv_message(agent_ws)
            assert event["type"] == "message"
            assert event["sender"] == "visitor"
            assert event["conversation_id"] == conv_id

            # Agent replies; the visitor receives it over the conversation channel.
            agent_ws.send_json({"type": "agent_message", "conversation_id": conv_id, "body": "sure!"})
            reply = vis_ws.receive_json()
            while reply.get("sender") == "visitor":  # skip own echo (multi-tab support)
                reply = vis_ws.receive_json()
            assert reply["type"] == "message"
            assert reply["sender"] == "agent"
            assert reply["body"] == "sure!"


def test_fanout_reaches_multiple_agent_connections(client):
    key = make_site(client)
    conv_id = _conv(client, key)

    # Two independent connections (simulating two browser tabs / two servers).
    with client.websocket_connect("/api/agent/ws") as agent1:
        with client.websocket_connect("/api/agent/ws") as agent2:
            time.sleep(0.2)
            with _vis_ws(client, key, conv_id) as vis_ws:
                time.sleep(0.2)
                vis_ws.send_json({"type": "message", "body": "hello agents"})
                e1 = recv_message(agent1)
                e2 = recv_message(agent2)
                assert e1["body"] == "hello agents"
                assert e2["body"] == "hello agents"


def test_typing_flows_between_sides(client):
    key = make_site(client)
    conv_id = _conv(client, key)

    with client.websocket_connect("/api/agent/ws") as agent_ws:
        time.sleep(0.2)
        with _vis_ws(client, key, conv_id) as vis_ws:
            time.sleep(0.2)
            vis_ws.send_json({"type": "typing"})
            event = agent_ws.receive_json()
            assert event == {"type": "typing", "sender": "visitor", "conversation_id": conv_id}

            agent_ws.send_json({"type": "typing", "conversation_id": conv_id})
            event = vis_ws.receive_json()
            while event.get("type") == "message" or (
                event.get("type") == "typing" and event.get("sender") == "visitor"
            ):
                event = vis_ws.receive_json()
            assert event["type"] == "typing"
            assert event["sender"] == "agent"


def test_presence_dot(client):
    key = make_site(client)

    assert client.get(f"/api/widget/{key}/status").json() == {"agents_online": False}

    with client.websocket_connect("/api/agent/ws"):
        assert client.get(f"/api/widget/{key}/status").json() == {"agents_online": True}

    assert client.get(f"/api/widget/{key}/status").json() == {"agents_online": False}


def test_offline_capture_flow(client):
    key = make_site(client)

    r = client.post(
        f"/api/widget/{key}/offline",
        json={"visitor_id": VID, "email": "lead@example.com", "body": "call me back"},
    )
    assert r.status_code == 201

    # Agent sees the capture in the dashboard API.
    caps = client.get("/api/agent/captures").json()
    assert [c["email"] for c in caps] == ["lead@example.com"]

    cap_id = caps[0]["id"]
    assert (
        client.post("/api/agent/captures/{id}/resolve".format(id=cap_id), json={"resolved": True}).status_code
        == 204
    )
    assert client.get("/api/agent/captures").json()[0]["resolved"] is True


def test_agent_ws_requires_auth(client_factory=None):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as anon:
        with pytest.raises(Exception):
            with anon.websocket_connect("/api/agent/ws"):
                pass
