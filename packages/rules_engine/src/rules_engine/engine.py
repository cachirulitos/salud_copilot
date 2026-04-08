"""
Clinical Rules Engine — SaludCopilot
=====================================
Independent module. Does not import anything from apps/api.
Input: list of requested studies
Output: ordered list with optimal sequence and the reason behind each decision

Rules coded directly from Salud Digna's operational documentation.
Each rule has a traceable code (R-00 through R-05) for auditing.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Study:
    id: str
    type: str                     # "laboratorio", "ultrasonido", "papanicolaou", etc.
    requires_fasting: bool = False
    is_urgent: bool = False
    has_appointment: bool = False


@dataclass
class SequenceStep:
    order: int
    study: Study
    rule_applied: Optional[str]   # code of the rule that determined this order, e.g. "R-01"
    reason: str                   # human-readable explanation in Spanish


@dataclass
class SequenceResult:
    steps: list[SequenceStep]
    estimated_time_minutes: int


MINUTES_PER_STUDY = 15
MINUTES_TRANSFER_BETWEEN_AREAS = 5

# ── Coded rules ──────────────────────────────────────────────────────────────
# Declarative reference for documentation and future tooling.
# The enforcement logic lives in _apply_rules below.

RULES = [
    {
        "code": "R-00",
        "description": "Urgentes primero, luego con cita, luego sin cita",
    },
    {
        "code": "R-01",
        "description": "Papanicolaou antes que Ultrasonido transvaginal",
        "affected_types": {"papanicolaou", "ultrasonido_transvaginal"},
        "first": "papanicolaou",
    },
    {
        "code": "R-02",
        "description": "En combinación VPH + Papanicolaou + Cultivo vaginal, Papanicolaou es primero",
        "affected_types": {"papanicolaou", "vph", "cultivo_vaginal"},
        "first": "papanicolaou",
    },
    {
        "code": "R-03",
        "description": "Densitometría antes que Tomografía o Resonancia con contraste",
        "affected_types": {"densitometria", "tomografia", "resonancia"},
        "first": "densitometria",
    },
    {
        "code": "R-04",
        "description": "Laboratorio con ayuno antes que Ultrasonido",
        "affected_types": {"laboratorio", "ultrasonido"},
        "first": "laboratorio",
        "condition": "requires_fasting",
    },
    {
        "code": "R-05",
        "description": "Estudios sin preparación antes que estudios con preparación",
        "affected_types": None,  # applies to all remaining studies
    },
]


def calculate_sequence(studies: list[Study]) -> SequenceResult:
    """
    Single entry point for the rules engine.

    Receives a patient's list of requested studies and returns the optimal
    sequence according to Salud Digna's operational rules.

    Parameters
    ----------
    studies : list[Study]
        Studies requested for the patient at check-in.

    Returns
    -------
    SequenceResult
        Ordered steps with rule traceability and total estimated time.
    """
    if not studies:
        return SequenceResult(steps=[], estimated_time_minutes=0)

    ordered = _apply_rules(studies)
    steps = [
        SequenceStep(
            order=index + 1,
            study=study,
            rule_applied=rule_code,
            reason=reason,
        )
        for index, (study, rule_code, reason) in enumerate(ordered)
    ]

    number_of_steps = len(steps)
    estimated_time_minutes = (
        number_of_steps * MINUTES_PER_STUDY
        + max(number_of_steps - 1, 0) * MINUTES_TRANSFER_BETWEEN_AREAS
    )

    return SequenceResult(steps=steps, estimated_time_minutes=estimated_time_minutes)


def validate_sequence(studies_with_order: list[tuple["Study", int]]) -> list[str]:
    """
    Validates whether a proposed exam sequence complies with all clinical rules.

    Does NOT reorder — only detects violations. Suitable for pre-flight checks
    before persisting a patient-proposed sequence.

    Parameters
    ----------
    studies_with_order : list[tuple[Study, int]]
        Each element is (Study, proposed_order) where proposed_order is 1-based.
        The list does not need to be pre-sorted by the caller.

    Returns
    -------
    list[str]
        Violation descriptions, one per broken rule.
        An empty list means the proposed sequence is fully valid.
    """
    if not studies_with_order:
        return []

    # Build a lookup: study_type -> proposed_order (1-based)
    order_by_type: dict[str, int] = {
        s.type: order for s, order in studies_with_order
    }
    types_present = set(order_by_type.keys())
    violations: list[str] = []

    # ── R-01 ─────────────────────────────────────────────────────────────────
    if {"papanicolaou", "ultrasonido_transvaginal"}.issubset(types_present):
        if order_by_type["papanicolaou"] > order_by_type["ultrasonido_transvaginal"]:
            violations.append(
                "R-01: Papanicolaou must be performed before Ultrasonido Transvaginal."
            )

    # ── R-02 ─────────────────────────────────────────────────────────────────
    if "papanicolaou" in types_present and types_present & {"vph", "cultivo_vaginal"}:
        companions = [t for t in ("vph", "cultivo_vaginal") if t in types_present]
        for companion in companions:
            if order_by_type["papanicolaou"] > order_by_type[companion]:
                violations.append(
                    f"R-02: Papanicolaou must be performed before {companion} "
                    f"when both are requested."
                )
                break  # report once per R-02 activation

    # ── R-03 ─────────────────────────────────────────────────────────────────
    if "densitometria" in types_present and types_present & {"tomografia", "resonancia"}:
        imaging = [t for t in ("tomografia", "resonancia") if t in types_present]
        for img in imaging:
            if order_by_type["densitometria"] > order_by_type[img]:
                violations.append(
                    f"R-03: Densitometria must be performed before {img}."
                )

    # ── R-04 ─────────────────────────────────────────────────────────────────
    if "laboratorio" in types_present and "ultrasonido" in types_present:
        fasting_labs = [s for s, _ in studies_with_order
                        if s.type == "laboratorio" and s.requires_fasting]
        if fasting_labs:
            if order_by_type["laboratorio"] > order_by_type["ultrasonido"]:
                violations.append(
                    "R-04: Fasting Laboratorio must be performed before Ultrasonido."
                )

    # ── R-05 ─────────────────────────────────────────────────────────────────
    fasting_studies = [
        (s, o) for s, o in studies_with_order if s.requires_fasting
    ]
    non_fasting_studies = [
        (s, o) for s, o in studies_with_order if not s.requires_fasting
    ]
    if fasting_studies and non_fasting_studies:
        max_fasting_order = max(o for _, o in fasting_studies)
        min_non_fasting_order = min(o for _, o in non_fasting_studies)
        # If any fasting study is placed *before* a non-fasting one it is invalid
        # (non-fasting should all precede fasting)
        min_fasting_order = min(o for _, o in fasting_studies)
        max_non_fasting_order = max(o for _, o in non_fasting_studies)
        if min_fasting_order < max_non_fasting_order:
            violations.append(
                "R-05: Studies without preparation must all precede studies that "
                "require preparation (e.g., fasting)."
            )

    return violations


def _apply_rules(studies: list[Study]) -> list[tuple[Study, Optional[str], str]]:
    """
    Applies all clinical rules in priority order.

    Returns a list of (study, rule_code, reason) tuples in the final
    recommended sequence.

    Priority order:
        R-00 → R-01 → R-02 → R-03 → R-04 → R-05 → standard order
    """
    types_present = {study.type for study in studies}

    # ── R-00: urgent first, then with appointment, then walk-in ──────────
    # Assign a priority bucket to each study so the sort is stable across
    # studies that share the same bucket.
    def _r00_priority(study: Study) -> int:
        if study.is_urgent:
            return 0
        if study.has_appointment:
            return 1
        return 2

    studies_sorted = sorted(studies, key=_r00_priority)

    # Separate studies that received R-00 (non-standard bucket) from those
    # that did not, so we can attach an explicit rule code only where it
    # changed the order.
    result: list[tuple[Study, Optional[str], str]] = []
    remaining: list[Study] = []

    for study in studies_sorted:
        if study.is_urgent:
            result.append((
                study,
                "R-00",
                "Estudio urgente; se atiende antes que los demás.",
            ))
        elif study.has_appointment:
            result.append((
                study,
                "R-00",
                "Paciente con cita previa; tiene prioridad sobre pacientes de paso.",
            ))
        else:
            remaining.append(study)

    # ── R-01: papanicolaou before ultrasonido_transvaginal ────────────────
    if {"papanicolaou", "ultrasonido_transvaginal"}.issubset(types_present):
        remaining = _move_first(
            remaining=remaining,
            study_type="papanicolaou",
            result=result,
            rule_code="R-01",
            reason="Papanicolaou debe realizarse antes del ultrasonido transvaginal.",
        )

    # ── R-02: papanicolaou first in VPH / cultivo_vaginal combination ─────
    if "papanicolaou" in types_present and types_present & {"vph", "cultivo_vaginal"}:
        remaining = _move_first(
            remaining=remaining,
            study_type="papanicolaou",
            result=result,
            rule_code="R-02",
            reason=(
                "En combinación con VPH o cultivo vaginal, "
                "el Papanicolaou debe realizarse primero."
            ),
        )

    # ── R-03: densitometria before tomografia / resonancia ────────────────
    if "densitometria" in types_present and types_present & {"tomografia", "resonancia"}:
        remaining = _move_first(
            remaining=remaining,
            study_type="densitometria",
            result=result,
            rule_code="R-03",
            reason=(
                "La densitometría debe realizarse antes de la tomografía "
                "o resonancia con contraste."
            ),
        )

    # ── R-04: fasting laboratorio before ultrasonido ──────────────────────
    if "laboratorio" in types_present and "ultrasonido" in types_present:
        fasting_lab = next(
            (s for s in remaining if s.type == "laboratorio" and s.requires_fasting),
            None,
        )
        if fasting_lab:
            remaining = _move_first(
                remaining=remaining,
                study_type="laboratorio",
                result=result,
                rule_code="R-04",
                reason="El laboratorio con ayuno debe realizarse antes del ultrasonido.",
            )

    # ── R-05: studies without preparation before studies with preparation ──
    without_preparation = [s for s in remaining if not s.requires_fasting]
    with_preparation = [s for s in remaining if s.requires_fasting]

    # Annotate R-05 only when the rule actually reorders something
    has_both_groups = bool(without_preparation) and bool(with_preparation)

    for study in without_preparation:
        rule_code = "R-05" if has_both_groups else None
        reason = (
            "Estudio sin preparación previa; se realiza antes de los que requieren preparación."
            if has_both_groups
            else "Orden estándar de atención."
        )
        result.append((study, rule_code, reason))

    for study in with_preparation:
        rule_code = "R-05" if has_both_groups else None
        reason = (
            "Estudio con preparación requerida; se realiza después de los que no la requieren."
            if has_both_groups
            else "Orden estándar de atención."
        )
        result.append((study, rule_code, reason))

    return result


def _move_first(
    remaining: list[Study],
    study_type: str,
    result: list,
    rule_code: str,
    reason: str,
) -> list[Study]:
    """
    Moves the first study of the given type from remaining into result.

    If a study of that type is already in result (placed by a previous rule),
    this function is a no-op — avoids duplicates when R-01 and R-02 both
    target papanicolaou.

    Parameters
    ----------
    remaining : list[Study]
        Studies not yet placed in result.
    study_type : str
        The Study.type value to look for.
    result : list
        Accumulator of (study, rule_code, reason) tuples already placed.
    rule_code : str
        Rule code to attach to this placement.
    reason : str
        Human-readable Spanish explanation for this placement.

    Returns
    -------
    list[Study]
        Updated remaining list with the matched study removed (if found).
    """
    already_placed_types = {entry[0].type for entry in result}
    if study_type in already_placed_types:
        # Study already placed by a prior rule — do not duplicate
        return remaining

    target = next((s for s in remaining if s.type == study_type), None)
    if target is not None:
        result.append((target, rule_code, reason))
        return [s for s in remaining if s is not target]

    return remaining
