# INTEGRACION.md — SaludCopilot

> This document is the single source of truth for Day 2 integration.
> Every developer reads this before connecting their module to any other.
> If a contract here differs from what you implemented, flag it immediately
> before connecting — do not silently adapt.

---

## Integration order — follow this exactly

Connecting in the wrong order wastes hours. Follow this sequence:

```
Step 1: CV Worker  → API           (Dev 4 + Dev 1)
Step 2: ML Model   → API           (Dev 3 + Dev 1)
Step 3: API        → Bot           (Dev 1 + Dev 2)
Step 4: Bot        → API           (Dev 2 + Dev 1)
Step 5: API        → Dashboard WS  (Dev 1 + Dev 5)
Step 6: End-to-end test            (all together)
```

Do not proceed to the next step until the current step's smoke test passes.

---

## Step 1 — CV Worker → API

**Who:** Dev 4 connects, Dev 1 verifies receipt.

**What happens:**
CV worker POSTs a people count to the API occupancy endpoint.
API responds with updated wait time estimate.

**Smoke test — manual first:**
```bash
# Start API
docker compose up api

# Simulate CV worker with curl
curl -X POST http://localhost:8000/api/v1/areas/{area_id}/occupancy \
  -H "Authorization: Bearer saludcopilot-internal-token-change-in-prod" \
  -H "Content-Type: application/json" \
  -d '{"people_count": 5, "timestamp": "2026-04-07T10:00:00Z"}'

# Expected:
# {"wait_time_estimate_minutes": 25}
```

**Then run actual CV worker:**
```bash
cd apps/cv && python main.py --demo
# Expected log every 5 seconds:
# "Area {id}: 3 people | Est. wait: 15 min"
```

**Done when:** CV worker logs show successful posts and API returns estimates.

**Common failure:** `area_id` in `.env` does not match any UUID in the database.
Fix: `GET http://localhost:8000/api/v1/areas/` to get real UUIDs,
then update `CAMERA_TO_AREA_MAPPING` in CV `.env`.

---

## Step 2 — ML Model → API

**Who:** Dev 3 delivers model files, Dev 1 integrates.

**What Dev 3 delivers (must be committed before this step):**
```
ml/models/model.pkl
ml/models/encodings.pkl
```

**What Dev 1 creates:**
`apps/api/app/core/predictor_client.py`:

```python
"""
Loads the trained ML model once at API startup.
Import get_predictor() wherever a wait time estimate is needed.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../ml"))
from src.predictor import WaitTimePredictor

_predictor: WaitTimePredictor | None = None

def get_predictor() -> WaitTimePredictor:
    global _predictor
    if _predictor is None:
        _predictor = WaitTimePredictor()
    return _predictor
```

**What Dev 1 changes in `apps/api/app/routers/areas.py`:**
```python
# Remove the placeholder formula:
# estimated_minutes = base_time + (people_count * 5)

# Replace with:
from app.core.predictor_client import get_predictor
from datetime import datetime

now = datetime.now()
estimated_minutes = get_predictor().predict_wait_minutes(
    hour_of_day=now.hour,
    day_of_week=now.weekday(),
    study_type_raw_id=area.study_type,
    clinic_raw_id=str(area.clinic_id),
    simultaneous_capacity=area.simultaneous_capacity,
    current_queue_length=current_queue_length,
    has_appointment=False,
)
```

**Smoke test:**
```bash
# POST occupancy twice with different people_count and different hours
# Estimates should differ based on model, not just count * 5
# Check API logs — should see "WaitTimePredictor" not "placeholder"
```

**Done when:** API logs confirm model predictions, not placeholder.

**Common failure:** `FileNotFoundError` on model files.
Fix: verify `ml/models/model.pkl` exists and is committed.
Check the `sys.path.insert` path resolves correctly.

---

## Step 3 — API → Bot (notifications)

**Who:** Dev 1 calls bot, Dev 2 receives.

**What Dev 1 creates:**
`apps/api/app/services/notification_service.py`:

```python
import httpx
from app.core.config import settings

async def trigger_bot_notification(
    visit_id: str,
    notification_type: str,
    payload: dict,
) -> bool:
    """
    Send notification trigger to bot.
    Never raises — bot failure must not crash the API.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{settings.bot_base_url}/bot/internal/notify",
                headers={"Authorization": f"Bearer {settings.internal_bot_token}"},
                json={
                    "visit_id": visit_id,
                    "notification_type": notification_type,
                    "payload": payload,
                },
            )
            return response.status_code == 200
    except Exception as e:
        print(f"Bot notification failed (non-fatal): {e}")
        return False
```

