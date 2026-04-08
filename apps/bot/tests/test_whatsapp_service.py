import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from services.whatsapp_service import (
    WHATSAPP_API_URL,
    send_text_message,
    send_welcome_message,
)
from config import settings


def _mock_client(status_code=200):
    response = MagicMock()
    response.status_code = status_code
    response.text = "ok"
    client = AsyncMock()
    client.post.return_value = response
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


def test_send_text_message_calls_correct_url():
    client = _mock_client(200)
    with patch("services.whatsapp_service.httpx.AsyncClient", return_value=client):
        result = asyncio.run(send_text_message("+5215500001111", "Hola"))

    assert result is True
    client.post.assert_called_once()
    args, kwargs = client.post.call_args
    expected_url = WHATSAPP_API_URL.format(phone_id=settings.whatsapp_phone_id)
    assert args[0] == expected_url
    assert kwargs["json"]["to"] == "525500001111"
    assert kwargs["json"]["text"]["body"] == "Hola"


def test_send_text_message_returns_false_on_http_error():
    client = _mock_client(401)
    with patch("services.whatsapp_service.httpx.AsyncClient", return_value=client):
        result = asyncio.run(send_text_message("+5215500001111", "Hola"))

    assert result is False


def test_send_welcome_message_formats_sequence_correctly():
    client = _mock_client(200)
    sequence = [
        {"area_name": "Laboratorio", "estimated_wait_minutes": 15},
        {"area_name": "Ultrasonido", "estimated_wait_minutes": 20},
    ]
    with patch("services.whatsapp_service.httpx.AsyncClient", return_value=client):
        result = asyncio.run(
            send_welcome_message("+5215500001111", "Juan", sequence, 35)
        )

    assert result is True
    body = client.post.call_args[1]["json"]["text"]["body"]
    assert "¡Hola Juan!" in body
    assert "Laboratorio" in body
    assert "Ultrasonido" in body
    assert "~35 minutos" in body


def test_send_welcome_message_numbers_are_sequential():
    client = _mock_client(200)
    sequence = [
        {"area_name": "Laboratorio", "estimated_wait_minutes": 15},
        {"area_name": "Ultrasonido", "estimated_wait_minutes": 20},
        {"area_name": "Rayos X", "estimated_wait_minutes": 12},
    ]
    with patch("services.whatsapp_service.httpx.AsyncClient", return_value=client):
        asyncio.run(
            send_welcome_message("+5215500001111", "Ana", sequence, 47)
        )

    body = client.post.call_args[1]["json"]["text"]["body"]
    assert "1. Laboratorio" in body
    assert "2. Ultrasonido" in body
    assert "3. Rayos X" in body
