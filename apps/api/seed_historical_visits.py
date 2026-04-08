"""
seed_historical_visits.py
=========================
Generates 90 days of realistic visit history for the CULIACAN clinic.

Usage:
    cd apps/api
    python seed_historical_visits.py
"""

import asyncio
import random
import sys
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

API_DIR = Path(__file__).resolve().parent
sys.path.append(str(API_DIR))
ROOT_DIR = API_DIR.parent.parent
sys.path.append(str(ROOT_DIR))

import redis.asyncio as redis
from sqlalchemy import select, delete
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import (
    ClinicalArea,
    Patient,
    PatientEvent,
    Visit,
    VisitStatus,
    VisitStep,
    VisitStepStatus,
    WaitTimeEstimate,
)

# ── Stable UUID helpers (same pattern as seed_real_data.py) ──────────────────

def get_stable_uuid(prefix: str, numeric_id: int) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"saludcopilot.com/{prefix}/{numeric_id}")


CULIACAN_CLINIC_ID = get_stable_uuid("clinic", 1)

# Area UUIDs: get_stable_uuid(f"area_{clinic_idx}", study_id)
# clinic_idx=1, study_ids: 2=laboratorio, 5=rayos_x, 6=ultrasonido, 9=electrocardiograma
AREA_IDS = {
    "laboratorio":        get_stable_uuid("area_1", 2),
    "rayos_x":            get_stable_uuid("area_1", 5),
    "ultrasonido":        get_stable_uuid("area_1", 6),
    "electrocardiograma": get_stable_uuid("area_1", 9),
}

# ── Distribution parameters ───────────────────────────────────────────────────

AREA_WEIGHTS = {
    "laboratorio":        0.45,
    "rayos_x":            0.20,
    "ultrasonido":        0.20,
    "electrocardiograma": 0.15,
}

WAIT_PARAMS = {
    "laboratorio":        {"mean": 18, "std": 6},
    "rayos_x":            {"mean": 12, "std": 4},
    "ultrasonido":        {"mean": 22, "std": 7},
    "electrocardiograma": {"mean": 8,  "std": 3},
}

# Hour slots: (start_hour, end_hour, weight)
HOUR_SLOTS = [
    (8,  10, 0.40),
    (10, 13, 0.35),
    (13, 16, 0.25),
]

APPOINTMENT_RATE = 0.15
APPOINTMENT_WAIT_FACTOR = 0.75
MONDAY_MORNING_FACTOR = 1.4

VISITS_PER_DAY_MIN = 80
VISITS_PER_DAY_MAX = 150

TODAY = date(2026, 4, 8)
START_DATE = TODAY - timedelta(days=90)

BATCH_SIZE = 200  # commit every N visits to avoid huge transactions

# ── Helpers ───────────────────────────────────────────────────────────────────

def random_hour_minute(is_monday_morning: bool) -> tuple[int, int]:
    """Pick a random hour:minute according to the defined distribution."""
    slot = random.choices(HOUR_SLOTS, weights=[s[2] for s in HOUR_SLOTS])[0]
    start_h, end_h, _ = slot
    total_minutes = (end_h - start_h) * 60
    offset = random.randint(0, total_minutes - 1)
    h = start_h + offset // 60
    m = offset % 60
    return h, m


def sample_wait_minutes(study_type: str, has_appointment: bool, is_monday_morning: bool) -> int:
    params = WAIT_PARAMS[study_type]
    minutes = random.gauss(params["mean"], params["std"])
    if is_monday_morning:
        minutes *= MONDAY_MORNING_FACTOR
    if has_appointment:
        minutes *= APPOINTMENT_WAIT_FACTOR
    return max(1, round(minutes))


def make_patient_phone(index: int) -> str:
    # Stable phone numbers to avoid unique constraint violations across runs
    base = 6000000000 + index
    return f"+52{base}"


# ── Main seeder ───────────────────────────────────────────────────────────────

