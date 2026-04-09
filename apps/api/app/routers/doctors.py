"""
Doctor endpoints:
  POST /api/v1/doctors/login         — authenticate and set JWT cookie
  POST /api/v1/doctors/logout        — clear JWT cookie
  GET  /api/v1/doctors/me/patients   — list active visits in the doctor's area
"""
import uuid
from datetime import datetime, timezone, date
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, AsyncSessionLocal
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
from app.core.predictor_client import get_predictor
from app.schemas.schemas import (
    DoctorLoginRequest,
    DoctorLoginResponse,
    DoctorPatientResponse,
    StepDetail,
    CompletedPatientEntry,
    CompletedTodayResponse,
)

BASE_WAIT_TIMES = {
    "laboratorio": 15,
    "ultrasonido": 20,
    "rayos_x": 12,
    "electrocardiograma": 8,
    "papanicolaou": 10,
    "densitometria": 15,
    "tomografia": 25,
}


async def _auto_advance_commit(step_id: uuid.UUID) -> None:
    """Persist the auto-advance of a pending step to in_progress."""
    try:
        from app.routers.dashboard_ws import broadcast_to_clinic
        from app.models.models import Visit as VisitModel
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(VisitStep).where(VisitStep.id == step_id))
            step = result.scalar_one_or_none()
            if step and step.status == VisitStepStatus.PENDING:
                step.status = VisitStepStatus.IN_PROGRESS
                step.started_at = datetime.now(timezone.utc)
                await db.commit()
                # Fetch clinic_id for broadcast
                visit_result = await db.execute(select(VisitModel).where(VisitModel.id == step.visit_id))
                visit = visit_result.scalar_one_or_none()
                if visit:
                    await broadcast_to_clinic(str(visit.clinic_id), {
                        "event": "visit_step_updated",
                        "data": {
                            "visit_id": str(step.visit_id),
                            "ticket_number": visit.ticket_number or "",
                            "visit_status": "in_progress",
                            "completed_step": None,
                            "next_step": {
                                "order": step.step_order,
                                "area_id": str(step.clinical_area_id),
                                "area_name": None,
                                "status": "in_progress",
                            },
                        },
                    })
    except Exception:
        import logging
        logging.getLogger(__name__).exception("_auto_advance_commit error")


