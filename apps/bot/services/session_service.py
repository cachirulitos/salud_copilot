import json
import logging
from datetime import datetime, timezone

import redis.asyncio as aioredis

from config import settings

logger = logging.getLogger(__name__)

SESSION_TTL_SECONDS = 14400  # 4 hours

_redis = aioredis.from_url(settings.redis_url)


def _session_key(phone_number: str) -> str:
    return f"session:{phone_number}"


async def save_session(
    phone_number: str,
    visit_id: str,
    bot_mode: str,
    current_step_order: int,
) -> None:
    """Persist a new bot session in Redis with a 4-hour TTL."""
    session_data = {
        "visit_id": visit_id,
        "bot_mode": bot_mode,
        "current_step_order": current_step_order,
        "awaiting_preparation_confirmation": False,
        "welcome_payload": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await _redis.set(
        _session_key(phone_number), json.dumps(session_data), ex=SESSION_TTL_SECONDS
    )


async def get_session(phone_number: str) -> dict | None:
    """Return the session dict for a phone number, or None if not found."""
    raw = await _redis.get(_session_key(phone_number))
    if raw is None:
        return None
    return json.loads(raw)


async def delete_session(phone_number: str) -> None:
    """Remove a session from Redis."""
    await _redis.delete(_session_key(phone_number))


async def update_session_step(phone_number: str, new_step_order: int) -> None:
    """Update current_step_order without resetting the TTL."""
    await _update_session_field(
        phone_number, "current_step_order", new_step_order
    )


async def set_awaiting_preparation(phone_number: str, value: bool) -> None:
    """Toggle the awaiting_preparation_confirmation flag without resetting TTL."""
    await _update_session_field(
        phone_number, "awaiting_preparation_confirmation", value
    )


async def save_welcome_payload(phone_number: str, welcome_payload: dict) -> None:
    """Store welcome message data in the session for deferred sending."""
    await _update_session_field(phone_number, "welcome_payload", welcome_payload)


async def set_awaiting_area_feedback(
    phone_number: str,
    area_name: str,
) -> None:
    """
    Store the area name pending feedback from the patient.
    Pass empty string to clear the feedback state.
    """
    await _update_session_field(phone_number, "awaiting_area_feedback", area_name)


async def _update_session_field(
    phone_number: str, field: str, value: object
) -> None:
    """Update a single field in the session, preserving the remaining TTL."""
    redis_key = _session_key(phone_number)
    remaining_ttl = await _redis.ttl(redis_key)
    if remaining_ttl < 0:
        logger.warning(
            "Session not found or expired for %s while updating %s",
            phone_number,
            field,
        )
        return
    raw = await _redis.get(redis_key)
    if raw is None:
        logger.warning(
            "Session key disappeared for %s while updating %s",
            phone_number,
            field,
        )
        return
    session_data = json.loads(raw)
    session_data[field] = value
    await _redis.set(redis_key, json.dumps(session_data), ex=remaining_ttl)
