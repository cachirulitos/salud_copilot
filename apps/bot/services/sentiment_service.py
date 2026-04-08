FRUSTRATION_KEYWORDS = frozenset({
    "cuánto falta", "cuanto falta", "mucho tiempo", "mucho rato",
    "ya llevo", "siguen tardando", "cuándo me toca", "cuando me toca",
    "tardando mucho", "demasiado tiempo", "hora que me atienden",
    "nunca me atienden", "están tardando", "no avanzan",
    "por qué tarda", "porque tarda", "tanto tiempo",
})

ESCALATION_THRESHOLD = 1  # Escalate after 1 frustration signal

def detect_frustration(message: str) -> bool:
    """
    Return True if the message contains frustration signals.
    Case-insensitive. Does not use LLM — purely keyword-based for speed.
    """
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in FRUSTRATION_KEYWORDS)


async def notify_dashboard_frustration(
    visit_id: str,
    phone_number: str,
    message: str,
    estimated_wait_minutes: int,
    api_base_url: str,
    api_token: str,
) -> None:
    """
    POST frustration alert to API dashboard endpoint.
    Non-blocking — logs failure without raising.
    """
    import httpx
    import logging
    logger = logging.getLogger(__name__)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{api_base_url}/api/v1/visits/{visit_id}/alerts",
                headers={"Authorization": f"Bearer {api_token}"},
                json={
                    "alert_type": "patient_frustration",
                    "phone_number": phone_number,
                    "message_snippet": message[:100],
                    "estimated_wait_minutes": estimated_wait_minutes,
                },
            )
    except Exception:
        logger.warning("Could not send frustration alert for visit %s", visit_id)
