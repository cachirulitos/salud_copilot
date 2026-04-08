"""
POST /api/v1/visits/check-in
GET  /api/v1/visits/{visit_id}/context
POST /api/v1/visits/{visit_id}/advance-step
"""

import uuid
import sys
from datetime import datetime, timezone
from pathlib import Path

import redis.asyncio as redis
from fastapi import APIRouter, Depends, status, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.routers.dashboard_ws import broadcast_checkin_created, broadcast_visit_step_updated
from app.services.notification_service import trigger_bot_notification
from app.models.models import (
    Clinic,
    ClinicalArea,
    Patient,
    PatientEvent,
    Visit,
    VisitStatus,
    VisitStep,
    VisitStepStatus,
    WaitTimeEstimate,
)
from app.schemas.schemas import (
    AdvanceStepResponse,
    AdvanceStepStepResponse,
    CheckInRequest,
    CheckInResponse,
    ExamPayloadItem,
    ReorderSequenceRequest,
    ReorderSequenceResponse,
    RulesEngineValidationPayload,
    SequenceStepResponse,
    VisitContextResponse,
    VisitContextStepResponse,
)

from app.core.config import ROOT_DIR
sys.path.append(str(ROOT_DIR))

from packages.rules_engine.src.rules_engine.engine import Study, calculate_sequence
from app.services.sequence_validation_service import validate_proposed_sequence
from app.core.exceptions import SequenceRuleViolationError
from app.services.reorder_sequence_service import (
    reorder_visit_sequence,
    _VisitNotFoundError,
    _VisitNotReorderableError,
    _SequenceUUIDMismatchError,
)

router = APIRouter()

# Placeholder until the ML model is integrated (Task 7 of api TASK.md)
PLACEHOLDER_WAIT_MINUTES = 15
FASTING_STUDY_TYPE = "laboratorio"
DEFAULT_PATIENT_NAME_PREFIX = "Paciente "

redis_client = redis.from_url(settings.redis_url)



# ── Helpers ─────────────────────────────────────────────────────────────────


