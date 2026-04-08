import logging

import httpx

from config import settings

logger = logging.getLogger(__name__)

HTTP_TIMEOUT_SECONDS = 10.0
CHECK_IN_PATH = "/api/v1/visits/check-in"
VISIT_CONTEXT_PATH = "/api/v1/visits/{visit_id}/context"


async def register_visit(
    phone_number: str,
    clinic_id: str,
    study_ids: list[str],
    has_appointment: bool,
    is_urgent: bool,
) -> dict | None:
    """Register a new visit via the API check-in endpoint. Returns the response dict or None."""
    url = f"{settings.api_base_url}{CHECK_IN_PATH}"
    headers = {"Authorization": f"Bearer {settings.internal_api_token}"}
    request_body = {
        "phone_number": phone_number,
        "clinic_id": clinic_id,
        "study_ids": study_ids,
        "has_appointment": has_appointment,
        "is_urgent": is_urgent,
    }

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=request_body, headers=headers)
            if response.status_code == 201:
                return response.json()
            logger.warning(
                "register_visit failed: status=%d body=%s",
                response.status_code,
                response.text,
            )
            return None
    except Exception:
        logger.exception("register_visit error for %s", phone_number)
        return None


async def get_visit_context(visit_id: str) -> dict | None:
    """Fetch the current visit context from the API. Returns the response dict or None."""
    url = f"{settings.api_base_url}{VISIT_CONTEXT_PATH.format(visit_id=visit_id)}"
    headers = {"Authorization": f"Bearer {settings.internal_api_token}"}

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            logger.warning(
                "get_visit_context failed: status=%d body=%s",
                response.status_code,
                response.text,
            )
            return None
    except Exception:
        logger.exception("get_visit_context error for visit %s", visit_id)
        return None
