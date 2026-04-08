import logging
from datetime import datetime, timezone

import httpx

from config import settings

logger = logging.getLogger(__name__)

HTTP_TIMEOUT_SECONDS = 5.0
OCCUPANCY_PATH = "api/v1/areas/{area_id}/occupancy"


async def publish_people_count(area_id: str, people_count: int) -> int | None:
    """POST the current people count to the API and return the estimated wait minutes."""
    url = f"{settings.api_base_url}{OCCUPANCY_PATH.format(area_id=area_id)}"
    print(f"Publishing to {url}")
    headers = {"Authorization": f"Bearer {settings.internal_cv_token}"}
    payload = {
        "people_count": people_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json()
                estimated_minutes = data["wait_time_estimate_minutes"]
                print(
                    f"Area {area_id}: {people_count} personas "
                    f"| Espera est: {estimated_minutes} min"
                )
                return estimated_minutes
            logger.warning(
                "publish_people_count failed: status=%d area=%s",
                response.status_code,
                area_id,
            )
            return None
    except Exception:
        logger.exception("Connection error publishing count for area %s", area_id)
        return None