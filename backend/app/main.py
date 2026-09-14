from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import Base, engine
from .routers import auth, sites, widget


@asynccontextmanager
async def lifespan(app: FastAPI):
    # v1: create_all is enough; switch to Alembic when migrations matter.
    Base.metadata.create_all(bind=engine)
    yield


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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
