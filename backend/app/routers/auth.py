from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import COOKIE_NAME, get_current_agent
from ..models import Agent, Tenant
from ..schemas import AgentOut, LoginRequest, SignupRequest
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_session_cookie(response: Response, agent: Agent) -> None:
    token = create_access_token(agent.id, agent.tenant_id)
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
        max_age=60 * 60 * 24 * 7,
        path="/",
    )


@router.post("/signup", response_model=AgentOut, status_code=201)
def signup(body: SignupRequest, response: Response, db: Session = Depends(get_db)) -> AgentOut:
    if db.query(Agent).filter_by(email=body.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    tenant = Tenant(name=body.tenant_name)
    db.add(tenant)
    db.flush()  # assign tenant.id before referencing it

    agent = Agent(
        tenant_id=tenant.id,
        email=body.email,
        password_hash=hash_password(body.password),
        is_owner=True,
    )
    db.add(agent)
    db.commit()

    _set_session_cookie(response, agent)
    return _agent_out(agent, tenant)


@router.post("/login", response_model=AgentOut)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)) -> AgentOut:
    agent = db.query(Agent).filter_by(email=body.email).first()
    if agent is None or not verify_password(body.password, agent.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    _set_session_cookie(response, agent)
    return _agent_out(agent, db.get(Tenant, agent.tenant_id))


@router.post("/logout", status_code=204)
def logout(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


@router.get("/me", response_model=AgentOut)
def me(agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)) -> AgentOut:
    return _agent_out(agent, db.get(Tenant, agent.tenant_id))


def _agent_out(agent: Agent, tenant: Tenant) -> AgentOut:
    return AgentOut(
        id=agent.id,
        email=agent.email,
        is_owner=agent.is_owner,
        tenant_id=agent.tenant_id,
        tenant_name=tenant.name,
        tenant_plan=tenant.plan,
    )
