"""
SaludCopilot — Admin CRUD endpoints
Manages clinics, clinical areas, and clinical rules.
No authentication enforced (hackathon scope).
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import ClinicalArea, ClinicalRule, Clinic

router = APIRouter()


# ── Request schemas ───────────────────────────────────────────────────────────


class ClinicCreate(BaseModel):
    name: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class ClinicUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    active: Optional[bool] = None


class AreaCreate(BaseModel):
    clinic_id: uuid.UUID
    name: str
    study_type: str
    simultaneous_capacity: int
    navigation_instructions: Optional[str] = None


class AreaUpdate(BaseModel):
    name: Optional[str] = None
    study_type: Optional[str] = None
    simultaneous_capacity: Optional[int] = None
    active: Optional[bool] = None
    navigation_instructions: Optional[str] = None


# ── Clinics ───────────────────────────────────────────────────────────────────


@router.get("/clinics")
async def list_clinics(db: AsyncSession = Depends(get_db)):
    """List all clinics ordered by name."""
    result = await db.execute(select(Clinic).order_by(Clinic.name))
    clinics = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "address": c.address,
            "active": c.active,
        }
        for c in clinics
    ]


@router.post("/clinics", status_code=status.HTTP_201_CREATED)
async def create_clinic(body: ClinicCreate, db: AsyncSession = Depends(get_db)):
    """Create a new clinic."""
    clinic = Clinic(
        name=body.name,
        address=body.address,
        latitude=body.latitude,
        longitude=body.longitude,
    )
    db.add(clinic)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return JSONResponse(status_code=409, content={"error": "Clinic already exists"})
    await db.refresh(clinic)
    return {
        "id": str(clinic.id),
        "name": clinic.name,
        "address": clinic.address,
        "active": clinic.active,
    }


@router.patch("/clinics/{clinic_id}")
async def update_clinic(
    clinic_id: uuid.UUID,
    body: ClinicUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update clinic name, address, or active flag."""
    result = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = result.scalar_one_or_none()
    if clinic is None:
        return JSONResponse(status_code=404, content={"error": "Clinic not found"})

    if body.name is not None:
        clinic.name = body.name
    if body.address is not None:
        clinic.address = body.address
    if body.active is not None:
        clinic.active = body.active

    await db.commit()
    return {
        "id": str(clinic.id),
        "name": clinic.name,
        "address": clinic.address,
        "active": clinic.active,
    }


@router.get("/clinics/{clinic_id}/areas")
async def list_clinic_areas(
    clinic_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all areas (active and inactive) for a clinic."""
    result = await db.execute(
        select(ClinicalArea)
        .where(ClinicalArea.clinic_id == clinic_id)
        .order_by(ClinicalArea.name)
    )
    areas = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "name": a.name,
            "study_type": a.study_type,
            "simultaneous_capacity": a.simultaneous_capacity,
            "active": a.active,
            "navigation_instructions": a.navigation_instructions,
        }
        for a in areas
    ]


# ── Areas ─────────────────────────────────────────────────────────────────────


@router.post("/areas", status_code=status.HTTP_201_CREATED)
async def create_area(body: AreaCreate, db: AsyncSession = Depends(get_db)):
    """Create a new clinical area inside a clinic."""
    area = ClinicalArea(
        clinic_id=body.clinic_id,
        name=body.name,
        study_type=body.study_type,
        simultaneous_capacity=body.simultaneous_capacity,
        navigation_instructions=body.navigation_instructions,
    )
    db.add(area)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return JSONResponse(
            status_code=422,
            content={"error": "Invalid clinic_id — clinic not found"},
        )
    await db.refresh(area)
    return {
        "id": str(area.id),
        "name": area.name,
        "study_type": area.study_type,
        "simultaneous_capacity": area.simultaneous_capacity,
        "active": area.active,
    }


@router.patch("/areas/{area_id}")
async def update_area(
    area_id: uuid.UUID,
    body: AreaUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing clinical area."""
    result = await db.execute(select(ClinicalArea).where(ClinicalArea.id == area_id))
    area = result.scalar_one_or_none()
    if area is None:
        return JSONResponse(status_code=404, content={"error": "Area not found"})

    if body.name is not None:
        area.name = body.name
    if body.study_type is not None:
        area.study_type = body.study_type
    if body.simultaneous_capacity is not None:
        area.simultaneous_capacity = body.simultaneous_capacity
    if body.active is not None:
        area.active = body.active
    if body.navigation_instructions is not None:
        area.navigation_instructions = body.navigation_instructions

    await db.commit()
    return {
        "id": str(area.id),
        "name": area.name,
        "study_type": area.study_type,
        "simultaneous_capacity": area.simultaneous_capacity,
        "active": area.active,
    }


# ── Rules ─────────────────────────────────────────────────────────────────────


import sys
from app.core.config import ROOT_DIR
sys.path.append(str(ROOT_DIR))
from packages.rules_engine.src.rules_engine.engine import RULES

@router.get("/rules")
async def list_rules():
    """List all clinical rules by interacting directly with the engine package."""
    serializable_rules = []
    for r in RULES:
        rule_dict = dict(r)
        if "affected_types" in rule_dict and isinstance(rule_dict["affected_types"], set):
            rule_dict["affected_types"] = list(rule_dict["affected_types"])
        serializable_rules.append(rule_dict)
    return serializable_rules
