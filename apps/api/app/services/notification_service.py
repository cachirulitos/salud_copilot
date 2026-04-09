import json
import logging
import uuid

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def trigger_bot_notification(
    visit_id: str,
    notification_type: str,
    payload: dict,
    clinic_id: str | None = None,
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

    success = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(url, json=body, headers=headers)
            if response.status_code == 200:
                success = True
            else:
                logger.warning(
                    "Bot notification failed: status=%d body=%s",
                    response.status_code,
                    response.text,
                )
    except httpx.ConnectError:
        logger.warning("Bot unreachable for visit %s — skipping notification", visit_id)
    except Exception:
        logger.exception("Bot notification error for visit %s", visit_id)

    await _record_notification(visit_id, notification_type, payload, success)

    if not success and clinic_id:
        try:
            from app.routers.dashboard_ws import broadcast_to_clinic
            await broadcast_to_clinic(
                clinic_id,
                {
                    "event": "notification_failed",
                    "data": {"visit_id": visit_id, "type": notification_type},
                },
            )
        except Exception:
            logger.exception("broadcast notification_failed error for visit %s", visit_id)

    return success


async def _record_notification(
    visit_id: str,
    notification_type: str,
    payload: dict,
    success: bool,
) -> None:
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.models import Notification, NotificationStatus, NotificationType

        ntype = NotificationType(notification_type) if notification_type in NotificationType._value2member_map_ else NotificationType.WELCOME

        async with AsyncSessionLocal() as db:
            db.add(
                Notification(
                    visit_id=uuid.UUID(visit_id),
                    notification_type=ntype,
                    content=json.dumps(payload),
                    status=NotificationStatus.SENT if success else NotificationStatus.FAILED,
                )
            )
            await db.commit()
    except Exception:
        logger.exception("Failed to record notification row for visit %s", visit_id)
