from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_agent
from ..models import Agent, Site
from ..schemas import SiteCreate, SiteOut
from ..scoping import ScopedQuery

router = APIRouter(prefix="/api/sites", tags=["sites"])


def scoped(agent: Agent, db: Session) -> ScopedQuery:
    return ScopedQuery(db, agent.tenant_id)


@router.get("", response_model=list[SiteOut])
def list_sites(
    agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)
) -> list[SiteOut]:
    sites = scoped(agent, db).all(Site)
    return [SiteOut(id=s.id, name=s.name, key=s.key) for s in sites]


@router.post("", response_model=SiteOut, status_code=201)
def create_site(
    body: SiteCreate,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
) -> SiteOut:
    site = Site(tenant_id=agent.tenant_id, name=body.name)
    scoped(agent, db).add(site)
    db.commit()
    return SiteOut(id=site.id, name=site.name, key=site.key)


@router.delete("/{site_id}", status_code=204)
def delete_site(
    site_id: str,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
) -> None:
    site = scoped(agent, db).get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")
    db.delete(site)
    db.commit()


@router.get("/{site_id}", response_model=SiteOut)
def get_site(
    site_id: str,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
) -> SiteOut:
    site = scoped(agent, db).get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")
    return SiteOut(id=site.id, name=site.name, key=site.key)
