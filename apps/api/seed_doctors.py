"""
Seed script: Insert one doctor per active clinical area (CULIACAN clinic).
Deletes all existing doctors first so credentials are always fresh.
Run from apps/api/:

    python seed_doctors.py

Credentials:
  employee_id = 1001..100N  (one per area, printed at runtime)
  password    = 12345678    (same for all)
"""
import asyncio
import uuid
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent
sys.path.append(str(API_DIR))

from sqlalchemy import select, delete
from app.core.database import AsyncSessionLocal
from app.core.auth import hash_password
from app.models.models import ClinicalArea, Doctor


def get_stable_uuid(prefix: str, numeric_id: int) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"saludcopilot.com/{prefix}/{numeric_id}")


CULIACAN_CLINIC_UUID = get_stable_uuid("clinic", 1)
PASSWORD = "12345678"


async def seed_doctors():
    async with AsyncSessionLocal() as db:
        # Fetch all active areas for the clinic
        result = await db.execute(
            select(ClinicalArea).where(
                ClinicalArea.clinic_id == CULIACAN_CLINIC_UUID,
                ClinicalArea.active.is_(True),
            ).order_by(ClinicalArea.name)
        )
        areas = list(result.scalars().all())

        if not areas:
            print("No active areas found — run seed_real_data.py first.")
            return

        # Delete all existing doctors
        await db.execute(delete(Doctor))
        print(f"Deleted existing doctors.\n")

        print("Creating one doctor per area:\n")
        for idx, area in enumerate(areas, start=1):
            employee_id = f"{1000 + idx}"
            first_name = ["Ana", "Carlos", "Sofía", "Miguel", "Laura", "Roberto"][idx % 6]
            last_name  = ["Torres", "Mena", "Reyes", "Flores", "González", "Díaz"][idx % 6]
            full_name  = f"Dr. {first_name} {last_name}"

            doctor = Doctor(
                employee_id=employee_id,
                password_hash=hash_password(PASSWORD),
                full_name=full_name,
                clinical_area_id=area.id,
                active=True,
            )
            db.add(doctor)
            print(
                f"  {full_name}\n"
                f"    employee_id : {employee_id}\n"
                f"    password    : {PASSWORD}\n"
                f"    área        : {area.name}\n"
            )

        await db.commit()

    print("Done. Login at http://localhost:3000/doctor/login")


if __name__ == "__main__":
    asyncio.run(seed_doctors())
