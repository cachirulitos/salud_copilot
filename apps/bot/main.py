import asyncio
import logging

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, Header, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from config import settings
from services.api_client import get_visit_context, register_visit
from services.llm_service import generate_response
from services.session_service import (
    delete_session,
    get_session,
    save_session,
    save_welcome_payload,
    set_awaiting_area_feedback,
    set_awaiting_preparation,
    update_session_step,
)
from services.educational_content import get_educational_content
from services.sentiment_service import detect_frustration, notify_dashboard_frustration
from services.whatsapp_service import (
    send_area_feedback_request,
    send_results_notification,
    send_text_message,
    send_turn_notification,
    send_visit_feedback_request,
    send_welcome_message,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="SaludCopilot Bot",
    description="WhatsApp bot for Salud Digna patient assistance",
    version="0.1.0",
)


# ── Constants ──────────────────────────────────────────────────────────────


PREPARATION_REQUIRED = {
    "laboratorio": "ayuno de 8 horas",
    "papanicolaou": "no usar desodorante y abstinencia sexual 48 horas previas",
    "tomografia": "preparación específica indicada por el médico",
    "resonancia": "preparación específica indicada por el médico",
}

CHECKIN_PREFIX = "CHECKIN_"

PREPARATION_CONFIRM_WORDS = {"sí", "si", "yes", "claro", "listo"}
PREPARATION_DENY_WORDS = {"no", "no pude", "no completé"}

WAIT_TIME_DELTA_THRESHOLD_MINUTES = 5

POSITIVE_FEEDBACK = {"😊", "excelente", "bien", "muy bien", "genial", "bueno"}
NEGATIVE_FEEDBACK = {"😞", "mala", "mal", "pésimo", "terrible", "horrible"}
NEUTRAL_FEEDBACK  = {"😐", "regular", "más o menos", "ok"}

RESCHEDULE_MESSAGE = (
    "Entendido. Para obtener resultados precisos te recomendamos "
    "reagendar tu cita. Puedes llamar a la clínica o visitar "
    "saluddigna.com para agendar."
)

NO_SESSION_MESSAGE = (
    "No tenemos una visita activa registrada para tu número. "
    "Por favor acércate a recepción para registrarte."
)

LLM_FALLBACK_MESSAGE = (
    "Disculpa, no pude procesar tu mensaje en este momento. "
    "Por favor intenta de nuevo en unos segundos."
)

MESSAGE_LOCK_TTL_SECONDS = 10

_redis_client = aioredis.from_url(settings.redis_url)


# ── Schemas ─────────────────────────────────────────────────────────────────


class NotifyRequest(BaseModel):
    visit_id: str
    notification_type: str
    payload: dict


# ── Webhook verification ────────────────────────────────────────────────────


