"""
SaludCopilot — Pydantic v2 schemas
====================================
Request and response contracts for all API endpoints.
Matches the interface specifications in ARQUITECTURA.md exactly.

Only this file defines the wire format. Models (SQLAlchemy) are in
app/models/models.py and are never exposed directly to callers.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Request schemas (entrada) ─────────────────────────────────────────────────


class CheckInRequest(BaseModel):
    """
    POST /api/v1/visits/check-in

    Registers a patient visit (walk-in or appointment).
    phone_number must be in E.164 format: +521234567890
    """

    phone_number: str = Field(
        ...,
        description="Patient phone number in E.164 format",
        examples=["+521234567890"],
        pattern=r"^\+[1-9]\d{7,14}$",
    )
    clinic_id: uuid.UUID = Field(..., description="UUID of the clinic")
    study_ids: list[uuid.UUID] = Field(
        ..., min_length=1, description="Ordered list of study UUIDs requested"
    )
    proposed_sequence: Optional[list[uuid.UUID]] = Field(
        None,
        description=(
            "Ordered list of area UUIDs representing the patient's preferred "
            "exam sequence. When provided, the sequence is validated against the "
            "rules engine before being accepted. Must contain the same UUIDs as "
            "study_ids. Omit (or set null) to let the engine decide the order."
        ),
    )
    has_appointment: bool = Field(
        ..., description="True if the patient has a prior appointment"
    )
    is_urgent: bool = Field(
        ..., description="True if the patient requires urgent attention"
    )


class OccupancyUpdateRequest(BaseModel):
    """
    POST /api/v1/areas/{area_id}/occupancy

    Published by the CV worker after each camera frame analysis.
    people_count is the number of people detected inside the area ROI.
    """

    people_count: int = Field(
        ..., ge=0, description="Number of people counted inside the area ROI"
    )
    timestamp: datetime = Field(
        ..., description="ISO8601 timestamp of the camera reading"
    )


class AdvanceStepRequest(BaseModel):
    """
    POST /api/v1/visits/{visit_id}/advance-step

    No body — the visit_id comes from the URL path parameter.
    This schema exists to make the contract explicit and allow future extension.
    """

    pass


# ── Response schemas (salida) ─────────────────────────────────────────────────


# ── Rules Engine payload DTOs (internal — shared between Prompt 1 & 2) ────────


class ExamPayloadItem(BaseModel):
    """
    Represents a single exam inside a RulesEngineValidationPayload.
    Carries all Study attributes the rules engine needs plus the
    caller's proposed position in the sequence.
    """

    area_id: uuid.UUID = Field(..., description="UUID of the ClinicalArea")
    study_type: str = Field(
        ..., description="Study type string matching rules engine constants (e.g. 'laboratorio')"
    )
    requires_fasting: bool = Field(default=False)
    is_urgent: bool = Field(default=False)
    has_appointment: bool = Field(default=False)
    proposed_order: int = Field(
        ..., ge=1, description="1-based position proposed by the patient"
    )


class RulesEngineValidationPayload(BaseModel):
    """
    Internal DTO consumed by the validation service (Prompt 2).
    Wraps the full ordered list of exams the caller wants to validate.
    """

    exams: list[ExamPayloadItem] = Field(
        ..., min_length=1, description="Ordered list of exams to validate"
    )



class SequenceStepResponse(BaseModel):
    """
    One step in a patient's study sequence.
    Used inside CheckInResponse, VisitContextResponse, and AdvanceStep responses.
    """

    order: int = Field(..., description="Position in the sequence (1-based)")
    area_id: uuid.UUID = Field(..., description="UUID of the clinical area")
    area_name: str = Field(..., description="Name of the clinical area")
    estimated_wait_minutes: int = Field(
        ..., description="Estimated wait time in minutes for this step"
    )
    rule_applied: Optional[str] = Field(
        None, description="Clinical rule code that determined this order (e.g. R-01), or null"
    )


class CheckInResponse(BaseModel):
    """
    Response for POST /api/v1/visits/check-in

    Returns the new visit ID, patient ID, and the full ordered study sequence.
    """

    visit_id: uuid.UUID = Field(..., description="UUID of the newly created visit")
    patient_id: uuid.UUID = Field(..., description="UUID of the patient")
    sequence: list[SequenceStepResponse] = Field(
        ..., description="Ordered sequence of studies calculated by the rules engine"
    )
    total_estimated_minutes: int = Field(
        ..., description="Total estimated visit duration in minutes"
    )


class VisitContextStepResponse(SequenceStepResponse):
    """
    One step as returned inside VisitContextResponse.

    Extends SequenceStepResponse with `status` so the bot and dashboard
    know whether a step is pending, currently being attended, or done.
    """

    status: str = Field(
        ...,
        description="Current step status: pending | in_progress | completed",
        examples=["pending", "in_progress", "completed"],
    )
    position_in_queue: int | None = Field(
        None,
        description="0-indexed position in the waiting area queue. 0 means they are next.",
    )


class VisitContextResponse(BaseModel):
    """
    Response for GET /api/v1/visits/{visit_id}/context

    Used by the bot to build WhatsApp messages with current visit state.
    """

    visit_id: uuid.UUID = Field(..., description="UUID of the visit")
    patient_name: str = Field(..., description="Full name of the patient")
    current_step: Optional[VisitContextStepResponse] = Field(
        None, description="The step the patient is currently waiting for or doing"
    )
    remaining_steps: list[VisitContextStepResponse] = Field(
        ..., description="Steps not yet started, in order"
    )
    total_estimated_minutes: int = Field(
        ..., description="Total remaining estimated time in minutes"
    )

# ── General schemas ───────────────────────────────────────────────────────────

class OccupancyResponse(BaseModel):
    """
    Response for POST /api/v1/areas/{area_id}/occupancy

    Returns the updated wait time estimate after processing the CV reading.
    """

    wait_time_estimate_minutes: int = Field(
        ..., description="Updated wait time estimate for this area in minutes"
    )


class AdvanceStepStepResponse(BaseModel):
    order: int
    area_name: str
    status: str
    actual_wait_minutes: Optional[int] = None


class AdvanceStepResponse(BaseModel):
    visit_id: uuid.UUID
    visit_status: str
    completed_step: AdvanceStepStepResponse
    next_step: Optional[AdvanceStepStepResponse] = None


class WaitTimeEstimateResponse(BaseModel):
    """
    Response for GET /api/v1/areas/{area_id}/wait-time-estimate

    Used by the dashboard WebSocket broadcast and direct polling.
    """

    area_id: uuid.UUID = Field(..., description="UUID of the clinical area")
    estimated_wait_minutes: int = Field(
        ..., description="Current ML model prediction for wait time in minutes"
    )
    current_queue_length: int = Field(
        ..., description="Number of patients currently waiting in this area"
    )
    people_in_area: int = Field(
        ..., description="Physical people count from CV worker (may be 0 if CV is offline)"
    )
    updated_at: datetime = Field(
        ..., description="Timestamp of the last update to this estimate"
    )


class ErrorResponse(BaseModel):
    """
    Standard error envelope returned by all 4xx and 5xx responses.

    Matches the error policy in CLAUDE.md:
    {"error": "human readable description", "code": "SCREAMING_SNAKE_ERROR_CODE"}
    """

    error: str = Field(..., description="Human-readable error description")
    code: str = Field(
        ...,
        description="Machine-readable error code in SCREAMING_SNAKE_CASE",
        examples=["VISIT_NOT_FOUND", "AREA_NOT_FOUND", "INVALID_PHONE_NUMBER"],
    )

# ── Doctor schemas ────────────────────────────────────────────────────────────


class DoctorLoginRequest(BaseModel):
    employee_id: str = Field(..., pattern=r"^\d{4}$", description="4-digit employee ID")
    password: str = Field(..., pattern=r"^\d{8}$", description="8-digit numeric password")


class DoctorLoginResponse(BaseModel):
    doctor_id: uuid.UUID
    full_name: str
    clinical_area_id: uuid.UUID
    clinical_area_name: str


class DoctorPatientResponse(BaseModel):
    """One row in the doctor's patient list."""
    visit_id: uuid.UUID
    patient_name: str
    step_status: str  # pending | in_progress | completed
    step_order: int
    total_steps: int
    estimated_wait_minutes: Optional[int]
    expected_consultation_minutes: Optional[int]
    elapsed_minutes: Optional[int]
    is_current: bool = True
    current_area_name: Optional[str] = None


