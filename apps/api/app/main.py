"""
SaludCopilot API — Main entry point
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.routers import visits, admin, areas, patients, visit_steps, notifications, dashboard, dashboard_ws, doctors

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Eagerly load ML predictor so the success/fail log appears at startup
    from app.core.predictor_client import get_predictor
    get_predictor()
    from app.services.step_monitor_service import run_step_monitor
    asyncio.create_task(run_step_monitor(interval_seconds=60))
    yield


app = FastAPI(
    title="SaludCopilot API",
    description="Clinical orchestration engine for Salud Digna",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if True else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_allowed_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(patients.router,      prefix="/api/v1/patients",      tags=["Patients"])
app.include_router(visits.router,        prefix="/api/v1/visits",        tags=["Visits"])
app.include_router(areas.router,         prefix="/api/v1/areas",         tags=["Areas"])
app.include_router(visit_steps.router,   prefix="/api/v1/visit-steps",   tags=["Visit Steps"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])
app.include_router(dashboard.router,     prefix="/api/v1/dashboard",     tags=["Dashboard"])
app.include_router(admin.router,         prefix="/api/v1/admin",         tags=["Admin"])
app.include_router(doctors.router,       prefix="/api/v1/doctors",       tags=["Doctors"])
app.include_router(dashboard_ws.router,  prefix="/ws/dashboard",         tags=["Dashboard WebSocket"])


@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "version": "0.1.0"}
