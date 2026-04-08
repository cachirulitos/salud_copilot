"""
Notifications & Alerts endpoints:
  GET  /api/v1/notifications/alerts          — list DoctorAlerts for a clinic
  POST /api/v1/notifications/alerts/{id}/resolve  — mark alert resolved
  POST /api/v1/notifications/study-change    — notify doctors on study change
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_doctor_id
from app.models.models import ClinicalArea, Doctor, DoctorAlert, AlertType
from app.schemas.schemas import DoctorAlertResponse, StudyChangeNotification
from app.routers.dashboard_ws import broadcast_to_clinic

router = APIRouter()


# ── Alerts ────────────────────────────────────────────────────────────────────


@router.get(
    "/alerts",
    response_model=list[DoctorAlertResponse],
    summary="List recent alerts for a clinic (unresolved first)",
)
async def list_alerts(
    clinic_id: uuid.UUID = Query(..., description="UUID of the clinic"),
    resolved: Optional[bool] = Query(None, description="Filter by resolved status"),
    db: AsyncSession = Depends(get_db),
):
    q = select(DoctorAlert).where(DoctorAlert.clinic_id == clinic_id)
    if resolved is False:
        q = q.where(DoctorAlert.resolved_at.is_(None))
    elif resolved is True:
        q = q.where(DoctorAlert.resolved_at.is_not(None))
    q = q.order_by(DoctorAlert.triggered_at.desc()).limit(50)

    result = await db.execute(q)
    alerts = list(result.scalars().all())
    return [
        DoctorAlertResponse(
            id=a.id,
            clinic_id=a.clinic_id,
            area_id=a.area_id,
            visit_id=a.visit_id,
            alert_type=a.alert_type.value,
            message=a.message,
            triggered_at=a.triggered_at,
            resolved_at=a.resolved_at,
        )
        for a in alerts
    ]


@router.post(
    "/alerts/{alert_id}/resolve",
    response_model=DoctorAlertResponse,
    summary="Mark an alert as resolved",
)
async def resolve_alert(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _doctor_id: str = Depends(get_current_doctor_id),
):
    result = await db.execute(select(DoctorAlert).where(DoctorAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.resolved_at = datetime.now(timezone.utc)
    await db.flush()

    return DoctorAlertResponse(
        id=alert.id,
        clinic_id=alert.clinic_id,
        area_id=alert.area_id,
        visit_id=alert.visit_id,
        alert_type=alert.alert_type.value,
        message=alert.message,
        triggered_at=alert.triggered_at,
        resolved_at=alert.resolved_at,
    )


# ── Study-change notification ─────────────────────────────────────────────────


@router.post(
    "/study-change",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Notify doctors when the bot recommends a study change",
)
async def notify_study_change(
    payload: StudyChangeNotification,
    db: AsyncSession = Depends(get_db),
    _doctor_id: str = Depends(get_current_doctor_id),
):
    # Look up old area to find its doctor and clinic
    old_area_result = await db.execute(
        select(ClinicalArea).where(ClinicalArea.id == payload.old_area_id)
    )
    old_area = old_area_result.scalar_one_or_none()
    if old_area is None:
        raise HTTPException(status_code=404, detail="Old area not found")

    new_area_result = await db.execute(
        select(ClinicalArea).where(ClinicalArea.id == payload.new_area_id)
    )
    new_area = new_area_result.scalar_one_or_none()
    if new_area is None:
        raise HTTPException(status_code=404, detail="New area not found")

    clinic_id = str(old_area.clinic_id)

    # Broadcast to all dashboard clients of this clinic
    await broadcast_to_clinic(clinic_id, {
        "event": "study_change_notification",
        "data": {
            "visit_id": str(payload.visit_id),
            "requesting_doctor_id": str(payload.requesting_doctor_id),
            "old_area": old_area.name,
            "new_area": new_area.name,
            "reason": payload.reason,
        },
    })
