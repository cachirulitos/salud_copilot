"""
SaludCopilot — SQLAlchemy 2.0 models
=====================================
Matches the database schema defined in ARQUITECTURA.md.
Only the API module writes to PostgreSQL.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ── Enums ────────────────────────────────────────────────────────────────────


class VisitStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class VisitStepStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class NotificationType(str, enum.Enum):
    WELCOME = "welcome"
    TURN_READY = "turn_ready"
    TURN_APPROACHING = "turn_approaching"
    RESULTS_READY = "results_ready"
    WAIT_TIME_UPDATED = "wait_time_updated"


class NotificationStatus(str, enum.Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class RuleType(str, enum.Enum):
    ORDER = "order"
    PRIORITY = "priority"
    RESTRICTION = "restriction"


# ── Models ───────────────────────────────────────────────────────────────────


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    visits: Mapped[list["Visit"]] = relationship("Visit", back_populates="patient")

    def __repr__(self) -> str:
        return f"<Patient id={self.id} phone_number={self.phone_number}>"


class Clinic(Base):
    __tablename__ = "clinics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float] = mapped_column(Numeric(10, 7), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    clinical_areas: Mapped[list["ClinicalArea"]] = relationship("ClinicalArea", back_populates="clinic")
    visits: Mapped[list["Visit"]] = relationship("Visit", back_populates="clinic")

    def __repr__(self) -> str:
        return f"<Clinic id={self.id} name={self.name}>"


class ClinicalArea(Base):
    __tablename__ = "clinical_areas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    study_type: Mapped[str] = mapped_column(String, nullable=False)
    simultaneous_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # A4: navigation instructions for bot welcome message
    navigation_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    clinic: Mapped["Clinic"] = relationship("Clinic", back_populates="clinical_areas")
    visit_steps: Mapped[list["VisitStep"]] = relationship("VisitStep", back_populates="clinical_area")
    wait_time_estimates: Mapped[list["WaitTimeEstimate"]] = relationship("WaitTimeEstimate", back_populates="clinical_area")

    def __repr__(self) -> str:
        return f"<ClinicalArea id={self.id} name={self.name}>"


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    clinic_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False)
    status: Mapped[VisitStatus] = mapped_column(Enum(VisitStatus), default=VisitStatus.PENDING)
    has_appointment: Mapped[bool] = mapped_column(Boolean, default=False)
    is_urgent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    patient: Mapped["Patient"] = relationship("Patient", back_populates="visits")
    clinic: Mapped["Clinic"] = relationship("Clinic", back_populates="visits")
    visit_steps: Mapped[list["VisitStep"]] = relationship("VisitStep", back_populates="visit")
    notifications: Mapped[list["Notification"]] = relationship("Notification", back_populates="visit")
    patient_events: Mapped[list["PatientEvent"]] = relationship("PatientEvent", back_populates="visit")

    def __repr__(self) -> str:
        return f"<Visit id={self.id} status={self.status}>"


class VisitStep(Base):
    __tablename__ = "visit_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("visits.id"), nullable=False)
    clinical_area_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinical_areas.id"), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[VisitStepStatus] = mapped_column(Enum(VisitStepStatus), default=VisitStepStatus.PENDING)
    rule_applied: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    estimated_wait_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actual_wait_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    visit: Mapped["Visit"] = relationship("Visit", back_populates="visit_steps")
    clinical_area: Mapped["ClinicalArea"] = relationship("ClinicalArea", back_populates="visit_steps")

    def __repr__(self) -> str:
        return f"<VisitStep id={self.id} step_order={self.step_order}>"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("visits.id"), nullable=False)
    notification_type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(Enum(NotificationStatus), default=NotificationStatus.SENT)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    visit: Mapped["Visit"] = relationship("Visit", back_populates="notifications")

    def __repr__(self) -> str:
        return f"<Notification id={self.id} type={self.notification_type}>"


class ClinicalRule(Base):
    __tablename__ = "clinical_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rule_type: Mapped[RuleType] = mapped_column(Enum(RuleType), nullable=False)
    condition: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    effect: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<ClinicalRule id={self.id} code={self.code}>"


class WaitTimeEstimate(Base):
    __tablename__ = "wait_time_estimates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinical_area_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinical_areas.id"), nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    people_in_area: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    clinical_area: Mapped["ClinicalArea"] = relationship("ClinicalArea", back_populates="wait_time_estimates")

    def __repr__(self) -> str:
        return f"<WaitTimeEstimate id={self.id} estimated_minutes={self.estimated_minutes}>"


class PatientEvent(Base):
    """Append-only event log. No updated_at by design."""
    __tablename__ = "patient_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("visits.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    event_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    visit: Mapped["Visit"] = relationship("Visit", back_populates="patient_events")

    def __repr__(self) -> str:
        return f"<PatientEvent id={self.id} event_type={self.event_type}>"
