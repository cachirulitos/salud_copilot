"""
Seed data for SaludCopilot hackathon demo.
Creates one clinic, 7 clinical areas, 7 doctors, and 3 demo visits.

Usage (inside the API container or with DATABASE_URL set):
  python scripts/seed.py

All IDs are deterministic so URLs are predictable for the demo.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ── Fixed IDs (match ml/scripts/train_synthetic.py CLINIC_ID) ──────────────
CLINIC_ID = "1db93003-d50e-4f56-80d0-8b994b98eaa8"

AREAS = [
    {"id": "a1000001-0000-0000-0000-000000000001", "name": "Laboratorio",        "study_type": "laboratorio",        "capacity": 3, "nav": "Planta baja, al fondo a la derecha"},
    {"id": "a1000001-0000-0000-0000-000000000002", "name": "Ultrasonido",        "study_type": "ultrasonido",        "capacity": 2, "nav": "Segundo piso, consultorio 201"},
    {"id": "a1000001-0000-0000-0000-000000000003", "name": "Rayos X",            "study_type": "rayos_x",            "capacity": 2, "nav": "Planta baja, pasillo izquierdo"},
    {"id": "a1000001-0000-0000-0000-000000000004", "name": "Electrocardiograma", "study_type": "electrocardiograma", "capacity": 1, "nav": "Segundo piso, consultorio 205"},
    {"id": "a1000001-0000-0000-0000-000000000005", "name": "Papanicolaou",       "study_type": "papanicolaou",       "capacity": 2, "nav": "Segundo piso, consultorio 210"},
    {"id": "a1000001-0000-0000-0000-000000000006", "name": "Densitometria",      "study_type": "densitometria",      "capacity": 1, "nav": "Tercer piso, consultorio 301"},
    {"id": "a1000001-0000-0000-0000-000000000007", "name": "Tomografia",         "study_type": "tomografia",         "capacity": 1, "nav": "Planta baja, area de imagenologia"},
]

# Password: 12345678
PASSWORD_HASH = "$2b$12$wF4TKQF9aLxqiI2gzQ/4DuTgL1Odxk016p9XP7c9IQax6C8EZb5Uy"

DOCTORS = [
    {"id": "d1000001-0000-0000-0000-000000000001", "employee_id": "0001", "name": "Dra. Maria Garcia",     "area_idx": 0},
    {"id": "d1000001-0000-0000-0000-000000000002", "employee_id": "0002", "name": "Dr. Carlos Rodriguez",  "area_idx": 1},
    {"id": "d1000001-0000-0000-0000-000000000003", "employee_id": "0003", "name": "Dra. Ana Martinez",     "area_idx": 2},
    {"id": "d1000001-0000-0000-0000-000000000004", "employee_id": "0004", "name": "Dr. Luis Hernandez",    "area_idx": 3},
    {"id": "d1000001-0000-0000-0000-000000000005", "employee_id": "0005", "name": "Dra. Sofia Lopez",      "area_idx": 4},
    {"id": "d1000001-0000-0000-0000-000000000006", "employee_id": "0006", "name": "Dr. Pedro Sanchez",     "area_idx": 5},
    {"id": "d1000001-0000-0000-0000-000000000007", "employee_id": "0007", "name": "Dra. Laura Torres",     "area_idx": 6},
]

# Demo patients
PATIENTS = [
    {"id": "p1000001-0000-0000-0000-000000000001", "phone": "+525512340001", "name": "Juan Perez Gomez"},
    {"id": "p1000001-0000-0000-0000-000000000002", "phone": "+525512340002", "name": "Maria Lopez Diaz"},
    {"id": "p1000001-0000-0000-0000-000000000003", "phone": "+525512340003", "name": "Carlos Ramirez Silva"},
]

# Demo visits with steps
VISITS = [
    {
        "id": "v1000001-0000-0000-0000-000000000001",
        "patient_idx": 0,
        "ticket": "A-001",
        "status": "in_progress",
        "steps": [
            {"area_idx": 0, "order": 1, "status": "in_progress", "est_wait": 12},
            {"area_idx": 2, "order": 2, "status": "pending", "est_wait": 8},
        ],
    },
    {
        "id": "v1000001-0000-0000-0000-000000000002",
        "patient_idx": 1,
        "ticket": "A-002",
        "status": "in_progress",
        "steps": [
            {"area_idx": 1, "order": 1, "status": "in_progress", "est_wait": 18},
            {"area_idx": 3, "order": 2, "status": "pending", "est_wait": 6},
            {"area_idx": 0, "order": 3, "status": "pending", "est_wait": 14},
        ],
    },
    {
        "id": "v1000001-0000-0000-0000-000000000003",
        "patient_idx": 2,
        "ticket": "A-003",
        "status": "in_progress",
        "steps": [
            {"area_idx": 2, "order": 1, "status": "in_progress", "est_wait": 10},
            {"area_idx": 4, "order": 2, "status": "pending", "est_wait": 9},
        ],
    },
]


async def seed():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # ── Clinic ──
            await session.execute(
                text(
                    "INSERT INTO clinics (id, name, address, active) "
                    "VALUES (:id, :name, :address, :active) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {
                    "id": CLINIC_ID,
                    "name": "Salud Digna Reforma",
                    "address": "Av. Paseo de la Reforma 222, CDMX",
                    "active": True,
                },
            )

            # ── Clinical Areas ──
            for area in AREAS:
                await session.execute(
                    text(
                        "INSERT INTO clinical_areas "
                        "(id, clinic_id, name, study_type, simultaneous_capacity, active, navigation_instructions) "
                        "VALUES (:id, :clinic_id, :name, :study_type, :capacity, :active, :nav) "
                        "ON CONFLICT (id) DO NOTHING"
                    ),
                    {
                        "id": area["id"],
                        "clinic_id": CLINIC_ID,
                        "name": area["name"],
                        "study_type": area["study_type"],
                        "capacity": area["capacity"],
                        "active": True,
                        "nav": area["nav"],
                    },
                )

            # ── Doctors ──
            for doc in DOCTORS:
                await session.execute(
                    text(
                        "INSERT INTO doctors "
                        "(id, employee_id, password_hash, full_name, clinical_area_id, active) "
                        "VALUES (:id, :employee_id, :password_hash, :full_name, :clinical_area_id, :active) "
                        "ON CONFLICT (id) DO NOTHING"
                    ),
                    {
                        "id": doc["id"],
                        "employee_id": doc["employee_id"],
                        "password_hash": PASSWORD_HASH,
                        "full_name": doc["name"],
                        "clinical_area_id": AREAS[doc["area_idx"]]["id"],
                        "active": True,
                    },
                )

            # ── WaitTimeEstimates (initial) ──
            base_waits = {"laboratorio": 12, "ultrasonido": 18, "rayos_x": 10, "electrocardiograma": 6, "papanicolaou": 9, "densitometria": 13, "tomografia": 22}
            for area in AREAS:
                await session.execute(
                    text(
                        "INSERT INTO wait_time_estimates "
                        "(id, clinical_area_id, estimated_minutes, people_in_area, updated_at) "
                        "VALUES (gen_random_uuid(), :area_id, :est, :people, NOW()) "
                        "ON CONFLICT DO NOTHING"
                    ),
                    {
                        "area_id": area["id"],
                        "est": base_waits.get(area["study_type"], 15),
                        "people": 0,
                    },
                )

            # ── Demo Patients ──
            for patient in PATIENTS:
                await session.execute(
                    text(
                        "INSERT INTO patients (id, phone_number, full_name) "
                        "VALUES (:id, :phone, :name) "
                        "ON CONFLICT (id) DO NOTHING"
                    ),
                    {"id": patient["id"], "phone": patient["phone"], "name": patient["name"]},
                )

            # ── Demo Visits + Steps ──
            for visit in VISITS:
                patient = PATIENTS[visit["patient_idx"]]
                await session.execute(
                    text(
                        "INSERT INTO visits "
                        "(id, patient_id, clinic_id, status, has_appointment, is_urgent, ticket_number) "
                        "VALUES (:id, :patient_id, :clinic_id, :status, :has_appt, :urgent, :ticket) "
                        "ON CONFLICT (id) DO NOTHING"
                    ),
                    {
                        "id": visit["id"],
                        "patient_id": patient["id"],
                        "clinic_id": CLINIC_ID,
                        "status": visit["status"],
                        "has_appt": False,
                        "urgent": False,
                        "ticket": visit["ticket"],
                    },
                )

                for step in visit["steps"]:
                    area = AREAS[step["area_idx"]]
                    started_at = "NOW()" if step["status"] == "in_progress" else "NULL"
                    await session.execute(
                        text(
                            f"INSERT INTO visit_steps "
                            f"(id, visit_id, clinical_area_id, step_order, status, estimated_wait_minutes, started_at) "
                            f"VALUES (gen_random_uuid(), :visit_id, :area_id, :order, :status, :est_wait, {started_at}) "
                            f"ON CONFLICT DO NOTHING"
                        ),
                        {
                            "visit_id": visit["id"],
                            "area_id": area["id"],
                            "order": step["order"],
                            "status": step["status"],
                            "est_wait": step["est_wait"],
                        },
                    )

            # ── Patient Events (arrival) ──
            for visit in VISITS:
                await session.execute(
                    text(
                        "INSERT INTO patient_events "
                        "(id, visit_id, event_type, metadata, occurred_at) "
                        "VALUES (gen_random_uuid(), :visit_id, 'arrival', '{}', NOW()) "
                        "ON CONFLICT DO NOTHING"
                    ),
                    {"visit_id": visit["id"]},
                )

    print("\n" + "=" * 60)
    print("SEED DATA CREATED SUCCESSFULLY")
    print("=" * 60)
    print(f"\nCLINIC_ID = {CLINIC_ID}")
    print(f"\nSet in dashboard .env.local:")
    print(f"  NEXT_PUBLIC_CLINIC_ID={CLINIC_ID}")
    print(f"\n── Demo URLs ──")
    print(f"  Dashboard:    http://localhost:3000/dashboard")
    print(f"  Check-in:     http://localhost:3000/checkin/{CLINIC_ID}")
    print(f"  Doctor Login: http://localhost:3000/doctor/login")
    print(f"  Pantalla:     http://localhost:3000/pantalla/{CLINIC_ID}")
    for area in AREAS:
        print(f"  Pantalla {area['name']}: http://localhost:3000/pantalla/{CLINIC_ID}/area/{area['id']}")
    print(f"\n── Doctor Credentials ──")
    for doc in DOCTORS:
        area = AREAS[doc["area_idx"]]
        print(f"  {doc['employee_id']} / 12345678 → {doc['name']} ({area['name']})")
    print(f"\n── Demo Visits ──")
    for visit in VISITS:
        patient = PATIENTS[visit["patient_idx"]]
        print(f"  {visit['ticket']}: {patient['name']} → http://localhost:3000/patient-test/{visit['id']}")
    print("=" * 60 + "\n")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
