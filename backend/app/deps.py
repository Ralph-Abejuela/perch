from fastapi import Depends, HTTPException, Request, Response, WebSocket
from sqlalchemy.orm import Session

from .db import get_db
from .models import Agent
from .security import decode_access_token

COOKIE_NAME = "perch_session"


def get_current_agent(request: Request, db: Session = Depends(get_db)) -> Agent:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid session")
    agent = db.get(Agent, payload["sub"])
    if agent is None or agent.tenant_id != payload["tenant"]:
        raise HTTPException(status_code=401, detail="Invalid session")
    return agent


def get_current_agent_ws(websocket: WebSocket, db: Session = Depends(get_db)) -> Agent:
    """WebSocket variant: session cookie comes from the handshake."""
    token = websocket.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid session")
    agent = db.get(Agent, payload["sub"])
    if agent is None or agent.tenant_id != payload["tenant"]:
        raise HTTPException(status_code=401, detail="Invalid session")
    return agent
