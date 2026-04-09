import uuid
from datetime import datetime, timezone

import redis.asyncio as redis
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.models import ClinicalArea, WaitTimeEstimate
from app.schemas.schemas import WaitTimeEstimateResponse

router = APIRouter()

redis_client = redis.from_url(settings.redis_url)

DEFAULT_BASE_WAIT_MINUTES = 15


@router.get("/{area_id}/wait-time-estimate", response_model=WaitTimeEstimateResponse)
async def get_wait_time_estimate(
    area_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Returns the current wait time estimate for a clinical area."""

    result = await db.execute(
        select(ClinicalArea).where(ClinicalArea.id == area_id)
    )
    area = result.scalar_one_or_none()
    if area is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Area not found", "code": "AREA_NOT_FOUND"},
        )

    result = await db.execute(
        select(WaitTimeEstimate).where(
            WaitTimeEstimate.clinical_area_id == area_id
        )
    )
    wait_estimate = result.scalar_one_or_none()

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


from app.models.models import Clinic, ClinicalArea, DoctorAlert, AlertType, VisitStep, VisitStepStatus, WaitTimeEstimate, Visit, Patient

from app.schemas.schemas import (
    OccupancyUpdateRequest,
    OccupancyResponse,
    WaitTimeEstimateResponse,
    AreaQueueShift,
)

@router.get("/{area_id}/shifts", response_model=list[AreaQueueShift])
async def get_area_shifts(
    area_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Returns the public shift list for this area to display on a public screen."""
    
    # Find all pending/in_progress steps for this area
    steps_result = await db.execute(
        select(VisitStep)
        .join(Visit, Visit.id == VisitStep.visit_id)
        .where(
            VisitStep.clinical_area_id == area_id,
            VisitStep.status.in_([VisitStepStatus.PENDING, VisitStepStatus.IN_PROGRESS]),
        )
        .order_by(Visit.created_at.asc())
    )
    all_potential_steps = list(steps_result.scalars().all())

    # Filter to only keep steps that are actually current for the patient
    shifts: list[AreaQueueShift] = []
    
    for step in all_potential_steps:
        earlier_uncompleted = await db.execute(
            select(VisitStep).where(
                VisitStep.visit_id == step.visit_id,
                VisitStep.step_order < step.step_order,
                VisitStep.status != VisitStepStatus.COMPLETED
            ).order_by(VisitStep.step_order.asc())
        )
        # If there are earlier steps uncompleted, this patient is in another area
        if earlier_uncompleted.first() is not None:
            continue
            
        visit_result = await db.execute(select(Visit).where(Visit.id == step.visit_id))
        visit = visit_result.scalar_one_or_none()
        if not visit:
            continue
            
        patient_result = await db.execute(select(Patient).where(Patient.id == visit.patient_id))
        patient = patient_result.scalar_one_or_none()
        patient_name = patient.full_name if patient else "Desconocido"

        # Generate a short alphanumeric turn number resembling a bank slip
        # Using first letter of name + first 3 hex chars of UUID
        initial = patient_name[0].upper() if patient_name else "A"
        code = step.visit_id.hex[:3].upper()
        turn_number = f"{initial}-{code}"

        shifts.append(
            AreaQueueShift(
                visit_id=step.visit_id,
                turn_number=turn_number,
                patient_name=patient_name,
                status=step.status.value,
                step_order=step.step_order,
            )
        )

    # Sort in-progress to top
    shifts.sort(key=lambda s: 0 if s.status == VisitStepStatus.IN_PROGRESS.value else 1)

    return shifts

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