async def seed_historical_visits() -> None:
    print("Starting historical visit seed for CULIACAN (90 days)…")

    # Pre-generate a pool of patients (phone numbers must be unique)
    # We'll reuse them across days — real patients visit multiple times
    PATIENT_POOL_SIZE = 3000

    async with AsyncSessionLocal() as db:
        # Verify the clinic areas exist
        for name, area_id in AREA_IDS.items():
            result = await db.execute(select(ClinicalArea).where(ClinicalArea.id == area_id))
            area = result.scalar_one_or_none()
            if area is None:
                print(f"ERROR: Area '{name}' not found (id={area_id}). Run seed_real_data.py first.")
                return

        # ── 1. Upsert patient pool ────────────────────────────────────────────
        print(f"Ensuring patient pool of {PATIENT_POOL_SIZE}…")
        patient_ids: list[uuid.UUID] = []
        for i in range(PATIENT_POOL_SIZE):
            phone = make_patient_phone(i)
            result = await db.execute(select(Patient).where(Patient.phone_number == phone))
            patient = result.scalar_one_or_none()
            if patient is None:
                patient = Patient(
                    id=uuid.uuid4(),
                    phone_number=phone,
                    full_name=f"Paciente Histórico {i:04d}",
                )
                db.add(patient)
            patient_ids.append(patient.id)
        await db.commit()
        print(f"  {PATIENT_POOL_SIZE} patients ready.")

        # ── 2. Generate visits day by day ─────────────────────────────────────
        area_keys = list(AREA_IDS.keys())
        area_weights = [AREA_WEIGHTS[k] for k in area_keys]

        # Track actual_wait_minutes per area for the LAST day (for WaitTimeEstimate)
        last_day_waits: dict[str, list[int]] = {k: [] for k in area_keys}

        total_visits = 0
        pending_objects: list = []

        current = START_DATE
        while current < TODAY:
            # Skip Sundays (weekday() == 6)
            if current.weekday() == 6:
                current += timedelta(days=1)
                continue

            is_monday = current.weekday() == 0
            n_visits = random.randint(VISITS_PER_DAY_MIN, VISITS_PER_DAY_MAX)

            is_last_day = (current == TODAY - timedelta(days=1))
            if is_last_day:
                last_day_waits = {k: [] for k in area_keys}

            for _ in range(n_visits):
                # Pick area
                study_type = random.choices(area_keys, weights=area_weights)[0]
                area_id = AREA_IDS[study_type]

                # Pick arrival time
                hour, minute = random_hour_minute(is_monday)
                is_monday_morning = is_monday and hour < 10

                arrived_at = datetime(
                    current.year, current.month, current.day,
                    hour, minute, random.randint(0, 59),
                    tzinfo=timezone.utc,
                )

                has_appointment = random.random() < APPOINTMENT_RATE
                actual_wait = sample_wait_minutes(study_type, has_appointment, is_monday_morning)

                started_at = arrived_at
                completed_at = arrived_at + timedelta(minutes=actual_wait)

                patient_id = random.choice(patient_ids)
                visit_id = uuid.uuid4()
                step_id = uuid.uuid4()

                visit = Visit(
                    id=visit_id,
                    patient_id=patient_id,
                    clinic_id=CULIACAN_CLINIC_ID,
                    status=VisitStatus.COMPLETED,
                    has_appointment=has_appointment,
                    is_urgent=False,
                    completed_at=completed_at,
                )
                # Override created_at via direct attribute (server_default is skipped on explicit set)
                visit.created_at = arrived_at

                step = VisitStep(
                    id=step_id,
                    visit_id=visit_id,
                    clinical_area_id=area_id,
                    step_order=1,
                    status=VisitStepStatus.COMPLETED,
                    estimated_wait_minutes=WAIT_PARAMS[study_type]["mean"],
                    actual_wait_minutes=actual_wait,
                    started_at=started_at,
                    completed_at=completed_at,
                )

                arrival_event = PatientEvent(
                    id=uuid.uuid4(),
                    visit_id=visit_id,
                    event_type="arrival",
                    event_metadata={"area": study_type, "has_appointment": has_appointment},
                )
                arrival_event.occurred_at = arrived_at

                step_event = PatientEvent(
                    id=uuid.uuid4(),
                    visit_id=visit_id,
                    event_type="step_completed",
                    event_metadata={
                        "area": study_type,
                        "actual_wait_minutes": actual_wait,
                        "step_order": 1,
                    },
                )
                step_event.occurred_at = completed_at

                pending_objects.extend([visit, step, arrival_event, step_event])

                if is_last_day:
                    last_day_waits[study_type].append(actual_wait)

            total_visits += n_visits

            # Commit in batches
            if len(pending_objects) >= BATCH_SIZE * 4:  # 4 objects per visit
                for obj in pending_objects:
                    db.add(obj)
                await db.commit()
                pending_objects.clear()
                print(f"  … committed up to {current.isoformat()} | total visits so far: {total_visits}")

            current += timedelta(days=1)

        # Final flush
        if pending_objects:
            for obj in pending_objects:
                db.add(obj)
            await db.commit()
            pending_objects.clear()

        print(f"\nTotal visits inserted: {total_visits}")

        # ── 3. WaitTimeEstimate for each area (last day's averages) ───────────
        print("Writing WaitTimeEstimate rows (last day averages)…")
        for study_type, waits in last_day_waits.items():
            area_id = AREA_IDS[study_type]
            if not waits:
                avg_minutes = WAIT_PARAMS[study_type]["mean"]
                people = 0
            else:
                avg_minutes = round(sum(waits) / len(waits))
                people = len(waits)

            # Delete existing estimates for this area to avoid duplicates
            await db.execute(
                delete(WaitTimeEstimate).where(WaitTimeEstimate.clinical_area_id == area_id)
            )
            estimate = WaitTimeEstimate(
                id=uuid.uuid4(),
                clinical_area_id=area_id,
                estimated_minutes=avg_minutes,
                people_in_area=people,
            )
            db.add(estimate)
            print(f"  {study_type}: avg={avg_minutes} min, people_in_area={people}")

        await db.commit()

    print("\n✅ Historical seed complete.")


QUEUE_OCCUPANCY = {
    "laboratorio":        (4, 6),
    "rayos_x":            (2, 3),
    "ultrasonido":        (3, 4),
    "electrocardiograma": (1, 2),
}


async def seed_redis_queues() -> None:
    print("Seeding Redis queues with current occupancy…")
    client = redis.from_url(settings.redis_url)
    now = time.time()

    try:
        for study_type, (lo, hi) in QUEUE_OCCUPANCY.items():
            area_id = AREA_IDS[study_type]
            key = f"queue:{area_id}"
            n = random.randint(lo, hi)
            members: dict[str, float] = {}
            for i in range(n):
                fake_visit_id = str(uuid.uuid4())
                timestamp = now - random.uniform(0, 30 * 60)
                members[fake_visit_id] = timestamp
            await client.delete(key)
            await client.zadd(key, members)
            print(f"  {study_type}: {n} entries in {key}")
    finally:
        await client.aclose()

    print("✅ Redis queues seeded.")


if __name__ == "__main__":
    async def main() -> None:
        await seed_historical_visits()
        await seed_redis_queues()

    asyncio.run(main())