Add to `app/core/config.py`:
```python
bot_base_url: str = "http://localhost:8001"
internal_bot_token: str = "saludcopilot-internal-token-change-in-prod"
```

**Smoke test:**
```bash
# Terminal 1: start bot
cd apps/bot && python main.py

# Terminal 2: trigger check-in (API calls bot internally)
curl -X POST http://localhost:8000/api/v1/visits/check-in \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+521234567890",
    "clinic_id": "{clinic_uuid}",
    "study_ids": ["{area_uuid}"],
    "has_appointment": false,
    "is_urgent": false
  }'

# Expected in bot logs:
# "Received notification: welcome for visit {id}"
# "Sent welcome message to +521234567890"
```

**Done when:** check-in triggers a visible send in bot logs.

**Common failure:** bot not running when API calls it.
Fix: always start bot before running integration tests.
Bot failure is non-fatal — API returns 201 even if bot notification fails.

---

## Step 4 — Bot → API (check-in and visit context)

**Who:** Dev 2 creates API client, Dev 1 has endpoints ready.

**What Dev 2 creates:**
`apps/bot/services/api_client.py`:

```python
import httpx
from bot.config import settings

async def register_visit(
    phone_number: str,
    clinic_id: str,
    study_ids: list[str],
    has_appointment: bool,
    is_urgent: bool,
) -> dict | None:
    """Call check-in endpoint. Returns visit data or None on failure."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.api_base_url}/api/v1/visits/check-in",
                headers={"Authorization": f"Bearer {settings.internal_api_token}"},
                json={
                    "phone_number": phone_number,
                    "clinic_id": clinic_id,
                    "study_ids": study_ids,
                    "has_appointment": has_appointment,
                    "is_urgent": is_urgent,
                },
            )
            if response.status_code == 201:
                return response.json()
            return None
    except Exception as e:
        print(f"Check-in API call failed: {e}")
        return None

async def get_visit_context(visit_id: str) -> dict | None:
    """Get current visit context for patient message handling."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.api_base_url}/api/v1/visits/{visit_id}/context",
                headers={"Authorization": f"Bearer {settings.internal_api_token}"},
            )
            if response.status_code == 200:
                return response.json()
            return None
    except Exception as e:
        print(f"Visit context API call failed: {e}")
        return None
```

**Smoke test:**
```bash
# Simulate incoming WhatsApp message to bot webhook
curl -X POST http://localhost:8001/bot/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "521234567890",
            "type": "text",
            "text": {"body": "¿Cuánto falta para mi turno?"}
          }]
        }
      }]
    }]
  }'

# Expected in bot logs:
# "Getting context for visit {id}"
# "Claude response: ..."
# "Message sent to +521234567890"
```

**Done when:** bot receives message, calls API, sends Claude response.

---

## Step 5 — API → Dashboard (WebSocket)

**Who:** Dev 1 implements broadcast, Dev 5 connects.

**What Dev 1 adds to `apps/api/app/routers/dashboard.py`:**

```python
from fastapi import WebSocket, WebSocketDisconnect

# Module-level connection registry
_connections: dict[str, list[WebSocket]] = {}

@app.websocket("/ws/dashboard/{clinic_id}")
async def dashboard_websocket_endpoint(
    websocket: WebSocket,
    clinic_id: str,
):
    await websocket.accept()
    _connections.setdefault(clinic_id, []).append(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep alive, ignore messages
    except WebSocketDisconnect:
        _connections[clinic_id].remove(websocket)

async def broadcast_to_clinic(clinic_id: str, event: dict) -> None:
    """
    Push event to all dashboard connections for this clinic.
    Call this from any endpoint that changes state visible on dashboard.
    """
    disconnected = []
    for ws in _connections.get(clinic_id, []):
        try:
            await ws.send_json(event)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        _connections[clinic_id].remove(ws)
```

**Where to call `broadcast_to_clinic`:**

In `POST /areas/{area_id}/occupancy`:
```python
await broadcast_to_clinic(str(area.clinic_id), {
    "event": "wait_time_updated",
    "area_id": str(area_id),
    "data": {
        "estimated_minutes": estimated_minutes,
        "people_count": people_count,
    },
})
```

In `POST /visits/{visit_id}/advance-step`:
```python
await broadcast_to_clinic(str(visit.clinic_id), {
    "event": "visit_updated",
    "visit_id": str(visit_id),
    "data": {
        "status": new_status,
        "current_area": next_area_name,
    },
})
```