@router.post(
    "/check-in",
    response_model=CheckInResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a patient visit and calculate the study sequence",
)
async def check_in(request: CheckInRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """
    Registers a patient visit (walk-in or appointment) and returns the
    optimal study sequence calculated by the clinical rules engine.

    Steps:
    1. Find or create Patient by phone_number.
    2. Create Visit.
    3. Validate all study_ids map to existing ClinicalArea rows.
    4. Build Study objects for the rules engine.
    5. Run calculate_sequence().
    6. Persist VisitStep rows for each sequence step.
    7. Record arrival PatientEvent.
    8. Push visit_id to Redis queue for the first area.
    9. Return 201 with CheckInResponse.
    """

    # ── Step 1: find or create patient ───────────────────────────────────
    result = await db.execute(
        select(Patient).where(Patient.phone_number == request.phone_number)
    )
    patient = result.scalar_one_or_none()
    if patient is None:
        patient = Patient(
            phone_number=request.phone_number,
            full_name=DEFAULT_PATIENT_NAME_PREFIX + request.phone_number[-4:],
        )
        db.add(patient)
        await db.flush()  # assigns patient.id before FK use

    # ── Step 2: create visit ──────────────────────────────────────────────
    visit = Visit(
        patient_id=patient.id,
        clinic_id=request.clinic_id,
        status=VisitStatus.PENDING,
        has_appointment=request.has_appointment,
        is_urgent=request.is_urgent,
    )
    db.add(visit)
    await db.flush()  # assigns visit.id before FK use

    # ── Step 3: resolve study_ids → ClinicalArea rows ────────────────────
    areas: list[ClinicalArea] = []
    for study_id in request.study_ids:
        result = await db.execute(
            select(ClinicalArea).where(ClinicalArea.id == study_id)
        )
        area = result.scalar_one_or_none()
        if area is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "Area not found", "code": "AREA_NOT_FOUND"},
            )
        areas.append(area)

    # ── Step 4: build Study objects for the rules engine ─────────────────
    # `type` matches Study.type (renamed from study_type in engine.py)
    studies = [
        Study(
            id=str(area.id),
            type=area.study_type,
            requires_fasting=(area.study_type == "laboratorio"),
            is_urgent=request.is_urgent,
            has_appointment=request.has_appointment,
        )
        for area in areas
    ]

    # ── Step 5: calculate optimal sequence ───────────────────────────────
    area_by_id: dict[str, ClinicalArea] = {str(area.id): area for area in areas}

    if request.proposed_sequence:
        # Validate that proposed_sequence contains exactly the same area UUIDs
        provided_set = set(str(u) for u in request.proposed_sequence)
        requested_set = set(str(u) for u in request.study_ids)
        if provided_set != requested_set:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "error": "proposed_sequence must contain exactly the same UUIDs as study_ids.",
                    "code": "SEQUENCE_UUID_MISMATCH",
                },
            )

        # Delegate validation to the service layer
        try:
            validate_proposed_sequence(
                payload=RulesEngineValidationPayload(
                    exams=[
                        ExamPayloadItem(
                            area_id=uid,
                            study_type=area_by_id[str(uid)].study_type,
                            requires_fasting=(
                                area_by_id[str(uid)].study_type == FASTING_STUDY_TYPE
                            ),
                            is_urgent=request.is_urgent,
                            has_appointment=request.has_appointment,
                            proposed_order=idx + 1,
                        )
                        for idx, uid in enumerate(request.proposed_sequence)
                    ]
                ),
                is_urgent=request.is_urgent,
                has_appointment=request.has_appointment,
            )
        except SequenceRuleViolationError as exc:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "error": "The proposed sequence violates one or more clinical rules.",
                    "code": exc.code,
                    "rules_violations": exc.violations,
                },
            )

        # Build the ordered override list for step persistence
        sequence_result_steps_override = [
            (
                Study(
                    id=str(uid),
                    type=area_by_id[str(uid)].study_type,
                    requires_fasting=(
                        area_by_id[str(uid)].study_type == FASTING_STUDY_TYPE
                    ),
                    is_urgent=request.is_urgent,
                    has_appointment=request.has_appointment,
                ),
                str(uid),
            )
            for uid in request.proposed_sequence
        ]
    else:
        sequence_result_steps_override = None

    studies = [
        Study(
            id=str(area.id),
            type=area.study_type,
            requires_fasting=(area.study_type == FASTING_STUDY_TYPE),
            is_urgent=request.is_urgent,
            has_appointment=request.has_appointment,
        )
        for area in areas
    ]

    sequence_result = calculate_sequence(studies)

    # ── Steps 6: persist VisitStep rows ──────────────────────────────────
    area_by_id: dict[str, ClinicalArea] = {str(area.id): area for area in areas}
    sequence_response: list[SequenceStepResponse] = []

    from app.core.predictor_client import get_predictor

    # If the caller provided a valid proposed_sequence, build steps in that order;
    # otherwise use the engine-calculated sequence.
    if sequence_result_steps_override:
        steps_to_process = [
            (idx + 1, area_by_id[area_id_str])
            for idx, (_, area_id_str) in enumerate(sequence_result_steps_override)
        ]
    else:
        steps_to_process = [
            (step.order, area_by_id[step.study.id])
            for step in sequence_result.steps
        ]
        
    for step_order, area in steps_to_process:
        # Priority 1: Predict fresh ML stats natively
        wait_estimate_result = await db.execute(
            select(WaitTimeEstimate).where(WaitTimeEstimate.clinical_area_id == area.id)
        )
        wait_estimate = wait_estimate_result.scalar_one_or_none()
        people_in_area = wait_estimate.people_in_area if wait_estimate else 0
        print(f"People in area: {people_in_area}", flush=True)

        now = datetime.now()
        queue_length = await redis_client.zcard(f"queue:{area.id}")
        print(f"Queue length: {queue_length}", flush=True)
       
        # ── Weighted Queue (Media Ponderada) ──
        if people_in_area >= 4:
            effective_queue = int(round((queue_length * 0.95) + (people_in_area * 0.05)))
        else:
            effective_queue = int(round((queue_length * 0.75) + (people_in_area * 0.25)))
        print(f"Effective queue: {effective_queue}", flush=True)
        
        predictor = get_predictor()
        estimated_mins = None

        if predictor:
            clinic_result = await db.execute(
                select(Clinic).where(Clinic.id == area.clinic_id)
            )
            clinic = clinic_result.scalar_one_or_none()
            historical_clinic_id = clinic.historical_ml_id if clinic and clinic.historical_ml_id else None
            
            if historical_clinic_id is not None:
                base_ml_estimate = predictor.predict_wait_minutes(
                    hour_of_day=now.hour,
                    day_of_week=now.weekday(),
                    study_type_raw_id=area.study_type,
                    clinic_raw_id=historical_clinic_id,
                    simultaneous_capacity=area.simultaneous_capacity,
                    current_queue_length=effective_queue,
                    has_appointment=request.has_appointment,
                )
                print(f"ML Base: {base_ml_estimate}", flush=True)
                estimated_mins = base_ml_estimate
        
        # Priority 2: Formulas fallback
        if estimated_mins is None:
            if wait_estimate:
                estimated_mins = wait_estimate.estimated_minutes
            else:
                base = 15
                estimated_mins = base + (effective_queue * 4)

        db.add(VisitStep(
            visit_id=visit.id,
            clinical_area_id=area.id,
            step_order=step_order,
            status=VisitStepStatus.PENDING,
            rule_applied=None,
            estimated_wait_minutes=int(estimated_mins),
        ))
        sequence_response.append(SequenceStepResponse(
            order=step_order,
            area_id=area.id,
            area_name=area.name,
            estimated_wait_minutes=int(estimated_mins),
            rule_applied=None,
        ))

    # ── Step 7: record arrival event ──────────────────────────────────────
    db.add(
        PatientEvent(
            visit_id=visit.id,
            event_type="arrival",
            event_metadata={},
        )
    )

    # ── Step 8: push to Redis queue for first area ────────────────────────
    if sequence_result.steps:
        await _enqueue_first_area(visit.id, sequence_result.steps[0].study.id)

    # ── Step 9: flush remaining inserts and return ────────────────────────
    await db.commit()

    response = CheckInResponse(
        visit_id=visit.id,
        patient_id=patient.id,
        sequence=sequence_response,
        total_estimated_minutes=sequence_result.estimated_time_minutes,
    )
    background_tasks.add_task(
        broadcast_checkin_created,
        clinic_id=str(request.clinic_id),
        visit_id=visit.id,
        patient_id=patient.id,
        sequence_response=sequence_response,
        total_estimated_minutes=sequence_result.estimated_time_minutes,
        patient_name=patient.full_name,
    )
    background_tasks.add_task(
        trigger_bot_notification,
        visit_id=str(visit.id),
        notification_type="welcome",
        payload=response.model_dump(mode="json"),
    )
    return response


