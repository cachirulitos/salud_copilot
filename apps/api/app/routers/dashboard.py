import logging
import uuid
import random
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import redis.asyncio as redis

from app.core.config import settings
from app.core.database import get_db
from app.models.models import (
    ClinicalArea,
    WaitTimeEstimate,
    Visit,
    VisitStep,
    Patient,
    VisitStepStatus,
    VisitStatus
)

redis_client = redis.from_url(settings.redis_url)

router = APIRouter()
logger = logging.getLogger(__name__)


async def _get_overview_data(clinic_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    # 1. Total areas, wait times
    areas_result = await db.execute(
        select(ClinicalArea)
        .where(ClinicalArea.clinic_id == clinic_id, ClinicalArea.active == True)
    )
    areas = areas_result.scalars().all()
    
    area_stats = []
    for area in areas:
        wt_result = await db.execute(
            select(WaitTimeEstimate).where(WaitTimeEstimate.clinical_area_id == area.id)
        )
        wt = wt_result.scalar_one_or_none()
        
        queue_length = await redis_client.zcard(f"queue:{area.id}")
        
        est_wait = wt.estimated_minutes if wt else 15
        
        area_stats.append({
            "area_id": str(area.id),
            "area_name": area.name,
            "current_queue_length": queue_length,
            "estimated_wait_minutes": est_wait,
            "people_in_area": wt.people_in_area if wt else 0,
            "status": "normal" if est_wait < 20 else "warning" if est_wait < 30 else "saturated"
        })
        
    # Active visits
    visits_result = await db.execute(
        select(Visit)
        .options(
            selectinload(Visit.patient),
            selectinload(Visit.visit_steps)
        )
        .where(Visit.clinic_id == clinic_id, Visit.status.in_([VisitStatus.PENDING, VisitStatus.IN_PROGRESS]))
    )
    active_visits = visits_result.scalars().all()
    
    visit_stats = []
    total_waiting = 0
    for visit in active_visits:
        current_step = next((s for s in visit.visit_steps if s.status != VisitStepStatus.COMPLETED), None)
        if not current_step and visit.visit_steps:
             current_step = visit.visit_steps[-1]
             
        if current_step:
            area_name = next((a.name for a in areas if a.id == current_step.clinical_area_id), "Desconocida")
            wait_time = 0
            if current_step.started_at:
                wait_time = int((datetime.now(timezone.utc) - current_step.started_at).total_seconds() / 60)
            
            if current_step.status == VisitStepStatus.PENDING:
                total_waiting += 1
                
            visit_stats.append({
                "visit_id": str(visit.id),
                "patient_name": visit.patient.full_name,
                "current_area": area_name,
                "step_order": current_step.step_order,
                "total_steps": len(visit.visit_steps),
                "status": current_step.status.value,
                "waiting_since_minutes": wait_time
            })
            
    summary = {
        "total_active_visits": len(visit_stats),
        "total_waiting_patients": total_waiting,
        "average_wait_minutes": int(sum(v["waiting_since_minutes"] for v in visit_stats) / len(visit_stats)) if visit_stats else 0,
        "areas_at_risk": sum(1 for a in area_stats if a["status"] in ["warning", "saturated"])
    }
    
    # Mock alerts
    alerts = []
    for a in area_stats:
        if a["status"] == "saturated":
            alerts.append({
                "id": f"alert-{uuid.uuid4()}",
                "severity": "critical",
                "area_name": a["area_name"],
                "message": f"Cola de {a['current_queue_length']} pacientes. Capacidad máxima alcanzada.",
                "triggered_at": datetime.now(timezone.utc).isoformat()
            })
        elif a["status"] == "warning":
            alerts.append({
                "id": f"alert-{uuid.uuid4()}",
                "severity": "warning",
                "area_name": a["area_name"],
                "message": f"Espera estimada supera 20 minutos.",
                "triggered_at": datetime.now(timezone.utc).isoformat()
            })
            
    return {
        "summary": summary,
        "areas": area_stats,
        "active_visits": visit_stats,
        "alerts": alerts
    }


@router.get("/{clinic_id}/overview")
async def get_dashboard_overview(clinic_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Returns the full consolidated dashboard overview state."""
    return await _get_overview_data(clinic_id, db)


@router.get("/{clinic_id}/history")
async def get_dashboard_history(clinic_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Returns simulated historical wait times for the last 60 minutes based on current data.
    Generates 12 data points (1 every 5 minutes).
    """
    areas_result = await db.execute(
        select(ClinicalArea).where(ClinicalArea.clinic_id == clinic_id, ClinicalArea.active == True)
    )
    areas = areas_result.scalars().all()
    
    labels = ["55m", "50m", "45m", "40m", "35m", "30m", "25m", "20m", "15m", "10m", "5m", "ahora"]
    series = {}
    
    for area in areas:
        wt_result = await db.execute(
            select(WaitTimeEstimate).where(WaitTimeEstimate.clinical_area_id == area.id)
        )
        wt = wt_result.scalar_one_or_none()
        current_val = wt.estimated_minutes if wt else 15
        
        # Simulate history: slowly converge to current wait time with some noise
        history = []
        val = max(5, current_val + random.randint(-5, 5))
        for _ in range(11):
            history.append(val)
            # random walk towards current_val
            step = 1 if current_val > val else -1 if current_val < val else 0
            val += step + random.choice([-1, 0, 1])
            val = max(2, val)
        
        history.append(current_val)
        series[area.name] = history
        
    return {
        "labels": labels,
        "series": series
    }