**Smoke test:**
```bash
# Open dashboard at http://localhost:3000
# Check browser console: "WebSocket connected — EN VIVO"

# Trigger occupancy update
curl -X POST http://localhost:8000/api/v1/areas/{area_id}/occupancy \
  -H "Authorization: Bearer saludcopilot-internal-token-change-in-prod" \
  -d '{"people_count": 7, "timestamp": "2026-04-07T11:00:00Z"}'

# Expected: dashboard wait time chart updates without page refresh
# Dashboard console: "Event: wait_time_updated — area {id}"
```

**Done when:** occupancy POST causes visible real-time update in dashboard.

---

## Step 6 — Full end-to-end test

**Who:** all developers together.

**Setup:**
```bash
# Start everything in order
docker compose up postgres redis
docker compose up api
cd apps/bot && python main.py          # new terminal
cd apps/dashboard && pnpm dev          # new terminal
cd apps/cv && python main.py --demo    # new terminal
```

**The demo run — execute exactly as Day 3 presentation:**

```
1. Dashboard opens → shows "EN VIVO" badge
2. CV worker demo mode running → area occupancy visible in dashboard
3. Simulate check-in:
   POST /api/v1/visits/check-in with a real phone number on the team
4. That phone receives WhatsApp: welcome + study sequence
5. Dashboard shows new patient in active visits table
6. Advance step:
   POST /api/v1/visits/{visit_id}/advance-step
7. Phone receives WhatsApp: turn notification
8. Dashboard updates: patient moved to next area
9. CV count changes → wait time chart updates in real time
```

**Timing target:** steps 1–9 in under 3 minutes.
This is what the jury sees. Practice until it's smooth.

**If any step fails:** check the troubleshooting section below.

---

## Environment variables — complete reference

All must be populated before Day 2 starts.

**API `.env`:**
```
DATABASE_URL=postgresql+asyncpg://saludcopilot:saludcopilot_dev@localhost:5432/saludcopilot_dev
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=any-32-char-string-for-dev
ENVIRONMENT=development
BOT_BASE_URL=http://localhost:8001
INTERNAL_BOT_TOKEN=saludcopilot-internal-token-change-in-prod
```

**Bot `.env`:**
```
WHATSAPP_TOKEN=your-meta-token
WHATSAPP_PHONE_ID=your-phone-number-id
WHATSAPP_VERIFY_TOKEN=saludcopilot_verify
ANTHROPIC_API_KEY=your-claude-key
API_BASE_URL=http://localhost:8000
INTERNAL_API_TOKEN=saludcopilot-internal-token-change-in-prod
INTERNAL_BOT_TOKEN=saludcopilot-internal-token-change-in-prod
```

**CV `.env`:**
```
API_BASE_URL=http://localhost:8000
INTERNAL_CV_TOKEN=saludcopilot-internal-token-change-in-prod
CAMERA_TO_AREA_MAPPING={"0": "paste-area-uuid-here"}
```

**Dashboard `.env.local`:**
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_CLINIC_ID=paste-clinic-uuid-here
```

**Shared internal token:** all services use the same value.
`saludcopilot-internal-token-change-in-prod` for local dev.
Everyone must use the exact same string — mismatch = 401 errors.

---

## Services startup order

```bash
1. docker compose up postgres redis     # infrastructure first
2. cd apps/api && alembic upgrade head  # only after schema changes
3. docker compose up api                # API before anything else
4. cd apps/bot && python main.py        # needs API running
5. cd apps/dashboard && pnpm dev        # needs API for WebSocket
6. cd apps/cv && python main.py --demo  # last — recovers from API downtime
```

---

## Troubleshooting

**401 on any internal endpoint**
All `INTERNAL_*_TOKEN` values must match exactly across all `.env` files.
Check: `grep INTERNAL apps/api/.env apps/bot/.env apps/cv/.env`

**Bot not receiving API notifications**
`BOT_BASE_URL` in API `.env` must point to bot port (default 8001).
Bot must be running before you test check-in.

**WebSocket shows "DEMO" instead of "EN VIVO"**
API WebSocket endpoint not implemented yet, or API not running.
Dashboard falls back to mock — expected until Step 5 complete.

**CV posts succeed but dashboard does not update**
`broadcast_to_clinic` not called from occupancy endpoint.
Verify it is called after `WaitTimeEstimate` is updated.

**Model not loading in API**
`ml/models/model.pkl` missing or not committed.
Dev 3 must run training notebook and commit both `.pkl` files.

**Check-in returns 404 on study_ids**
Study UUIDs in the request do not exist in `clinical_areas` table.
Run seed data first: `GET /api/v1/areas/` to verify areas exist.
