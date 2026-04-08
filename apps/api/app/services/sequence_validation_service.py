# apps/api/app/services/sequence_validation_service.py

import sys

from app.core.config import ROOT_DIR
sys.path.append(str(ROOT_DIR))

from packages.rules_engine.src.rules_engine.engine import Study, validate_sequence
from app.core.exceptions import SequenceRuleViolationError
from app.schemas.schemas import RulesEngineValidationPayload


def validate_proposed_sequence(
    payload: RulesEngineValidationPayload,
    is_urgent: bool = False,
    has_appointment: bool = False,
) -> None:
    """
    Adapter between the API layer and the clinical rules engine.

    Converts each ExamPayloadItem into a (Study, proposed_order) tuple,
    runs validate_sequence(), and raises SequenceRuleViolationError if any
    rule is violated.

    Parameters
    ----------
    payload : RulesEngineValidationPayload
        Ordered list of exams to validate. Each item's proposed_order field
        determines the sequence position under evaluation.
    is_urgent : bool
        Patient-level urgency flag forwarded to every Study object.
    has_appointment : bool
        Patient-level appointment flag forwarded to every Study object.

    Raises
    ------
    SequenceRuleViolationError
        If one or more clinical rules (R-01 through R-05) are violated.
        The exception carries the full list of violation descriptions.

    Returns
    -------
    None
        Returns without raising when the proposed sequence is fully valid.
    """
    studies_with_order: list[tuple[Study, int]] = [
        (
            Study(
                id=str(item.area_id),
                type=item.study_type,
                requires_fasting=item.requires_fasting,
                is_urgent=is_urgent,
                has_appointment=has_appointment,
            ),
            item.proposed_order,
        )
        for item in payload.exams
    ]

    violations = validate_sequence(studies_with_order)

    if violations:
        raise SequenceRuleViolationError(violations)