class AreaQueueShift(BaseModel):
    """Represents a patient's shift in the public area screen."""
    visit_id: uuid.UUID
    turn_number: str
    patient_name: str
    status: str
    step_order: int


# ── Alert schemas ─────────────────────────────────────────────────────────────


class DoctorAlertResponse(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    area_id: uuid.UUID
    visit_id: Optional[uuid.UUID] = None
    alert_type: str
    message: str
    triggered_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Study change notification schema ──────────────────────────────────────────


class StudyChangeNotification(BaseModel):
    visit_id: uuid.UUID
    requesting_doctor_id: uuid.UUID
    old_area_id: uuid.UUID
    new_area_id: uuid.UUID
    reason: Optional[str] = None


# ── Reorder schemas ───────────────────────────────────────────────────────────


class ReorderSequenceRequest(BaseModel):
    """
    POST /api/v1/visits/{visit_id}/reorder-sequence

    Allows the patient (or a staff member) to propose a new exam order
    for a visit that has not yet started. The proposed_sequence must
    contain exactly the same area UUIDs that are pending on the visit.
    """

    proposed_sequence: list[uuid.UUID] = Field(
        ...,
        min_length=1,
        description=(
            "Ordered list of ClinicalArea UUIDs representing the desired exam order. "
            "Must contain the same UUIDs as the visit's pending steps."
        ),
    )


class ReorderSequenceResponse(BaseModel):
    """
    Response for POST /api/v1/visits/{visit_id}/reorder-sequence

    Returns the updated sequence if valid, or the list of violated rules
    if the proposed order was rejected.
    """

    visit_id: uuid.UUID = Field(..., description="UUID of the visit")
    accepted: bool = Field(
        ...,
        description="True if the proposed sequence passed all rules and was persisted.",
    )
    sequence: list[SequenceStepResponse] = Field(
        ...,
        description="The effective sequence after the operation (updated or unchanged).",
    )
    total_estimated_minutes: int = Field(
        ..., description="Total estimated visit duration in minutes"
    )
    rules_violations: list[str] = Field(
        default_factory=list,
        description=(
            "List of violated rule descriptions (e.g. 'R-01: Papanicolaou must precede "
            "ultrasonido transvaginal'). Empty when accepted=True."
        ),
    )
    reorder_rejected_reason: Optional[str] = Field(
        None,
        description="Human-readable reason when the reorder was rejected due to insufficient time savings.",
    )