@app.get("/bot/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """Verify the Meta webhook subscription using the shared verify token."""
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return PlainTextResponse(content=hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


# ── Incoming WhatsApp messages ──────────────────────────────────────────────


@app.post("/bot/webhook")
async def incoming_webhook(request: Request):
    """Receive incoming WhatsApp messages from Meta. Always returns 200."""
    try:
        webhook_body = await request.json()
        for entry in webhook_body.get("entry", []):
            for change in entry.get("changes", []):
                messages = change.get("value", {}).get("messages", [])
                for incoming_message in messages:
                    await _handle_incoming_message(incoming_message)
    except Exception:
        logger.exception("Error processing incoming webhook")

    return {"status": "ok"}


async def _handle_incoming_message(incoming_message: dict) -> None:
    """Route an incoming WhatsApp message through preparation, session, and LLM flows."""
    if incoming_message.get("type") != "text":
        return

    raw_phone = incoming_message.get("from", "")
    phone_number = raw_phone if raw_phone.startswith("+") else f"+{raw_phone}"
    message_text = incoming_message.get("text", {}).get("body", "").strip()

    if not raw_phone or not message_text:
        return

    # Acquire lock to prevent race conditions on concurrent messages
    lock_key = f"processing:{phone_number}"
    lock_acquired = await _redis_client.set(lock_key, "1", nx=True, ex=MESSAGE_LOCK_TTL_SECONDS)
    if not lock_acquired:
        return

    try:
        await _process_message(phone_number, message_text)
    finally:
        await _redis_client.delete(lock_key)


async def _process_message(phone_number: str, message_text: str) -> None:
    """Core message processing: check-in via QR, preparation flow, then LLM."""

    # ── WhatsApp-based check-in (QR → wa.me deep link) ────────────────
    if message_text.startswith(CHECKIN_PREFIX):
        await _handle_checkin_message(phone_number, message_text)
        return

    session = await get_session(phone_number)

    if session is None:
        await send_text_message(phone_number, NO_SESSION_MESSAGE)
        return

    if session.get("awaiting_preparation_confirmation"):
        await _handle_preparation_response(phone_number, message_text, session)
        return

    if session.get("awaiting_area_feedback"):
        await _handle_feedback_response(
            phone_number,
            message_text,
            session["awaiting_area_feedback"],
            visit_id=session["visit_id"],
        )
        return

    visit_context = await get_visit_context(session["visit_id"])
    if visit_context is None:
        await send_text_message(phone_number, NO_SESSION_MESSAGE)
        return

    # Detect and escalate frustration in real time
    if detect_frustration(message_text):
        current_step = visit_context.get("current_step", {})
        estimated_wait = current_step.get("estimated_wait_minutes", 0)
        await notify_dashboard_frustration(
            visit_id=session["visit_id"],
            phone_number=phone_number,
            message=message_text,
            estimated_wait_minutes=estimated_wait,
            api_base_url=settings.api_base_url,
            api_token=settings.internal_api_token,
        )

    llm_response = await generate_response(message_text, visit_context)
    if llm_response is None:
        await send_text_message(phone_number, LLM_FALLBACK_MESSAGE)
        return

    await send_text_message(phone_number, llm_response)


async def _handle_preparation_response(
    phone_number: str, message_text: str, session: dict
) -> None:
    """Process the patient's yes/no response to the preparation question."""
    await set_awaiting_preparation(phone_number, False)
    message_lower = message_text.lower()

    if any(word in message_lower for word in PREPARATION_CONFIRM_WORDS):
        await _send_deferred_welcome(phone_number, session)
    elif any(word in message_lower for word in PREPARATION_DENY_WORDS):
        await send_text_message(phone_number, RESCHEDULE_MESSAGE)
    else:
        await _send_deferred_welcome(phone_number, session)


async def _handle_feedback_response(
    phone_number: str,
    message_text: str,
    area_name: str,
    visit_id: str,
) -> None:
    """Process emoji or text feedback for a completed area."""
    await set_awaiting_area_feedback(phone_number, "")

    text_lower = message_text.lower()
    if any(w in text_lower for w in NEGATIVE_FEEDBACK):
        # Escalate to dashboard
        await _notify_negative_feedback(visit_id, area_name, message_text)
        await send_text_message(
            phone_number,
            "Lamentamos que tu experiencia no haya sido la mejor. "
            "Hemos notificado al equipo para mejorar. ¡Gracias por tu comentario!"
        )
    else:
        await send_text_message(
            phone_number,
            "¡Gracias por tu comentario! Continuamos con tu siguiente estudio."
        )

async def _notify_negative_feedback(
    visit_id: str,
    area_name: str,
    comment: str,
) -> None:
    """Send negative feedback alert to the API dashboard endpoint."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{settings.api_base_url}/api/v1/visits/{visit_id}/feedback",
                headers={"Authorization": f"Bearer {settings.internal_api_token}"},
                json={"area_name": area_name, "sentiment": "negative", "comment": comment},
            )
    except Exception:
        logger.warning("Could not notify dashboard of negative feedback for visit %s", visit_id)


async def _send_deferred_welcome(phone_number: str, session: dict) -> None:
    """Send the welcome message that was deferred pending preparation confirmation."""
    visit_id = session.get("visit_id", "")
    context = await get_visit_context(visit_id)
    if context is None:
        logger.warning("Could not get visit context for deferred welcome: %s", visit_id)
        return

    patient_name = context.get("patient_name", "Paciente")
    welcome_data = session.get("welcome_payload", {})
    sequence = welcome_data.get("sequence", [])
    total_minutes = welcome_data.get("total_estimated_minutes", 0)
    await send_welcome_message(phone_number, patient_name, sequence, total_minutes)


# ── WhatsApp check-in handler ──────────────────────────────────────────────


async def _handle_checkin_message(phone_number: str, message_text: str) -> None:
    """Parse CHECKIN_{clinic_id}_{area_id} and register the visit via the API.

    DEPRECATED: QR self-check-in is replaced by reception-first flow.
    This handler is kept for backward compatibility but will be removed.
    """
    logger.warning(
        "DEPRECATED QR check-in used by %s — patients should register at reception",
        phone_number,
    )
    parts = message_text.strip().split("_", 2)
    # Expected: ["CHECKIN", clinic_id, area_id]
    if len(parts) != 3:
        await send_text_message(
            phone_number,
            "El formato del mensaje no es valido. "
            "Por favor escanea el codigo QR nuevamente.",
        )
        return

    _, clinic_id, area_id = parts

    # Check for existing active session (avoid duplicate check-ins)
    existing_session = await get_session(phone_number)
    if existing_session is not None:
        context = await get_visit_context(existing_session["visit_id"])
        if context is None:
            await delete_session(phone_number)
        else:
            await send_text_message(
                phone_number,
                "Ya tienes una visita activa. "
                "Escribe cualquier mensaje para consultar tu estado.",
            )
            return

    result = await register_visit(
        phone_number=phone_number,
        clinic_id=clinic_id,
        study_ids=[area_id],
        has_appointment=False,
        is_urgent=False,
    )

    if result is None:
        await send_text_message(
            phone_number,
            "No pudimos registrar tu visita. "
            "Por favor acercate a recepcion para ayuda.",
        )
        return

    # The API triggers a welcome notification to this bot via /bot/internal/notify,
    # which will send the welcome message with the sequence. Nothing else to do here.
    logger.info("WhatsApp check-in completed for %s, visit_id=%s", phone_number, result.get("visit_id"))


# ── Internal notification endpoint ──────────────────────────────────────────


@app.post("/bot/internal/notify")
async def internal_notify(
    body: NotifyRequest,
    authorization: str = Header(None),
):
    """Receive notification triggers from the API and dispatch to WhatsApp."""
    expected_token = f"Bearer {settings.internal_bot_token}"
    if authorization != expected_token:
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized", "code": "UNAUTHORIZED"},
        )

    handlers = {
        "welcome": _handle_welcome,
        "turn_ready": _handle_turn_ready,
        "results_ready": _handle_results_ready,
        "wait_time_updated": _handle_wait_time_updated,
    }

    handler = handlers.get(body.notification_type)
    if handler is None:
        return JSONResponse(
            status_code=400,
            content={"error": "Unknown type", "code": "UNKNOWN_NOTIFICATION_TYPE"},
        )

    await handler(body.visit_id, body.payload)
    return {"status": "sent"}


# ── Notification handlers ──────────────────────────────────────────────────


async def _handle_welcome(visit_id: str, payload: dict) -> None:
    """Send welcome message or preparation check, and create the bot session."""
    context = await get_visit_context(visit_id)
    if context is None:
        logger.warning("Could not get visit context for welcome: %s", visit_id)
        return

    phone_number = context.get("patient_phone", "")
    if phone_number.startswith("+0000000"):
        logger.info("Skipping WhatsApp for no-phone patient: %s", visit_id)
        return
    patient_name = context.get("patient_name", "Paciente")
    sequence = payload.get("sequence", [])
    total_minutes = payload.get("total_estimated_minutes", 0)
    has_appointment = payload.get("has_appointment", False)
    bot_mode = "proactive" if has_appointment else "reactive"

    await save_session(phone_number, visit_id, bot_mode, current_step_order=1)

    preparations_needed = _find_required_preparations(sequence, has_appointment)

    if preparations_needed:
        await save_welcome_payload(phone_number, {
            "sequence": sequence,
            "total_estimated_minutes": total_minutes,
        })
        await set_awaiting_preparation(phone_number, True)
        await _send_preparation_question(phone_number, patient_name, preparations_needed)
    else:
        await send_welcome_message(phone_number, patient_name, sequence, total_minutes)


def _find_required_preparations(
    sequence: list[dict], has_appointment: bool
) -> list[str]:
    """Return list of preparation instructions needed for the given sequence."""
    if not has_appointment:
        return []
    preparations = []
    for step in sequence:
        area_name_lower = step.get("area_name", "").lower()
        for study_type, preparation_text in PREPARATION_REQUIRED.items():
            if study_type in area_name_lower:
                preparations.append(preparation_text)
    return preparations


async def _send_preparation_question(
    phone_number: str,
    patient_name: str,
    preparations_needed: list[str],
) -> None:
    """Ask the patient to confirm they completed the required preparations."""
    preparation_list = "\n".join(f"  • {prep}" for prep in preparations_needed)
    message = (
        f"¡Hola {patient_name}! Antes de registrarte, confirma que completaste:\n"
        f"{preparation_list}\n"
        f"¿Lo completaste? Responde Sí o No."
    )
    await send_text_message(phone_number, message)


async def _handle_turn_ready(visit_id: str, payload: dict) -> None:
    """Notify the patient their turn is approaching and update the session step."""
    context = await get_visit_context(visit_id)
    if context is None:
        logger.warning("Could not get visit context for turn_ready: %s", visit_id)
        return

    phone_number = context.get("patient_phone", "")
    if phone_number.startswith("+0000000"):
        logger.info("Skipping WhatsApp for no-phone patient: %s", visit_id)
        return
    area_name = payload.get("area_name", "")
    estimated_wait = payload.get("estimated_wait_minutes", WAIT_TIME_DELTA_THRESHOLD_MINUTES)
    position = payload.get("position_in_queue", 0)

    navigation = payload.get("navigation_instructions", "")
    await send_turn_notification(
        phone_number,
        area_name,
        estimated_wait,
        position,
        navigation_instructions=navigation,
    )

    # Send educational content after a short delay so messages don't arrive simultaneously
    educational_message = get_educational_content(area_name)
    if educational_message:
        await asyncio.sleep(3)
        await send_text_message(phone_number, educational_message)

    current_step = context.get("current_step", {})
    step_order = current_step.get("order", 1)
    await update_session_step(phone_number, step_order)

    # Request feedback for the area the patient just completed
    completed_area = payload.get("completed_area_name", "")
    if completed_area:
        await asyncio.sleep(5)
        await send_area_feedback_request(phone_number, completed_area)
        await set_awaiting_area_feedback(phone_number, completed_area)


async def _handle_results_ready(visit_id: str, payload: dict) -> None:
    """Send results notification and clean up the session."""
    context = await get_visit_context(visit_id)
    if context is None:
        logger.warning("Could not get visit context for results_ready: %s", visit_id)
        return

    phone_number = context.get("patient_phone", "")
    study_name = payload.get("study_name", "estudio")
    result_url = payload.get("result_url", "")
    recommendation = payload.get("recommendation", "")

    await send_results_notification(phone_number, study_name, result_url, recommendation)

    # Request overall visit feedback before closing session
    await send_visit_feedback_request(phone_number)
    await asyncio.sleep(2)
    await delete_session(phone_number)


async def _handle_wait_time_updated(visit_id: str, payload: dict) -> None:
    """Notify the patient only if the wait time changed by more than the threshold."""
    context = await get_visit_context(visit_id)
    if context is None:
        return

    phone_number = context.get("patient_phone", "")
    new_minutes = payload.get("estimated_minutes", 0)
    previous_minutes = payload.get("previous_minutes", 0)

    delta = abs(new_minutes - previous_minutes)
    if delta > WAIT_TIME_DELTA_THRESHOLD_MINUTES:
        await send_text_message(
            phone_number,
            f"⏱ Actualización: tu tiempo de espera cambió a ~{new_minutes} minutos.",
        )


# ── Health ──────────────────────────────────────────────────────────────────


@app.get("/health", tags=["System"])
async def health():
    """Return service health status."""
    return {"status": "ok", "service": "bot", "version": "0.1.0"}
