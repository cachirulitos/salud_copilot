"""
Seed script: Insert 2 test doctors into the database.
Run from apps/api/:

    python seed_doctors.py

Each doctor is assigned to a different clinical area in the CULIACAN clinic.
Credentials (for manual testing of the Portal Médico):

  Doctor 1 — Dr. Ana Torres
    employee_id : 1001
    password    : 12345678

  Doctor 2 — Dr. Carlos Mena
    employee_id : 1002
    password    : 87654321
"""
import asyncio
import uuid
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent
sys.path.append(str(API_DIR))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.auth import hash_password
from app.models.models import ClinicalArea, Doctor


# ── Clinic UUID used in seed_real_data.py (CULIACAN → id=1) ─────────────────
def get_stable_uuid(prefix: str, numeric_id: int) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"saludcopilot.com/{prefix}/{numeric_id}")

CULIACAN_CLINIC_UUID = get_stable_uuid("clinic", 1)


# ── Doctors to seed ──────────────────────────────────────────────────────────
# study_key matches the keys used in seed_real_data.py for CULIACAN areas
#   area_lab  = get_stable_uuid("area_1", 2)  → Laboratorio
#   area_rx   = get_stable_uuid("area_1", 5)  → Rayos X
#   area_us   = get_stable_uuid("area_1", 6)  → Ultrasonido
#   area_ecg  = get_stable_uuid("area_1", 9)  → Electrocardiograma

DOCTORS = [
    {
        "employee_id": "1001",
        "password": "12345678",
        "full_name": "Dra. Ana Torres",
        "area_uuid": get_stable_uuid("area_1", 2),   # Laboratorio
        "area_label": "Laboratorio",
    },
    {
        "employee_id": "1002",
        "password": "87654321",
        "full_name": "Dr. Carlos Mena",
        "area_uuid": get_stable_uuid("area_1", 5),   # Rayos X
        "area_label": "Rayos X",
    },
]


async def seed_doctors():
    print("🩺  Iniciando seed de doctores de prueba...\n")

    async with AsyncSessionLocal() as db:
        for doc in DOCTORS:
            # ── Check if area exists ─────────────────────────────────────
            area_result = await db.execute(
                select(ClinicalArea).where(ClinicalArea.id == doc["area_uuid"])
            )
            area = area_result.scalar_one_or_none()

            if area is None:
                print(
                    f"  ⚠️  Área '{doc['area_label']}' no encontrada (UUID: {doc['area_uuid']}).\n"
                    f"      Ejecuta seed_real_data.py primero para crear las áreas."
                )
                continue

            # ── Check for duplicate employee_id ──────────────────────────
            existing_result = await db.execute(
                select(Doctor).where(Doctor.employee_id == doc["employee_id"])
            )
            existing = existing_result.scalar_one_or_none()

            if existing:
                print(f"  ⏭️  Doctor con employee_id={doc['employee_id']} ya existe — omitiendo.")
                continue

            # ── Insert doctor ────────────────────────────────────────────
            doctor = Doctor(
                employee_id=doc["employee_id"],
                password_hash=hash_password(doc["password"]),
                full_name=doc["full_name"],
                clinical_area_id=doc["area_uuid"],
                active=True,
            )
            db.add(doctor)
            print(
                f"  ✅  Creando doctor: {doc['full_name']}\n"
                f"      employee_id : {doc['employee_id']}\n"
                f"      password    : {doc['password']}\n"
                f"      área        : {doc['area_label']} ({doc['area_uuid']})"
            )

        await db.commit()

    print("\n🎉  Seed completado. Accede al portal médico con las credenciales indicadas arriba.")
    print(f"     URL: http://localhost:3000/doctor/login\n")


if __name__ == "__main__":
    asyncio.run(seed_doctors())
