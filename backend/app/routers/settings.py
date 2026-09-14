"""Plan limits and team management (settings)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_agent
from ..models import Agent, Conversation, Plan, Site, Tenant
from ..security import hash_password

router = APIRouter(prefix="/api/agent", tags=["settings"])


def _plan(db: Session, plan_name: str) -> Plan:
    plan = db.get(Plan, plan_name)
    if plan is None:  # unknown plan name in the tenants table
        raise HTTPException(status_code=500, detail="Unknown plan")
    return plan


def _tenant(db: Session, agent: Agent) -> Tenant:
    tenant = db.get(Tenant, agent.tenant_id)
    assert tenant is not None
    return tenant


class PlanChange(BaseModel):
    plan: str


@router.get("/settings")
def get_settings(agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)) -> dict:
    plan = _plan(db, _tenant(db, agent).plan)
    return {
        "plan": plan.name,
        "max_sites": plan.max_sites,
        "max_agents": plan.max_agents,
        "site_count": db.query(Site).filter(Site.tenant_id == agent.tenant_id).count(),
        "agent_count": db.query(Agent).filter(Agent.tenant_id == agent.tenant_id).count(),
        "open_conversations": db.query(Conversation)
        .filter(Conversation.tenant_id == agent.tenant_id, Conversation.status == "open")
        .count(),
    }


@router.post("/settings/plan")
def change_plan(
    body: PlanChange,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
) -> dict:
    if not agent.is_owner:
        raise HTTPException(status_code=403, detail="Only the owner can change the plan")
    plan = _plan(db, body.plan)
    tenant = _tenant(db, agent)
    tenant.plan = plan.name
    db.commit()
    return {"plan": plan.name}


# --- team management ---------------------------------------------------------


class AgentCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=200)


@router.get("/agents")
def list_agents(
    agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)
) -> list[dict]:
    agents = db.query(Agent).filter(Agent.tenant_id == agent.tenant_id).all()
    return [
        {"id": a.id, "email": a.email, "is_owner": a.is_owner, "tenant_id": a.tenant_id}
        for a in agents
    ]


@router.post("/agents", status_code=201)
def add_agent(
    body: AgentCreate,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
) -> dict:
    if not agent.is_owner:
        raise HTTPException(status_code=403, detail="Only the owner can add agents")
    if db.query(Agent).filter_by(email=body.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    plan = _plan(db, _tenant(db, agent).plan)
    count = db.query(Agent).filter(Agent.tenant_id == agent.tenant_id).count()
    if plan.max_agents is not None and count >= plan.max_agents:
        raise HTTPException(
            status_code=403,
            detail=f"Plan limit reached: {plan.name} allows {plan.max_agents} agents. Upgrade to Pro for unlimited.",
        )

    new_agent = Agent(
        tenant_id=agent.tenant_id,
        email=body.email,
        password_hash=hash_password(body.password),
        is_owner=False,
    )
    db.add(new_agent)
    db.commit()
    return {"id": new_agent.id, "email": new_agent.email, "is_owner": False}
