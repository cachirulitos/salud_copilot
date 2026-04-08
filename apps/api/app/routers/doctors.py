"""
Doctor endpoints:
  POST /api/v1/doctors/login         — authenticate and set JWT cookie
  POST /api/v1/doctors/logout        — clear JWT cookie
  GET  /api/v1/doctors/me/patients   — list active visits in the doctor's area
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import (
    verify_password,
    create_access_token,
    get_current_doctor_id,
)
from app.models.models import (
    ClinicalArea,
    Doctor,
    Patient,
    Visit,
    VisitStep,
    VisitStepStatus,
)
from app.schemas.schemas import (
    DoctorLoginRequest,
    DoctorLoginResponse,
    DoctorPatientResponse,
)

router = APIRouter()

COOKIE_NAME = "doctor_token"
COOKIE_MAX_AGE = 60 * 60 * 8  # 8 hours in seconds


# ── Auth ──────────────────────────────────────────────────────────────────────


@router.post(
    "/login",
    response_model=DoctorLoginResponse,
    summary="Doctor login — issues a JWT stored as an HttpOnly cookie",
)
async def doctor_login(
    request: DoctorLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Doctor).where(Doctor.employee_id == request.employee_id, Doctor.active.is_(True))
    )
    doctor = result.scalar_one_or_none()

    if doctor is None or not verify_password(request.password, doctor.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid employee ID or password",
        )

    area_result = await db.execute(
        select(ClinicalArea).where(ClinicalArea.id == doctor.clinical_area_id)
    )
    area = area_result.scalar_one()

    token = create_access_token(str(doctor.id))
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        secure=False,  # set to True in production (HTTPS)
    )

    return DoctorLoginResponse(
        doctor_id=doctor.id,
        full_name=doctor.full_name,
        clinical_area_id=doctor.clinical_area_id,
        clinical_area_name=area.name,
    )


@router.post("/logout", summary="Clear the doctor JWT cookie")
async def doctor_logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME)
    return {"status": "logged_out"}


# ── Patient list ──────────────────────────────────────────────────────────────


@router.get(
    "/me/patients",
    response_model=list[DoctorPatientResponse],
    summary="Get active patients in the authenticated doctor's area",
)
async def get_my_patients(
    doctor_id: str = Depends(get_current_doctor_id),
    db: AsyncSession = Depends(get_db),
):
    # Load doctor to get their area
    result = await db.execute(
        select(Doctor).where(Doctor.id == uuid.UUID(doctor_id))
    )
    doctor = result.scalar_one_or_none()
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # Find all visit steps in this area that are pending or in_progress
    steps_result = await db.execute(
        select(VisitStep)
        .where(
            VisitStep.clinical_area_id == doctor.clinical_area_id,
            VisitStep.status.in_([VisitStepStatus.PENDING, VisitStepStatus.IN_PROGRESS]),
        )
        .order_by(VisitStep.started_at.asc().nullslast())
    )
    steps = list(steps_result.scalars().all())

    # Count total steps per visit
    total_steps_result = await db.execute(
        select(VisitStep.visit_id, func.count(VisitStep.id).label("total"))
        .where(VisitStep.visit_id.in_([s.visit_id for s in steps]))
        .group_by(VisitStep.visit_id)
    )
    total_steps_map: dict[uuid.UUID, int] = {
        row.visit_id: row.total for row in total_steps_result
    }

    patients: list[DoctorPatientResponse] = []
    for step in steps:
        visit_result = await db.execute(select(Visit).where(Visit.id == step.visit_id))
        visit = visit_result.scalar_one_or_none()
        if visit is None:
            continue

        patient_result = await db.execute(
            select(Patient).where(Patient.id == visit.patient_id)
        )
        patient = patient_result.scalar_one_or_none()
        patient_name = patient.full_name if patient else "Desconocido"

        elapsed: Optional[int] = None
        if step.started_at:
            elapsed = int(
                (datetime.now(timezone.utc) - step.started_at).total_seconds() / 60
            )

        patients.append(
            DoctorPatientResponse(
                visit_id=step.visit_id,
                patient_name=patient_name,
                step_status=step.status.value,
                step_order=step.step_order,
                total_steps=total_steps_map.get(step.visit_id, 1),
                estimated_wait_minutes=step.estimated_wait_minutes,
                elapsed_minutes=elapsed,
            )
        )

    return patients
