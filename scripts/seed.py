"""
Seed data for SaludCopilot hackathon demo.
Creates one clinic with 7 clinical areas and prints the UUIDs.

Usage:
  cd apps/api
  python ../../scripts/seed.py
"""

import asyncio
import uuid
import sys
import os

# Ensure the api app is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))

from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

CLINIC_ID = uuid.uuid4()

AREAS = [
    {"id": uuid.uuid4(), "name": "Laboratorio",        "study_type": "laboratorio",        "capacity": 3},
    {"id": uuid.uuid4(), "name": "Ultrasonido",        "study_type": "ultrasonido",        "capacity": 2},
    {"id": uuid.uuid4(), "name": "Rayos X",            "study_type": "rayos_x",            "capacity": 2},
    {"id": uuid.uuid4(), "name": "Electrocardiograma", "study_type": "electrocardiograma", "capacity": 1},
    {"id": uuid.uuid4(), "name": "Papanicolaou",       "study_type": "papanicolaou",       "capacity": 2},
    {"id": uuid.uuid4(), "name": "Densitometría",      "study_type": "densitometria",      "capacity": 1},
    {"id": uuid.uuid4(), "name": "Tomografía",         "study_type": "tomografia",         "capacity": 1},
]


async def seed():
    """Inserts demo clinic and clinical areas into the database."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Insert clinic
            await session.execute(
                text(
                    "INSERT INTO clinics (id, name, address, active) "
                    "VALUES (:id, :name, :address, :active) "
                    "ON CONFLICT DO NOTHING"
                ),
                {
                    "id": str(CLINIC_ID),
                    "name": "Salud Digna Reforma",
                    "address": "Av. Paseo de la Reforma 222, CDMX",
                    "active": True,
                },
            )

            # Insert clinical areas
            for area in AREAS:
                await session.execute(
                    text(
                        "INSERT INTO clinical_areas "
                        "(id, clinic_id, name, study_type, simultaneous_capacity, active) "
                        "VALUES (:id, :clinic_id, :name, :study_type, :capacity, :active) "
                        "ON CONFLICT DO NOTHING"
                    ),
                    {
                        "id": str(area["id"]),
                        "clinic_id": str(CLINIC_ID),
                        "name": area["name"],
                        "study_type": area["study_type"],
                        "capacity": area["capacity"],
                        "active": True,
                    },
                )

    print("\n=== SEED DATA CREATED ===")
    print(f"CLINIC_ID={CLINIC_ID}")
    for area in AREAS:
        print(f"AREA_{area['study_type'].upper()}_ID={area['id']}")
    print("\nCopy these values to:")
    print("  apps/dashboard/.env.local → NEXT_PUBLIC_CLINIC_ID")
    print("  apps/cv/.env → CAMERA_TO_AREA_MAPPING")
    print("========================\n")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