def _predict_consultation_minutes(
    area: ClinicalArea,
    visit: Visit,
    queue_length: int,
) -> int:
    """Return ML-predicted wait or fall back to BASE_WAIT_TIMES."""
    predictor = get_predictor()
    if predictor is not None:
        now = datetime.now(timezone.utc)
        try:
            return predictor.predict_wait_minutes(
                hour_of_day=now.hour,
                day_of_week=now.weekday(),
                study_type_raw_id=area.study_type,
                clinic_raw_id=str(area.clinic_id),
                simultaneous_capacity=area.simultaneous_capacity,
                current_queue_length=queue_length,
                has_appointment=visit.has_appointment,
            )
        except Exception:
            pass
    return BASE_WAIT_TIMES.get(area.study_type, 15)

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
        token=token,
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
    background_tasks: BackgroundTasks,
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
        .order_by(Visit.created_at.asc())
    )
    all_potential_steps = list(steps_result.scalars().all())

    if not all_potential_steps:
        return []

    # Batch-load all visit steps for these visits in one query to check blocking
    candidate_visit_ids = list({s.visit_id for s in all_potential_steps})
    all_visit_steps_result = await db.execute(
        select(VisitStep).where(VisitStep.visit_id.in_(candidate_visit_ids))
    )
    all_visit_steps_by_visit: dict[uuid.UUID, list[VisitStep]] = {}
    for vs in all_visit_steps_result.scalars().all():
        all_visit_steps_by_visit.setdefault(vs.visit_id, []).append(vs)

    # Filter so a patient only appears if this is ACTUALLY their current step
    steps = []
    for step in all_potential_steps:
        visit_steps = all_visit_steps_by_visit.get(step.visit_id, [])
        has_earlier_uncompleted = any(
            s.step_order < step.step_order and s.status != VisitStepStatus.COMPLETED
            for s in visit_steps
        )
        if not has_earlier_uncompleted:
            steps.append(step)

    # ── Automágico: Call the next patient automatically if idle ──
    has_in_progress = any(s.status == VisitStepStatus.IN_PROGRESS for s in steps)
    if not has_in_progress and steps:
        first_pending = steps[0]
        if first_pending.status == VisitStepStatus.PENDING:
            first_pending.status = VisitStepStatus.IN_PROGRESS
            first_pending.started_at = datetime.now(timezone.utc)
            # Commit in background so it doesn't block the response
            background_tasks.add_task(_auto_advance_commit, first_pending.id)


    # Count total steps per visit
    total_steps_result = await db.execute(
        select(VisitStep.visit_id, func.count(VisitStep.id).label("total"))
        .where(VisitStep.visit_id.in_([s.visit_id for s in steps]))
        .group_by(VisitStep.visit_id)
    )
    total_steps_map: dict[uuid.UUID, int] = {
        row.visit_id: row.total for row in total_steps_result
    }

    area_result = await db.execute(select(ClinicalArea).where(ClinicalArea.id == doctor.clinical_area_id))
    area = area_result.scalar_one()
    queue_length = len(steps)

    # Cache ML predictions (only varies by has_appointment for same area+queue)
    _prediction_cache: dict[bool, int] = {}

    all_areas_result = await db.execute(
        select(ClinicalArea).where(ClinicalArea.clinic_id == area.clinic_id)
    )
    area_name_map: dict[uuid.UUID, str] = {
        a.id: a.name for a in all_areas_result.scalars().all()
    }

    # Batch-load all visits and patients in 2 queries instead of 2N
    visit_ids = [s.visit_id for s in steps]
    visits_result = await db.execute(select(Visit).where(Visit.id.in_(visit_ids)))
    visit_map: dict[uuid.UUID, Visit] = {v.id: v for v in visits_result.scalars().all()}

    patient_ids = [v.patient_id for v in visit_map.values()]
    patients_result = await db.execute(select(Patient).where(Patient.id.in_(patient_ids)))
    patient_map: dict[uuid.UUID, Patient] = {p.id: p for p in patients_result.scalars().all()}

    patients: list[DoctorPatientResponse] = []

    for step in steps:
        visit = visit_map.get(step.visit_id)
        if visit is None:
            continue

        patient = patient_map.get(visit.patient_id)
        patient_name = patient.full_name if patient else "Desconocido"

        elapsed: Optional[int] = None
        if step.started_at:
            elapsed = int(
                (datetime.now(timezone.utc) - step.started_at).total_seconds() / 60
            )

        expected_consultation_minutes = step.estimated_wait_minutes or BASE_WAIT_TIMES.get(area.study_type, 15)

        # Use already-loaded visit steps (no extra query)
        all_steps = sorted(
            all_visit_steps_by_visit.get(step.visit_id, []),
            key=lambda s: s.step_order,
        )

        coming_from_area: Optional[str] = None
        next_area_after: Optional[str] = None

        prev_step = next((s for s in reversed(all_steps) if s.step_order < step.step_order and s.status == VisitStepStatus.COMPLETED), None)
        if prev_step:
            coming_from_area = area_name_map.get(prev_step.clinical_area_id)

        next_step_obj = next((s for s in all_steps if s.step_order > step.step_order and s.status == VisitStepStatus.PENDING), None)
        if next_step_obj:
            next_area_after = area_name_map.get(next_step_obj.clinical_area_id)

        step_details = [
            StepDetail(
                order=s.step_order,
                area_name=area_name_map.get(s.clinical_area_id, "Desconocida"),
                status=s.status.value,
                estimated_wait_minutes=s.estimated_wait_minutes,
                actual_wait_minutes=s.actual_wait_minutes,
            )
            for s in all_steps
        ]

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
                coming_from_area=coming_from_area,
                next_area_after=next_area_after,
                steps=step_details,
            )
        )

    # Ensure in-progress patient appears at the top
    patients.sort(key=lambda p: (0 if p.step_status == VisitStepStatus.IN_PROGRESS.value else 1))

    return patients


@router.get(
    "/me/completed-today",
    response_model=CompletedTodayResponse,
    summary="Get patients whose step in this doctor's area was completed today",
)
async def get_completed_today(
    doctor_id: str = Depends(get_current_doctor_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Doctor).where(Doctor.id == uuid.UUID(doctor_id)))
    doctor = result.scalar_one_or_none()
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")

    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)

    steps_result = await db.execute(
        select(VisitStep)
        .join(Visit, Visit.id == VisitStep.visit_id)
        .where(
            VisitStep.clinical_area_id == doctor.clinical_area_id,
            VisitStep.status == VisitStepStatus.COMPLETED,
            VisitStep.completed_at >= today_start,
        )
        .order_by(VisitStep.completed_at.desc())
    )
    completed_steps = list(steps_result.scalars().all())

    if not completed_steps:
        return CompletedTodayResponse(count=0, patients=[])

    visit_ids = list({s.visit_id for s in completed_steps})

    # Batch load visits, patients, and step counts
    visits_res = await db.execute(select(Visit).where(Visit.id.in_(visit_ids)))
    visit_map = {v.id: v for v in visits_res.scalars().all()}

    patient_ids = [v.patient_id for v in visit_map.values()]
    patients_res = await db.execute(select(Patient).where(Patient.id.in_(patient_ids)))
    patient_map = {p.id: p for p in patients_res.scalars().all()}

    totals_res = await db.execute(
        select(VisitStep.visit_id, func.count(VisitStep.id).label("total"))
        .where(VisitStep.visit_id.in_(visit_ids))
        .group_by(VisitStep.visit_id)
    )
    totals_map = {row.visit_id: row.total for row in totals_res}

    entries: list[CompletedPatientEntry] = []
    for s in completed_steps:
        visit = visit_map.get(s.visit_id)
        if not visit:
            continue
        patient = patient_map.get(visit.patient_id)
        entries.append(CompletedPatientEntry(
            visit_id=s.visit_id,
            patient_name=patient.full_name if patient else "Desconocido",
            completed_at=s.completed_at,
            total_steps=totals_map.get(s.visit_id, 1),
        ))

    return CompletedTodayResponse(count=len(entries), patients=entries)
