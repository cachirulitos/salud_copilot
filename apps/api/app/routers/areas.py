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
