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
    _connections.setdefault(clinic_id, []).append(websocket)
    
    try:
        # Push initial state immediately upon connection
        overview_data = await _get_overview_data(uuid.UUID(clinic_id), db)
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

async def broadcast_to_clinic(clinic_id: str, event: dict) -> None:
    """Send an event to all WebSocket connections for a given clinic."""
    active_connections = _connections.get(clinic_id, [])
    dead_connections: list[WebSocket] = []
    for connection in active_connections:
        try:
            await connection.send_json(event)
        except Exception:
            logger.warning("Removing dead WebSocket for clinic %s", clinic_id)
            dead_connections.append(connection)
    for connection in dead_connections:
        active_connections.remove(connection)
    if clinic_id in _connections and not _connections[clinic_id]:
        del _connections[clinic_id]
