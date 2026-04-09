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
    # Eagerly load ML predictor and warm it with a dummy prediction
    from app.core.predictor_client import get_predictor
    predictor = get_predictor()
    if predictor is not None:
        try:
            predictor.predict_wait_minutes(
                hour_of_day=12, day_of_week=2, study_type_raw_id="warmup",
                clinic_raw_id="warmup", simultaneous_capacity=1,
                current_queue_length=1, has_appointment=False,
            )
        except Exception:
            pass  # warmup failed, no big deal — model will load on first real call
    from app.services.step_monitor_service import run_step_monitor
    asyncio.create_task(run_step_monitor(interval_seconds=60))
    from app.services.retraining_service import run_retraining_monitor
    asyncio.create_task(run_retraining_monitor())
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
