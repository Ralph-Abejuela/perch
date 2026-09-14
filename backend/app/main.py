from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import Base, engine
from .routers import auth, sites


@asynccontextmanager
async def lifespan(app: FastAPI):
    # v1: create_all is enough; switch to Alembic when migrations matter.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Perch", version="0.1.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(sites.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
