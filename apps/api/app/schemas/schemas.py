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


class SequenceStepResponse(BaseModel):
    """
    One step in a patient's study sequence.
    Used inside CheckInResponse, VisitContextResponse, and AdvanceStep responses.
    """

    order: int = Field(..., description="Position in the sequence (1-based)")
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


class VisitContextResponse(BaseModel):
    """
    Response for GET /api/v1/visits/{visit_id}/context

    Used by the bot to build WhatsApp messages with current visit state.
    """

    visit_id: uuid.UUID = Field(..., description="UUID of the visit")
    patient_name: str = Field(..., description="Full name of the patient")
    current_step: SequenceStepResponse = Field(
        ..., description="The step the patient is currently at"
    )
    remaining_steps: list[SequenceStepResponse] = Field(
        ..., description="Steps not yet started, in order"
    )
    total_estimated_minutes: int = Field(
        ..., description="Total remaining estimated time in minutes"
    )


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
