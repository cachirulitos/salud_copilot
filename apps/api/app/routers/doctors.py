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
        .join(Visit, Visit.id == VisitStep.visit_id)
        .where(
            VisitStep.clinical_area_id == doctor.clinical_area_id,
            VisitStep.status.in_([VisitStepStatus.PENDING, VisitStepStatus.IN_PROGRESS]),
        )
        .order_by(Visit.created_at.asc()) # Using Visit created_at to keep chronological order
    )
    all_potential_steps = list(steps_result.scalars().all())

    # Filter so a patient only appears in the doctor queue if this is ACTUALLY their current step
    steps = []
    incoming_steps = []
    for step in all_potential_steps:
        earlier_uncompleted = await db.execute(
            select(VisitStep).where(
                VisitStep.visit_id == step.visit_id,
                VisitStep.step_order < step.step_order,
                VisitStep.status != VisitStepStatus.COMPLETED
            ).order_by(VisitStep.step_order.asc())
        )
        first_earlier = earlier_uncompleted.first()
        if first_earlier is None:
            steps.append((step, True, None))
        else:
            earlier_step = first_earlier[0]
            area_res = await db.execute(select(ClinicalArea).where(ClinicalArea.id == earlier_step.clinical_area_id))
            area_obj = area_res.scalar_one_or_none()
            area_name = area_obj.name if area_obj else "Otra área"
            incoming_steps.append((step, False, area_name))

    # ── Automágico: Call the next patient automatically if idle ──
    # Only applies to 'current' steps
    actual_steps = [s for s, is_curr, _ in steps if is_curr]
    has_in_progress = any(s.status == VisitStepStatus.IN_PROGRESS for s in actual_steps)
    if not has_in_progress and actual_steps:
        # The doctor is completely free. Pop the first pending!
        first_pending = actual_steps[0]
        if first_pending.status == VisitStepStatus.PENDING:
            first_pending.status = VisitStepStatus.IN_PROGRESS
            first_pending.started_at = datetime.now(timezone.utc)
            await db.commit()
            # No need to refetch, object is updated in memory

    # Combine both groups
    all_steps = steps + incoming_steps

    # Count total steps per visit
    total_steps_result = await db.execute(
        select(VisitStep.visit_id, func.count(VisitStep.id).label("total"))
        .where(VisitStep.visit_id.in_([s[0].visit_id for s in all_steps]))
        .group_by(VisitStep.visit_id)
    )
    total_steps_map: dict[uuid.UUID, int] = {
        row.visit_id: row.total for row in total_steps_result
    }

    patients: list[DoctorPatientResponse] = []
    
    # Calculate Expected Consultation Time
    area_result = await db.execute(select(ClinicalArea).where(ClinicalArea.id == doctor.clinical_area_id))
    area = area_result.scalar_one()
    BASE_WAIT_TIMES = {
        "laboratorio": 15,
        "ultrasonido": 20,
        "rayos_x": 12,
        "electrocardiograma": 8,
        "papanicolaou": 10,
        "densitometria": 15,
        "tomografia": 25,
    }
    expected_consultation_minutes = BASE_WAIT_TIMES.get(area.study_type, 15)

    for step, is_curr, curr_area in all_steps:
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
                expected_consultation_minutes=expected_consultation_minutes,
                elapsed_minutes=elapsed,
                is_current=is_curr,
                current_area_name=curr_area,
            )
        )

    # Sort: In progress first, then current pending, then incoming patients
    patients.sort(key=lambda p: (
        0 if p.step_status == VisitStepStatus.IN_PROGRESS.value else 1,
        0 if p.is_current else 1
    ))

    return patients
