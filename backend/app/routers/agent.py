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


# --- conversation inbox ------------------------------------------------------

PAGE_SIZE = 50


def _last_message(db: Session, conversation_id: str) -> Message | None:
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .first()
    )


@router.get("/conversations")
def list_conversations(
    status: str | None = None,
    page: int = 1,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
) -> dict:
    q = db.query(Conversation).filter(Conversation.tenant_id == agent.tenant_id)
    if status:
        q = q.filter(Conversation.status == status)
    total = q.count()
    convs = (
        q.order_by(Conversation.created_at.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE + 1)
        .all()
    )
    has_more = len(convs) > PAGE_SIZE
    convs = convs[:PAGE_SIZE]
    return {
        "items": [
            {
                "id": c.id,
                "site_id": c.site_id,
                "visitor_name": c.visitor_name,
                "visitor_email": c.visitor_email,
                "status": c.status,
                "created_at": c.created_at.isoformat(),
                "last_message": (
                    last.body if (last := _last_message(db, c.id)) else None
                ),
            }
            for c in convs
        ],
        "has_more": has_more,
    }


@router.get("/conversations/{conversation_id}/messages")
def conversation_messages(
    conversation_id: str,
    page: int = 1,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
) -> dict:
    conv = _conv_for_agent(db, agent, conversation_id)
    q = db.query(Message).filter(Message.conversation_id == conv.id)
    total = q.count()
    msgs = (
        q.order_by(Message.created_at.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE + 1)
        .all()
    )
    has_more = len(msgs) > PAGE_SIZE
    msgs = list(reversed(msgs[:PAGE_SIZE]))  # oldest → newest for display
    return {
        "items": [
            {"id": m.id, "sender": m.sender, "body": m.body, "ts": m.created_at.isoformat()}
            for m in msgs
        ],
        "has_more": has_more,
    }


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
