from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.api import routes_chat, routes_scenarios, routes_evals

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AutonomePay — Autonomous Financial Concierge & Settlement Sentinel API",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(routes_chat.router, prefix=settings.API_V1_STR, tags=["chat"])
app.include_router(routes_scenarios.router, prefix=settings.API_V1_STR, tags=["scenarios"])
app.include_router(routes_evals.router, prefix=settings.API_V1_STR, tags=["evals"])

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/")
def root():
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "docs": "/docs"
    }
