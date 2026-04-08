import uuid
from datetime import datetime, timezone

import redis.asyncio as redis
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.predictor_client import get_predictor
from app.models.models import Clinic, ClinicalArea, DoctorAlert, AlertType, VisitStep, VisitStepStatus, WaitTimeEstimate
from app.routers.dashboard_ws import broadcast_to_clinic
from app.schemas.schemas import (
    OccupancyUpdateRequest,
    OccupancyResponse,
    WaitTimeEstimateResponse,
)

router = APIRouter()

redis_client = redis.from_url(settings.redis_url)

OCCUPANCY_TTL_SECONDS = 30

# Fallback formula used when ML predictor is not available
BASE_WAIT_TIMES = {
    "laboratorio": 15,
    "ultrasonido": 20,
    "rayos_x": 12,
    "electrocardiograma": 8,
    "papanicolaou": 10,
    "densitometria": 15,
    "tomografia": 25,
}

WAIT_MINUTES_PER_PERSON = 3
WAIT_MINUTES_PER_QUEUED = 5
DEFAULT_BASE_WAIT_MINUTES = 15


@router.post("/{area_id}/occupancy", response_model=OccupancyResponse)
async def update_occupancy(
    area_id: uuid.UUID,
    request: OccupancyUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Receive people count from CV worker and update wait time estimate."""

    # 1. Find ClinicalArea
    result = await db.execute(
        select(ClinicalArea).where(ClinicalArea.id == area_id)
    )
    area = result.scalar_one_or_none()
    if area is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Area not found", "code": "AREA_NOT_FOUND"},
        )

    # 2. Store occupancy in Redis with TTL
    await redis_client.set(
        f"occupancy:{area_id}", request.people_count, ex=OCCUPANCY_TTL_SECONDS
    )

    # 3. Get queue length from Redis
    queue_length = await redis_client.zcard(f"queue:{area_id}")

    # 4. Calculate estimated wait via ML model, fallback to formula if unavailable
    now = datetime.now()
    predictor = get_predictor()
    if predictor is not None:
        clinic_result = await db.execute(select(Clinic).where(Clinic.id == area.clinic_id))
        clinic = clinic_result.scalar_one_or_none()
        historical_clinic_id = clinic.historical_ml_id if clinic and clinic.historical_ml_id else None

        if historical_clinic_id is not None:
            base_ml_estimate = predictor.predict_wait_minutes(
                hour_of_day=now.hour,
                day_of_week=now.weekday(),
                study_type_raw_id=area.study_type,
                clinic_raw_id=historical_clinic_id,
                simultaneous_capacity=area.simultaneous_capacity,
                current_queue_length=queue_length,
                has_appointment=False,
            )
            estimated_minutes = (
                base_ml_estimate
                + (request.people_count * WAIT_MINUTES_PER_PERSON)
            )
            print(f"ML Base: {base_ml_estimate} | Total con {request.people_count} personas: {estimated_minutes}")
        else:
            # No ML mapping for this clinic — use formula
            base = BASE_WAIT_TIMES.get(area.study_type, DEFAULT_BASE_WAIT_MINUTES)
            estimated_minutes = (
                base
                + (request.people_count * WAIT_MINUTES_PER_PERSON)
                + (queue_length * WAIT_MINUTES_PER_QUEUED)
            )
    else:
        base = BASE_WAIT_TIMES.get(area.study_type, DEFAULT_BASE_WAIT_MINUTES)
        estimated_minutes = (
            base
            + (request.people_count * WAIT_MINUTES_PER_PERSON)
            + (queue_length * WAIT_MINUTES_PER_QUEUED)
        )

    # 5. Upsert WaitTimeEstimate
    result = await db.execute(
        select(WaitTimeEstimate).where(
            WaitTimeEstimate.clinical_area_id == area_id
        )
    )
    wait_estimate = result.scalar_one_or_none()

    if wait_estimate is not None:
        wait_estimate.estimated_minutes = estimated_minutes
        wait_estimate.people_in_area = request.people_count
        wait_estimate.updated_at = datetime.now(timezone.utc)
    else:
        wait_estimate = WaitTimeEstimate(
            clinical_area_id=area_id,
            estimated_minutes=estimated_minutes,
            people_in_area=request.people_count,
        )
        db.add(wait_estimate)

    # 6. Check for overtime on any in-progress step in this area
    in_progress_result = await db.execute(
        select(VisitStep).where(
            VisitStep.clinical_area_id == area_id,
            VisitStep.status == VisitStepStatus.IN_PROGRESS,
        )
    )
    for step in in_progress_result.scalars().all():
        if step.started_at and step.estimated_wait_minutes:
            elapsed_min = int(
                (datetime.now(timezone.utc) - step.started_at).total_seconds() / 60
            )
            overtime_threshold = step.estimated_wait_minutes + 5
            if elapsed_min > overtime_threshold:
                # Deduplicate: skip if an unresolved alert for this visit already exists
                existing_result = await db.execute(
                    select(DoctorAlert).where(
                        DoctorAlert.visit_id == step.visit_id,
                        DoctorAlert.area_id == area_id,
                        DoctorAlert.alert_type == AlertType.OVERTIME,
                        DoctorAlert.resolved_at.is_(None),
                    )
                )
                if existing_result.scalar_one_or_none() is None:
                    overtime_alert = DoctorAlert(
                        clinic_id=area.clinic_id,
                        area_id=area_id,
                        visit_id=step.visit_id,
                        alert_type=AlertType.OVERTIME,
                        message=(
                            f"Consulta lleva {elapsed_min} min "
                            f"(estimado: {step.estimated_wait_minutes} min) "
                            f"en {area.name}"
                        ),
                    )
                    db.add(overtime_alert)
                    await db.flush()
                    await broadcast_to_clinic(
                        str(area.clinic_id),
                        {
                            "event": "alert",
                            "data": {
                                "alert_type": "overtime",
                                "area_name": area.name,
                                "visit_id": str(step.visit_id),
                                "elapsed_minutes": elapsed_min,
                                "estimated_minutes": step.estimated_wait_minutes,
                                "message": overtime_alert.message,
                            },
                        },
                    )

    # 7. Broadcast wait time update to dashboard
    await broadcast_to_clinic(
        str(area.clinic_id),
        {
            "event": "wait_time_updated",
            "data": {
                "estimated_minutes": estimated_minutes,
                "people_count": request.people_count,
            },
        },
    )

    # 8. Return response
    return OccupancyResponse(wait_time_estimate_minutes=estimated_minutes)


@router.get("/{area_id}/wait-time-estimate", response_model=WaitTimeEstimateResponse)
async def get_wait_time_estimate(
    area_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Returns the current wait time estimate for a clinical area."""

    # 1. Find ClinicalArea
    result = await db.execute(
        select(ClinicalArea).where(ClinicalArea.id == area_id)
    )
    area = result.scalar_one_or_none()
    if area is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Area not found", "code": "AREA_NOT_FOUND"},
        )

    # 2. Find WaitTimeEstimate
    result = await db.execute(
        select(WaitTimeEstimate).where(
            WaitTimeEstimate.clinical_area_id == area_id
        )
    )
    wait_estimate = result.scalar_one_or_none()

    # 3. Get queue length from Redis
    queue_length = await redis_client.zcard(f"queue:{area_id}")

    if wait_estimate is None:
        return WaitTimeEstimateResponse(
            area_id=area_id,
            estimated_wait_minutes=DEFAULT_BASE_WAIT_MINUTES,
            current_queue_length=queue_length,
            people_in_area=0,
            updated_at=datetime.now(timezone.utc),
        )

    return WaitTimeEstimateResponse(
        area_id=area_id,
        estimated_wait_minutes=wait_estimate.estimated_minutes,
        current_queue_length=queue_length,
        people_in_area=wait_estimate.people_in_area,
        updated_at=wait_estimate.updated_at,
    )


@router.get("/")
async def list_areas(
    clinic_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Returns all active clinical areas for a clinic."""

    result = await db.execute(
        select(ClinicalArea).where(
            ClinicalArea.clinic_id == clinic_id,
            ClinicalArea.active == True,
        )
    )
    areas = result.scalars().all()

    return [
        {
            "id": area.id,
            "name": area.name,
            "study_type": area.study_type,
        }
        for area in areas
    ]
