"""Agent-facing realtime: dashboard WebSocket (messages, typing, presence)
and offline-capture REST endpoints."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import SessionLocal, get_db
from ..deps import get_current_agent, get_current_agent_ws
from ..models import Agent, Conversation, Message, OfflineCapture
from ..realtime import (
    PRESENCE_TTL_S,
    clear_presence,
    publish_event,
    publish_tenant,
    subscribe_tenant,
    touch_presence,
)
from ..scoping import ScopedQuery

router = APIRouter(prefix="/api/agent", tags=["agent"])

MAX_BODY = 2000


# --- offline captures -------------------------------------------------------


@router.get("/captures")
def list_captures(
    agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)
) -> list[dict]:
    captures = (
        db.query(OfflineCapture)
        .filter(OfflineCapture.tenant_id == agent.tenant_id)
        .order_by(OfflineCapture.created_at.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": c.id,
            "site_id": c.site_id,
            "email": c.email,
            "body": c.body,
            "resolved": c.resolved,
            "ts": c.created_at.isoformat(),
        }
        for c in captures
    ]


class CaptureResolve(BaseModel):
    resolved: bool


@router.post("/captures/{capture_id}/resolve", status_code=204)
def resolve_capture(
    capture_id: str,
    body: CaptureResolve,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
) -> None:
    capture = ScopedQuery(db, agent.tenant_id).get(OfflineCapture, capture_id)
    if capture is None:
        raise HTTPException(status_code=404, detail="Capture not found")
    capture.resolved = body.resolved
    db.commit()


# --- dashboard websocket -----------------------------------------------------


def _conv_for_agent(db: Session, agent: Agent, conversation_id: str) -> Conversation:
    conv = db.get(Conversation, conversation_id)
    if conv is None or conv.tenant_id != agent.tenant_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.websocket("/ws")
async def agent_ws(websocket: WebSocket, agent: Agent = Depends(get_current_agent_ws)):
    await websocket.accept()
    db = SessionLocal()

    await touch_presence(agent.tenant_id, agent.id)
    await publish_tenant(
        agent.tenant_id,
        {"type": "presence", "agent_id": agent.id, "online": True},
    )

    async def pump():
        async for event in subscribe_tenant(agent.tenant_id):
            if event.get("type") == "presence" and event.get("agent_id") == agent.id:
                continue  # don't echo my own presence back to me
            await websocket.send_json(event)

    pump_task = asyncio.create_task(pump())
    try:
        while True:
            data = await websocket.receive_json()
            kind = data.get("type")

            if kind == "ping":
                await touch_presence(agent.tenant_id, agent.id)
                continue

            conversation_id = str(data.get("conversation_id") or "")
            try:
                conv = _conv_for_agent(db, agent, conversation_id)
            except HTTPException:
                continue

            if kind == "agent_message":
                body = str(data.get("body", "")).strip()
                if not body or len(body) > MAX_BODY or conv.status != "open":
                    continue
                msg = Message(
                    tenant_id=conv.tenant_id,
                    conversation_id=conv.id,
                    sender="agent",
                    body=body,
                )
                db.add(msg)
                db.commit()
                await publish_event(
                    conv.tenant_id,
                    conv.id,
                    {
                        "type": "message",
                        "id": msg.id,
                        "sender": "agent",
                        "conversation_id": conv.id,
                        "body": msg.body,
                        "ts": msg.created_at.isoformat(),
                    },
                )
            elif kind == "typing":
                await publish_event(
                    conv.tenant_id, conv.id, {"type": "typing", "sender": "agent", "conversation_id": conv.id}
                )
            elif kind == "close":
                conv.status = "closed"
                db.commit()
                await publish_event(
                    conv.tenant_id, conv.id, {"type": "status", "status": "closed", "conversation_id": conv.id}
                )
    except WebSocketDisconnect:
        pass
    finally:
        pump_task.cancel()
        await clear_presence(agent.tenant_id, agent.id)
        await publish_tenant(
            agent.tenant_id,
            {"type": "presence", "agent_id": agent.id, "online": False},
        )
        db.close()
