"""Public widget-facing endpoints. Authenticated by the site key (public id),
not by an agent session. Visitor identity is a client-generated UUID."""

import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import SessionLocal, get_db
from ..models import Conversation, Message, OfflineCapture, Site
from ..realtime import allow_message, online_agents, publish_event, publish_tenant, subscribe

router = APIRouter(prefix="/api/widget", tags=["widget"])

MAX_BODY = 2000


def _site(db: Session, site_key: str) -> Site:
    site = db.query(Site).filter_by(key=site_key).first()
    if site is None:
        raise HTTPException(status_code=404, detail="Unknown site key")
    return site


def _visitor_id(raw: str) -> str:
    try:
        return str(uuid.UUID(raw))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid visitor id")


def _conversation(db: Session, site: Site, conversation_id: str, visitor_id: str) -> Conversation:
    conv = db.get(Conversation, conversation_id)
    if conv is None or conv.site_id != site.id or conv.visitor_id != visitor_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


def _message_out(m: Message) -> dict:
    return {
        "type": "message",
        "id": m.id,
        "sender": m.sender,
        "body": m.body,
        "ts": m.created_at.astimezone(timezone.utc).isoformat(),
    }


class VisitorInfo(BaseModel):
    visitor_id: str
    name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)


class MessageIn(BaseModel):
    visitor_id: str
    body: str = Field(min_length=1, max_length=MAX_BODY)


@router.get("/{site_key}/config")
def config(site_key: str, db: Session = Depends(get_db)) -> dict:
    site = _site(db, site_key)
    return {"site_id": site.id, "site_name": site.name}


@router.get("/{site_key}/status")
async def status(site_key: str, db: Session = Depends(get_db)) -> dict:
    site = _site(db, site_key)
    return {"agents_online": await online_agents(site.tenant_id) > 0}


@router.post("/{site_key}/conversations", status_code=201)
def start_conversation(site_key: str, body: VisitorInfo, db: Session = Depends(get_db)) -> dict:
    site = _site(db, site_key)
    vid = _visitor_id(body.visitor_id)
    conv = Conversation(
        tenant_id=site.tenant_id,
        site_id=site.id,
        visitor_id=vid,
        visitor_name=body.name,
        visitor_email=body.email,
    )
    db.add(conv)
    db.commit()
    return {"conversation_id": conv.id}


@router.get("/{site_key}/conversations/{conversation_id}/messages")
def history(
    site_key: str, conversation_id: str, visitor_id: str, db: Session = Depends(get_db)
) -> list[dict]:
    site = _site(db, site_key)
    conv = _conversation(db, site, conversation_id, _visitor_id(visitor_id))
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at)
        .limit(200)
        .all()
    )
    return [_message_out(m) for m in messages]


@router.post("/{site_key}/conversations/{conversation_id}/messages", status_code=201)
async def send_message(
    site_key: str, conversation_id: str, body: MessageIn, db: Session = Depends(get_db)
) -> dict:
    site = _site(db, site_key)
    vid = _visitor_id(body.visitor_id)
    conv = _conversation(db, site, conversation_id, vid)
    if conv.status != "open":
        raise HTTPException(status_code=409, detail="Conversation is closed")
    if not await allow_message(site.key, vid):
        raise HTTPException(status_code=429, detail="Too many messages, slow down")

    msg = Message(tenant_id=conv.tenant_id, conversation_id=conv.id, sender="visitor", body=body.body)
    db.add(msg)
    db.commit()
    event = _message_out(msg)
    event["conversation_id"] = conv.id
    await publish_event(conv.tenant_id, conv.id, event)
    return event


class OfflineCaptureIn(BaseModel):
    visitor_id: str
    email: str = Field(min_length=3, max_length=320)
    body: str = Field(min_length=1, max_length=MAX_BODY)


@router.post("/{site_key}/offline", status_code=201)
async def offline_capture(site_key: str, body: OfflineCaptureIn, db: Session = Depends(get_db)) -> dict:
    site = _site(db, site_key)
    vid = _visitor_id(body.visitor_id)
    if not await allow_message(site.key, vid):
        raise HTTPException(status_code=429, detail="Too many messages, slow down")
    capture = OfflineCapture(
        tenant_id=site.tenant_id, site_id=site.id, visitor_id=vid, email=body.email, body=body.body
    )
    db.add(capture)
    db.commit()
    await publish_tenant(
        site.tenant_id,
        {
            "type": "capture",
            "id": capture.id,
            "site_id": site.id,
            "email": capture.email,
            "body": capture.body,
            "ts": capture.created_at.isoformat(),
        },
    )
    return {"id": capture.id}


@router.websocket("/{site_key}/ws")
async def visitor_ws(websocket: WebSocket, site_key: str, visitor_id: str, conversation_id: str):
    await websocket.accept()
    try:
        vid = _visitor_id(visitor_id)
    except HTTPException:
        await websocket.close(code=4400)
        return

    db = SessionLocal()
    try:
        site = _site(db, site_key)
        conv = _conversation(db, site, conversation_id, vid)
    except HTTPException:
        await websocket.close(code=4404)
        return

    async def pump_outgoing():
        async for event in subscribe(conv.id):
            await websocket.send_json(event)

    pump_task = asyncio.create_task(pump_outgoing())
    try:
        while True:
            data = await websocket.receive_json()
            kind = data.get("type")
            if kind == "message":
                body = str(data.get("body", "")).strip()
                if not body or len(body) > MAX_BODY:
                    continue
                if conv.status != "open" or not await allow_message(site.key, vid):
                    await websocket.send_json({"type": "error", "detail": "Message rejected"})
                    continue
                msg = Message(
                    tenant_id=conv.tenant_id, conversation_id=conv.id, sender="visitor", body=body
                )
                db.add(msg)
                db.commit()
                event = _message_out(msg)
                event["conversation_id"] = conv.id
                await publish_event(conv.tenant_id, conv.id, event)
            elif kind == "typing":
                await publish_event(
                    conv.tenant_id, conv.id, {"type": "typing", "sender": "visitor", "conversation_id": conv.id}
                )
            elif kind == "identify":
                conv.visitor_name = str(data.get("name") or "")[:200] or None
                conv.visitor_email = str(data.get("email") or "")[:320] or None
                db.commit()
            elif kind == "close":
                await websocket.close()
                break
    except WebSocketDisconnect:
        pass
    finally:
        pump_task.cancel()
        db.close()
