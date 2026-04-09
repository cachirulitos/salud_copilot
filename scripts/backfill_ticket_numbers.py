"""
Backfill ticket_number for visits that don't have one.
Assigns A-001, A-002... per clinic per day, ordered by created_at.

Run from repo root:
  docker compose exec api python scripts/backfill_ticket_numbers.py
"""
import asyncio
from collections import defaultdict
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.models import Visit


async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Visit).order_by(Visit.clinic_id, Visit.created_at)
        )
        all_visits = result.scalars().all()

        # count per (clinic_id, date) across ALL visits (including already-numbered)
        counters: dict[tuple, int] = defaultdict(int)
        for v in all_visits:
            if v.ticket_number:
                continue  # skip already-assigned
            key = (str(v.clinic_id), v.created_at.date())
            counters[key] += 1
            v.ticket_number = f"A-{counters[key]:03d}"

        await db.commit()
        total = sum(counters.values())
        print(f"Backfilled {total} visits.")


asyncio.run(main())
