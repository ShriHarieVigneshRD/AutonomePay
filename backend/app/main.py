import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, evals, scenarios
from app.core.config import settings
from app.core.database import init_db
from app.evals.runner import mark_interrupted_batches

logging.basicConfig(level=settings.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    mark_interrupted_batches()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AutonomePay — Autonomous Financial Concierge & Settlement Sentinel API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,  # no cookies are used
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Admin-Token"],
)

app.include_router(chat.router, prefix=settings.API_V1_STR, tags=["chat"])
app.include_router(scenarios.router, prefix=settings.API_V1_STR, tags=["scenarios"])
app.include_router(evals.router, prefix=settings.API_V1_STR, tags=["evals"])


@app.get("/")
def root():
    return {"status": "online", "project": settings.PROJECT_NAME, "docs": "/docs"}
