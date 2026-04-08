# apps/api/app/services/reorder_sequence_service.py

import sys
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import ROOT_DIR, settings
sys.path.append(str(ROOT_DIR))

import redis.asyncio as redis
from app.routers.dashboard_ws import broadcast_to_clinic

from app.core.exceptions import SequenceRuleViolationError
from app.models.models import ClinicalArea, Visit, VisitStatus, VisitStep, VisitStepStatus, WaitTimeEstimate
from app.schemas.schemas import (
    ExamPayloadItem,
    ReorderSequenceRequest,
    ReorderSequenceResponse,
    RulesEngineValidationPayload,
    SequenceStepResponse,
)
from app.services.sequence_validation_service import validate_proposed_sequence

MINUTES_PER_STUDY = 15
MINUTES_TRANSFER = 5
FASTING_STUDY_TYPE = "laboratorio"


async def reorder_visit_sequence(
    visit_id: uuid.UUID,
    request: ReorderSequenceRequest,
    db: AsyncSession,
) -> ReorderSequenceResponse:
    """
    Core use case: reorder the pending exam steps of an existing visit.

    Injects validate_proposed_sequence (Prompt 2) to guard against rule violations.
    Persists the updated step_order values only if the sequence is fully valid.

    Business rules enforced:
    - Visit must exist and be in a non-terminal state (not completed/cancelled).
    - Only PENDING steps are reorderable; IN_PROGRESS step position is frozen.
    - proposed_sequence must match the set of pending area UUIDs exactly.
    - Proposed order must not violate any clinical rule (R-01 through R-05).

    Returns ReorderSequenceResponse with accepted=True and the new sequence on success,
    or accepted=False with rules_violations populated on a rule violation.
    Raises JSONResponse-compatible exceptions for structural errors (404/409/422).
    """

    # ── 1. Load visit ─────────────────────────────────────────────────────────
    visit_result = await db.execute(select(Visit).where(Visit.id == visit_id))
    visit = visit_result.scalar_one_or_none()
    if visit is None:
        raise _VisitNotFoundError()

    if visit.status in (VisitStatus.COMPLETED, VisitStatus.CANCELLED):
        raise _VisitNotReorderableError(
            f"Visit is already {visit.status.value} and cannot be reordered."
        )

    # ── 2. Load all steps ─────────────────────────────────────────────────────
    steps_result = await db.execute(
        select(VisitStep)
        .where(VisitStep.visit_id == visit_id)
        .order_by(VisitStep.step_order)
    )
    all_steps = list(steps_result.scalars().all())

    pending_steps = [s for s in all_steps if s.status == VisitStepStatus.PENDING]
    has_in_progress = any(s.status == VisitStepStatus.IN_PROGRESS for s in all_steps)

    if has_in_progress and not pending_steps:
        raise _VisitNotReorderableError(
            "All remaining steps are in-progress; nothing to reorder."
        )

    if not pending_steps:
        raise _VisitNotReorderableError("No pending steps to reorder.")

    # ── 3. Validate UUID set matches pending steps ────────────────────────────
    pending_area_ids = {str(s.clinical_area_id) for s in pending_steps}
    proposed_ids = {str(uid) for uid in request.proposed_sequence}
    if pending_area_ids != proposed_ids:
        raise _SequenceUUIDMismatchError(
            "proposed_sequence must contain exactly the UUIDs of all pending steps."
        )

    # ── 4. Resolve area metadata for validation ───────────────────────────────
    area_rows_result = await db.execute(
        select(ClinicalArea).where(
            ClinicalArea.id.in_([s.clinical_area_id for s in pending_steps])
        )
    )
    area_by_id: dict[str, ClinicalArea] = {
        str(a.id): a for a in area_rows_result.scalars().all()
    }

    # Determine patient-level flags from the visit
    has_appointment: bool = visit.has_appointment
    is_urgent: bool = visit.is_urgent

    # ── 5. Validate proposed order against rules engine ───────────────────────
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
                        is_urgent=is_urgent,
                        has_appointment=has_appointment,
                        proposed_order=idx + 1,
                    )
                    for idx, uid in enumerate(request.proposed_sequence)
                ]
            ),
            is_urgent=is_urgent,
            has_appointment=has_appointment,
        )
    except SequenceRuleViolationError as exc:
        # Return a soft rejection — do not persist, expose violations to caller
        current_sequence = await _build_current_sequence(pending_steps, area_by_id)
        total = _estimate_total(len(pending_steps))
        return ReorderSequenceResponse(
            visit_id=visit_id,
            accepted=False,
            sequence=current_sequence,
            total_estimated_minutes=total,
            rules_violations=exc.violations,
        )

    # ── 5.5 Check time savings ────────────────────────────────────────────────
    savings = await _compute_time_savings(pending_steps, request.proposed_sequence, area_by_id, db)
    if savings <= 5:
        current_sequence = await _build_current_sequence(pending_steps, area_by_id)
        return ReorderSequenceResponse(
            visit_id=visit_id,
            accepted=False,
            sequence=current_sequence,
            total_estimated_minutes=_estimate_total(len(pending_steps)),
            rules_violations=[],
            reorder_rejected_reason=(
                f"El reordenamiento no genera ahorro suficiente "
                f"({savings} min ≤ 5 min mínimo requerido)."
            ),
        )

    # ── 6. Persist updated step_order values ──────────────────────────────────
    step_by_area: dict[str, VisitStep] = {
        str(s.clinical_area_id): s for s in pending_steps
    }
    # Offset pending steps by the number of already-completed/in-progress steps
    in_progress_count = sum(
        1 for s in all_steps
        if s.status in (VisitStepStatus.COMPLETED, VisitStepStatus.IN_PROGRESS)
    )

    for new_order, area_uid in enumerate(request.proposed_sequence, start=1):
        step = step_by_area[str(area_uid)]
        step.step_order = in_progress_count + new_order

    await db.flush()

    # ── 6.5 Queue Transfer & WebSockets ────────────────────────────────────────
    old_first_area_uid = str(pending_steps[0].clinical_area_id)
    new_first_area_uid = str(request.proposed_sequence[0])

    if old_first_area_uid != new_first_area_uid:
        # 1. Update Redis Queue
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.zrem(f"queue:{old_first_area_uid}", str(visit_id))
        timestamp = datetime.now(timezone.utc).timestamp()
        await redis_client.zadd(f"queue:{new_first_area_uid}", {str(visit_id): timestamp})

        # 2. Alerts for Doctors
        old_area_name = area_by_id[old_first_area_uid].name
        new_area_name = area_by_id[new_first_area_uid].name

        # Notify old doctor that patient moved away
        await broadcast_to_clinic(
            str(visit.clinic_id),
            {
                "event": "study_change_notification",
                "data": {
                    "visit_id": str(visit_id),
                    "old_area": old_area_name,
                    "new_area": new_area_name,
                    "reason": "El paciente ha reordenado dinámicamente sus estudios",
                }
            }
        )
        
        # Notify new doctor that patient arrived
        await broadcast_to_clinic(
            str(visit.clinic_id),
            {
                "event": "checkin_created",
                "data": {
                    "current_area": new_area_name,
                }
            }
        )

    # ── 7. Build and return the updated sequence ──────────────────────────────
    updated_steps = sorted(
        [step_by_area[str(uid)] for uid in request.proposed_sequence],
        key=lambda s: s.step_order,
    )
    updated_sequence = [
        SequenceStepResponse(
            order=s.step_order,
            area_id=s.clinical_area_id,
            area_name=area_by_id[str(s.clinical_area_id)].name,
            estimated_wait_minutes=s.estimated_wait_minutes or 0,
            rule_applied=s.rule_applied,
        )
        for s in updated_steps
    ]

    return ReorderSequenceResponse(
        visit_id=visit_id,
        accepted=True,
        sequence=updated_sequence,
        total_estimated_minutes=_estimate_total(len(updated_steps)),
        rules_violations=[],
    )


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _compute_time_savings(
    pending_steps: list[VisitStep],
    proposed_sequence: list,
    area_by_id: dict,
    db: AsyncSession,
) -> int:
    """
    Returns current_total - proposed_total in minutes.
    Positive means the proposed order saves time.
    Falls back to 0 for any area missing a WaitTimeEstimate.
    """
    area_ids = [s.clinical_area_id for s in pending_steps]
    wt_result = await db.execute(
        select(WaitTimeEstimate).where(WaitTimeEstimate.clinical_area_id.in_(area_ids))
    )
    wait_by_area: dict[str, int] = {
        str(wt.clinical_area_id): wt.estimated_minutes
        for wt in wt_result.scalars().all()
    }

    current_order = [str(s.clinical_area_id) for s in sorted(pending_steps, key=lambda s: s.step_order)]
    proposed_order = [str(uid) for uid in proposed_sequence]

    current_total = sum(wait_by_area.get(aid, 0) for aid in current_order)
    proposed_total = sum(wait_by_area.get(aid, 0) for aid in proposed_order)

    return current_total - proposed_total


def _estimate_total(n: int) -> int:
    return n * MINUTES_PER_STUDY + max(n - 1, 0) * MINUTES_TRANSFER


async def _build_current_sequence(
    steps: list[VisitStep], area_by_id: dict[str, ClinicalArea]
) -> list[SequenceStepResponse]:
    return [
        SequenceStepResponse(
            order=s.step_order,
            area_id=s.clinical_area_id,
            area_name=area_by_id[str(s.clinical_area_id)].name,
            estimated_wait_minutes=s.estimated_wait_minutes or 0,
            rule_applied=s.rule_applied,
        )
        for s in sorted(steps, key=lambda s: s.step_order)
    ]


# ── Domain errors (caught by the controller) ──────────────────────────────────

class _VisitNotFoundError(Exception):
    code = "VISIT_NOT_FOUND"
    http_status = 404
    message = "Visit not found."


class _VisitNotReorderableError(Exception):
    code = "VISIT_NOT_REORDERABLE"
    http_status = 409

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class _SequenceUUIDMismatchError(Exception):
    code = "SEQUENCE_UUID_MISMATCH"
    http_status = 422

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