@router.get(
    "/{visit_id}/context",
    response_model=VisitContextResponse,
    summary="Get current visit context for bot or dashboard",
)
async def get_visit_context(
    visit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the current state of a visit.
    Used by the bot to build WhatsApp messages and by the dashboard.
    """

    # 1. Find visit
    result = await db.execute(select(Visit).where(Visit.id == visit_id))
    visit = result.scalar_one_or_none()
    if visit is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Visit not found", "code": "VISIT_NOT_FOUND"},
        )

    # 2. Load patient
    result = await db.execute(select(Patient).where(Patient.id == visit.patient_id))
    patient = result.scalar_one()

    # 3. Load all steps ordered
    result = await db.execute(
        select(VisitStep)
        .where(VisitStep.visit_id == visit_id)
        .order_by(VisitStep.step_order)
    )
    visit_steps = list(result.scalars().all())
    if not visit_steps:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Visit has no steps", "code": "NO_STEPS_FOUND"},
        )

    # 4. Current step = first non-completed; fallback to last
    current_step = next(
        (s for s in visit_steps if s.status != VisitStepStatus.COMPLETED),
        visit_steps[-1],
    )

    # 5. Live wait time from WaitTimeEstimate if available
    result = await db.execute(
        select(WaitTimeEstimate).where(
            WaitTimeEstimate.clinical_area_id == current_step.clinical_area_id
        )
    )
    wait_estimate = result.scalar_one_or_none()
    current_wait_minutes = (
        wait_estimate.estimated_minutes
        if wait_estimate is not None
        else current_step.estimated_wait_minutes
    )

    # 6. Area name for current step
    result = await db.execute(
        select(ClinicalArea).where(ClinicalArea.id == current_step.clinical_area_id)
    )
    current_area = result.scalar_one()

    # 6.5 Queue position for the first step
    if current_step.status != VisitStepStatus.IN_PROGRESS:
        position = await redis_client.zrank(
            f"queue:{current_step.clinical_area_id}", str(visit.id)
        )
    else:
        position = None

    current_step_response = VisitContextStepResponse(
        order=current_step.step_order,
        area_id=current_step.clinical_area_id,
        area_name=current_area.name,
        status=current_step.status.value,
        estimated_wait_minutes=current_wait_minutes,
        rule_applied=current_step.rule_applied,
        position_in_queue=position,
    )

    # 7. Remaining steps (pending, excluding current)
    remaining_steps_response: list[VisitContextStepResponse] = []
    for step in visit_steps:
        if step.status == VisitStepStatus.PENDING and step.id != current_step.id:
            area = await _load_area_by_id(step.clinical_area_id, db)
            remaining_steps_response.append(VisitContextStepResponse(
                order=step.step_order,
                area_id=step.clinical_area_id,
                area_name=area.name,
                status=step.status.value,
                estimated_wait_minutes=step.estimated_wait_minutes,
                rule_applied=step.rule_applied,
            ))

    total_estimated_minutes = current_wait_minutes + sum(
        s.estimated_wait_minutes for s in remaining_steps_response
    )

    return VisitContextResponse(
        visit_id=visit.id,
        patient_name=patient.full_name,
        current_step=current_step_response,
        remaining_steps=remaining_steps_response,
        total_estimated_minutes=total_estimated_minutes,
    )


@router.post("/{visit_id}/advance-step", response_model=AdvanceStepResponse)
async def advance_step(
    visit_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Advance the current visit step to completed and start the next one."""
    result = await db.execute(select(Visit).where(Visit.id == visit_id))
    visit = result.scalar_one_or_none()
    if visit is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Visit not found", "code": "VISIT_NOT_FOUND"},
        )

    current_step = await _find_visit_step_by_status(visit_id, VisitStepStatus.IN_PROGRESS, db)
    if current_step is None:
        current_step = await _find_visit_step_by_status(visit_id, VisitStepStatus.PENDING, db)
    if current_step is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "No steps to advance", "code": "NO_STEPS"},
        )

    actual_wait_minutes = await _complete_current_step(current_step)
    current_area = await _load_area_by_id(current_step.clinical_area_id, db)

    db.add(PatientEvent(
        visit_id=visit.id,
        event_type="step_completed",
        event_metadata={"area": current_area.name, "actual_wait": actual_wait_minutes},
    ))

    next_step = await _find_visit_step_by_status(visit_id, VisitStepStatus.PENDING, db)
    completed_step_response = AdvanceStepStepResponse(
        order=current_step.step_order,
        area_name=current_area.name,
        status="completed",
        actual_wait_minutes=actual_wait_minutes,
    )
    next_step_response = None

    if next_step is not None:
        await _start_next_step(next_step, current_step.clinical_area_id, visit.id)
        next_area = await _load_area_by_id(next_step.clinical_area_id, db)
        next_step_response = AdvanceStepStepResponse(
            order=next_step.step_order,
            area_name=next_area.name,
            status="pending",
        )
        position = await redis_client.zrank(
            f"queue:{next_step.clinical_area_id}", str(visit.id)
        )
        background_tasks.add_task(
            trigger_bot_notification,
            visit_id=str(visit.id),
            notification_type="turn_ready",
            payload={
                "area_name": next_area.name,
                "estimated_wait_minutes": next_step.estimated_wait_minutes or PLACEHOLDER_WAIT_MINUTES,
                "position_in_queue": position if position is not None else 0,
            },
        )
    else:
        await _finish_visit(visit, current_step.clinical_area_id, db)

    await db.flush()

    broadcast_area_name = next_step_response.area_name if next_step_response else current_area.name
    background_tasks.add_task(
        broadcast_visit_step_updated,
        clinic_id=str(visit.clinic_id),
        visit_id=visit.id,
        visit_status=visit.status.value,
        completed_step={
            "order": completed_step_response.order,
            "area_name": completed_step_response.area_name,
            "actual_wait_minutes": completed_step_response.actual_wait_minutes,
        },
        next_step={
            "order": next_step_response.order,
            "area_name": next_step_response.area_name,
            "estimated_wait_minutes": next_step.estimated_wait_minutes,
        } if next_step_response else None,
    )

    return AdvanceStepResponse(
        visit_id=visit.id,
        visit_status=visit.status.value,
        completed_step=completed_step_response,
        next_step=next_step_response,
    )


