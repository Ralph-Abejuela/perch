from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .config import settings
from .db import Base, engine
from .routers import agent, auth, settings as settings_router, sites, widget


@asynccontextmanager
async def lifespan(app: FastAPI):
    # v1: create_all is enough; switch to Alembic when migrations matter.
    Base.metadata.create_all(bind=engine)
    _seed_plans()
    yield


def _seed_plans() -> None:
    from sqlalchemy.orm import Session

    from .models import Plan

    with Session(engine) as db:
        for name, max_sites, max_agents in [("free", 1, 2), ("pro", None, None)]:
            if db.get(Plan, name) is None:
                db.add(Plan(name=name, max_sites=max_sites, max_agents=max_agents))
        db.commit()


app = FastAPI(title="Perch", version="0.1.0", lifespan=lifespan)

# Widget runs on arbitrary customer origins; dashboard origin is configurable.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sites.router)
app.include_router(widget.router)
app.include_router(agent.router)
app.include_router(settings_router.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/widget.js", include_in_schema=False)
def widget_js() -> FileResponse:
    """Serve the built widget bundle so the embed snippet only needs the API origin."""
    candidates = [
        Path(settings.widget_js_path),
        Path.cwd() / "widget.js",
        Path.cwd().parent / "widget" / "dist" / "perch.js",
    ]
    for path in candidates:
        if path.is_file():
            return FileResponse(path, media_type="application/javascript")
    raise FileNotFoundError("widget bundle not built; run `pnpm build` in widget/")
