import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.core.database import get_db

# Import overview data helper to push initial state
from app.routers.dashboard import _get_overview_data

router = APIRouter()
logger = logging.getLogger(__name__)

_connections: dict[str, list[WebSocket]] = {}

@router.websocket("/{clinic_id}")
async def dashboard_websocket(websocket: WebSocket, clinic_id: str, db: AsyncSession = Depends(get_db)):
    """Accept a WebSocket connection and keep it alive for real-time dashboard events."""
    await websocket.accept()

    try:
        clinic_uuid = uuid.UUID(clinic_id)
    except ValueError:
        await websocket.close(code=1008, reason="Invalid clinic_id")
        return

    _connections.setdefault(clinic_id, []).append(websocket)

    try:
        # Push initial state immediately upon connection
        overview_data = await _get_overview_data(clinic_uuid, db)
        await websocket.send_json({"event": "overview_snapshot", "data": overview_data})
        
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _connections[clinic_id].remove(websocket)
        if not _connections[clinic_id]:
            del _connections[clinic_id]

# ── Broadcast helpers (en ws.py o donde tengas broadcast_to_clinic) ──────────

async def broadcast_checkin_created(
    clinic_id: str,
    visit_id: uuid.UUID,
    patient_id: uuid.UUID,
    patient_name: str,          # ← agregar este parámetro
    sequence_response: list,
    total_estimated_minutes: int,
) -> None:
    first_step = sequence_response[0] if sequence_response else None
    await broadcast_to_clinic(
        clinic_id,
        {
            "event": "checkin_created",
            "data": {
                "visit_id": str(visit_id),
                "patient_id": str(patient_id),
                "patient_name": patient_name,
                "current_area": first_step.area_name if first_step else "—",
                "step_order": 1,
                "total_steps": len(sequence_response),
                "waiting_since_minutes": 0,
                "visit_status": "pending",
                "sequence": [
                    {
                        "order": s.order,
                        "area_name": s.area_name,
                        "estimated_wait_minutes": s.estimated_wait_minutes,
                        "rule_applied": s.rule_applied,
                    }
                    for s in sequence_response
                ],
                "timestamp": datetime.utcnow().isoformat(),
            },
        },
    )

async def broadcast_visit_step_updated(
    clinic_id: str,
    visit_id: uuid.UUID,
    visit_status: str,
    completed_step: dict,
    next_step: dict | None,
) -> None:
    """Notifica al dashboard que un paciente avanzó de step."""
    await broadcast_to_clinic(
        clinic_id,
        {
            "event": "visit_step_updated",
            "data": {
                "visit_id": str(visit_id),
                "visit_status": visit_status,
                "completed_step": completed_step,   # {order, area_name, actual_wait_minutes}
                "next_step": next_step,              # {order, area_name, estimated_wait_minutes} | None
                "timestamp": datetime.utcnow().isoformat(),
            },
        },
    )

async def broadcast_patient_arriving(
    clinic_id: str,
    visit_id: uuid.UUID,
    patient_name: str,
    from_area: str,
    to_area: str,
    next_area_after: str | None,
    estimated_wait_minutes: int,
) -> None:
    """Notify all dashboards that a patient is moving to the next area."""
    await broadcast_to_clinic(
        clinic_id,
        {
            "event": "patient_arriving",
            "data": {
                "visit_id": str(visit_id),
                "patient_name": patient_name,
                "from_area": from_area,
                "to_area": to_area,
                "next_area_after": next_area_after,
                "estimated_wait_minutes": estimated_wait_minutes,
                "timestamp": datetime.utcnow().isoformat(),
            },
        },
    )

async def broadcast_wait_updated(clinic_id: str, area_id: str, area_name: str, new_wait_minutes: int) -> None:
    await broadcast_to_clinic(clinic_id, {
        "type": "wait_time_updated",
        "area_id": area_id,
        "area_name": area_name,
        "wait_minutes": new_wait_minutes,
    })


async def broadcast_alert_resolved(clinic_id: str, alert_id: str) -> None:
    await broadcast_to_clinic(clinic_id, {
        "type": "alert_resolved",
        "alert_id": alert_id,
    })


import asyncio

async def broadcast_to_clinic(clinic_id: str, event: dict) -> None:
    """Send an event to all WebSocket connections for a given clinic."""
    active_connections = _connections.get(clinic_id, [])
    if not active_connections:
        return

    async def _send(connection: WebSocket):
        try:
            await connection.send_json(event)
            return None
        except Exception:
            return connection

    results = await asyncio.gather(*[_send(c) for c in active_connections])
    
    dead_connections = [c for c in results if c is not None]

    if dead_connections:
        for connection in dead_connections:
            logger.warning("Removing dead WebSocket for clinic %s", clinic_id)
            try:
                active_connections.remove(connection)
            except ValueError:
                pass
                
        if clinic_id in _connections and not _connections[clinic_id]:
            del _connections[clinic_id]