@router.post(
    "/{visit_id}/reorder-sequence",
    response_model=ReorderSequenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Propose a new exam sequence for a pending visit",
)
async def reorder_sequence(
    visit_id: uuid.UUID,
    request: ReorderSequenceRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Allows a patient or staff member to reorder their pending exams.
    Validates the proposed order against clinical rules before applying.
    """
    try:
        response = await reorder_visit_sequence(visit_id, request, db)
        await db.commit()
        return response
    except _VisitNotFoundError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content={"error": exc.message, "code": exc.code},
        )
    except _VisitNotReorderableError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content={"error": exc.message, "code": exc.code},
        )
    except _SequenceUUIDMismatchError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content={"error": exc.message, "code": exc.code},
        )


# ── Helper Functions ────────────────────────────────────────────────────────

async def _enqueue_first_area(visit_id: uuid.UUID, area_id: str) -> None:
    timestamp = datetime.now(timezone.utc).timestamp()
    await redis_client.zadd(f"queue:{area_id}", {str(visit_id): timestamp})

async def _load_area_by_id(area_id: uuid.UUID, db: AsyncSession) -> ClinicalArea:
    result = await db.execute(select(ClinicalArea).where(ClinicalArea.id == area_id))
    return result.scalar_one()

async def _find_visit_step_by_status(visit_id: uuid.UUID, status: VisitStepStatus, db: AsyncSession) -> VisitStep | None:
    result = await db.execute(
        select(VisitStep)
        .where(VisitStep.visit_id == visit_id, VisitStep.status == status)
        .order_by(VisitStep.step_order)
    )
    return result.scalars().first()

async def _complete_current_step(step: VisitStep) -> int:
    step.status = VisitStepStatus.COMPLETED
    step.completed_at = datetime.now(timezone.utc)
    if step.started_at:
        actual_wait = (step.completed_at - step.started_at).total_seconds() / 60.0
        step.actual_wait_minutes = int(actual_wait)
    else:
        step.actual_wait_minutes = 0
    return step.actual_wait_minutes

async def _start_next_step(next_step: VisitStep, current_area_id: uuid.UUID, visit_id: uuid.UUID) -> None:
    next_step.status = VisitStepStatus.PENDING
    # We do NOT set started_at here because they are not being attended yet, just queuing.
    timestamp = datetime.now(timezone.utc).timestamp()
    await redis_client.zrem(f"queue:{current_area_id}", str(visit_id))
    await redis_client.zadd(f"queue:{next_step.clinical_area_id}", {str(visit_id): timestamp})

async def _finish_visit(visit: Visit, current_area_id: uuid.UUID, db: AsyncSession) -> None:
    visit.status = VisitStatus.COMPLETED
    visit.completed_at = datetime.now(timezone.utc)
    await redis_client.zrem(f"queue:{current_area_id}", str(visit.id))
    db.add(PatientEvent(
        visit_id=visit.id,
        event_type="visit_completed",
        event_metadata={}
    ))
