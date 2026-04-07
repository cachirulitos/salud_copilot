import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def trigger_bot_notification(
    visit_id: str,
    notification_type: str,
    payload: dict,
) -> bool:
    """
    Sends a notification trigger to the bot via HTTP.
    Never raises — bot failure must not break the API flow.
    Returns True if the bot responded 200, False otherwise.
    """
    url = f"{settings.bot_base_url}/bot/internal/notify"
    headers = {"Authorization": f"Bearer {settings.internal_bot_token}"}
    body = {
        "visit_id": visit_id,
        "notification_type": notification_type,
        "payload": payload,
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(url, json=body, headers=headers)
            if response.status_code == 200:
                return True
            logger.warning(
                "Bot notification failed: status=%d body=%s",
                response.status_code,
                response.text,
            )
            return False
    except Exception:
        logger.exception("Bot notification error for visit %s", visit_id)
        return False
