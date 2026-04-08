# SaludCopilot — Module Integration Plan

## What already exists (do NOT rewrite)
- `apps/api/app/services/reorder_sequence_service.py` — reorder logic + rule validation
- `apps/api/app/routers/areas.py` — occupancy endpoint + overtime DoctorAlert creation
- `apps/api/app/routers/dashboard.py` + `dashboard_ws.py` — WS broadcast infrastructure
- `apps/api/app/models/models.py` — all DB models including DoctorAlert, VisitStep, PatientEvent
- `apps/api/app/routers/visits.py` — check-in, advance-step, reorder-sequence endpoints
- `packages/rules_engine` — R-00..R-05, do not modify

---

## Module 1 — Wait-time-aware reordering

**Gap:** `reorder_sequence_service.py` validates rules but ignores current wait times.
Reordering only makes sense if it produces actual time savings.

**File to edit:** `apps/api/app/services/reorder_sequence_service.py`

Add helper `_compute_time_savings(pending_steps, proposed_sequence, area_by_id, db)`:
1. Fetch `WaitTimeEstimate.estimated_minutes` for each pending area from DB
2. Sum estimated minutes for current order → `current_total`
3. Sum estimated minutes for proposed order → `proposed_total`
4. Return `current_total - proposed_total` (positive = savings)

In `reorder_visit_sequence()`, after step 5 (rule validation passes), call the helper.
If savings <= 5 min → return `accepted=False`, do not persist, include new field in response.
If savings > 5 min → continue to step 6 (persist).

**File to edit:** `apps/api/app/schemas/schemas.py`

Add to `ReorderSequenceResponse`:
```python
reorder_rejected_reason: Optional[str] = None
```

No new files. No new endpoints. No migration needed.

---

## Module 2 — Automatic overtime monitor

**Gap:** Overtime alerts only fire when the CV worker posts occupancy to `areas.py`.
If cameras are offline or slow, overtime is never detected.

**New file:** `apps/api/app/services/step_monitor_service.py`

```python
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import VisitStep, VisitStepStatus, DoctorAlert, AlertType, ClinicalArea
from app.core.database import AsyncSessionLocal
from app.routers.dashboard_ws import broadcast_to_clinic
import logging, asyncio

logger = logging.getLogger(__name__)

OVERTIME_MARGIN_PCT = 0.15  # 15% over estimate triggers alert

async def check_overtime_steps() -> None:
    async with AsyncSessionLocal() as db:
        # find all IN_PROGRESS steps
        # for each: compute elapsed, compare vs estimated_wait_minutes * (1 + margin)
        # deduplicate against open DoctorAlert rows (same pattern as areas.py)
        # create DoctorAlert + broadcast_to_clinic if new overtime found
        pass  # Claude Code implements this body

async def run_step_monitor(interval_seconds: int = 60) -> None:
    while True:
        try:
            await check_overtime_steps()
        except Exception:
            logger.exception("step_monitor error")
        await asyncio.sleep(interval_seconds)
```

**File to edit:** `apps/api/app/main.py`

In the `lifespan` function, after `get_predictor()`, add:
```python
from app.services.step_monitor_service import run_step_monitor
asyncio.create_task(run_step_monitor(interval_seconds=60))
```

Do not change VisitStep statuses automatically.
Do not add an HTTP endpoint for this.
Follow the exact DoctorAlert deduplication pattern already in `areas.py` (lines ~95-115).

---

## Module 3 — Real alerts in dashboard overview

**Gap:** `_get_overview_data()` in `dashboard.py` generates mock alerts from area status thresholds.
`DoctorAlert` rows exist in the DB and are unused by the overview response.

**File to edit:** `apps/api/app/routers/dashboard.py`

In `_get_overview_data()`, find the `# Mock alerts` block and replace entirely:

```python
# Add to imports at top of dashboard.py:
from app.models.models import DoctorAlert, AlertType

# Replace mock alerts block with:
alerts_result = await db.execute(
    select(DoctorAlert, ClinicalArea.name.label("area_name"))
    .join(ClinicalArea, DoctorAlert.area_id == ClinicalArea.id)
    .where(DoctorAlert.clinic_id == clinic_id, DoctorAlert.resolved_at.is_(None))
    .order_by(DoctorAlert.triggered_at.desc())
    .limit(20)
)
alerts = [
    {
        "id": str(row.DoctorAlert.id),
        "severity": "critical" if row.DoctorAlert.alert_type == AlertType.OVERTIME else "warning",
        "area_name": row.area_name,
        "message": row.DoctorAlert.message,
        "triggered_at": row.DoctorAlert.triggered_at.isoformat(),
    }
    for row in alerts_result
]
```

No new files. No schema changes. No migration needed.
The frontend `AlertsPanel` already consumes this shape — no frontend changes.

---

## Implementation order

1. **Module 3** — one block replacement, immediate visible impact, lowest risk
2. **Module 2** — new file + two lines in lifespan
3. **Module 1** — extend existing service, most logic

## Hard constraints

- Never touch `packages/rules_engine`
- Never touch `apps/bot/`
- No sync SQLAlchemy calls — always `await db.execute(select(...))`
- `broadcast_to_clinic` lives in `dashboard_ws.py` — import from there only
- HTTP errors: `JSONResponse({"error": "...", "code": "SCREAMING_SNAKE"})`
- Background task errors: `logger.exception(...)`, never raise
- Run `alembic revision --autogenerate` only if a model column is added — none needed here

## Thinking budget
Module 1 savings logic needs careful reasoning (edge cases: no WaitTimeEstimate row, all steps equal cost).
Modules 2 and 3 are mechanical — implement directly without over-reasoning.
