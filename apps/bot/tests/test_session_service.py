import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from services import session_service
from services.session_service import (
    SESSION_TTL_SECONDS,
    get_session,
    save_session,
    set_awaiting_preparation,
    update_session_step,
)


@pytest.fixture(autouse=True)
def mock_redis():
    mock = AsyncMock()
    with patch.object(session_service, "_redis", mock):
        yield mock


def test_save_session_sets_correct_ttl(mock_redis):
    asyncio.run(save_session("+5215500001111", "visit-abc", "guide", 1))

    mock_redis.set.assert_called_once()
    args, kwargs = mock_redis.set.call_args
    assert args[0] == "session:+5215500001111"
    data = json.loads(args[1])
    assert data["visit_id"] == "visit-abc"
    assert data["bot_mode"] == "guide"
    assert data["current_step_order"] == 1
    assert data["awaiting_preparation_confirmation"] is False
    assert kwargs["ex"] == SESSION_TTL_SECONDS


def test_get_session_returns_none_for_missing_key(mock_redis):
    mock_redis.get.return_value = None

    result = asyncio.run(get_session("+5215500009999"))

    assert result is None
    mock_redis.get.assert_called_once_with("session:+5215500009999")


def test_update_step_preserves_ttl(mock_redis):
    original_data = {
        "visit_id": "visit-abc",
        "bot_mode": "guide",
        "current_step_order": 1,
        "awaiting_preparation_confirmation": False,
        "created_at": "2026-03-31T10:00:00+00:00",
    }
    mock_redis.ttl.return_value = 7200
    mock_redis.get.return_value = json.dumps(original_data)

    asyncio.run(update_session_step("+5215500001111", 3))

    mock_redis.set.assert_called_once()
    args, kwargs = mock_redis.set.call_args
    data = json.loads(args[1])
    assert data["current_step_order"] == 3
    assert kwargs["ex"] == 7200


def test_set_awaiting_preparation_updates_flag(mock_redis):
    original_data = {
        "visit_id": "visit-abc",
        "bot_mode": "guide",
        "current_step_order": 1,
        "awaiting_preparation_confirmation": False,
        "created_at": "2026-03-31T10:00:00+00:00",
    }
    mock_redis.ttl.return_value = 5000
    mock_redis.get.return_value = json.dumps(original_data)

    asyncio.run(set_awaiting_preparation("+5215500001111", True))

    mock_redis.set.assert_called_once()
    args, kwargs = mock_redis.set.call_args
    data = json.loads(args[1])
    assert data["awaiting_preparation_confirmation"] is True
    assert kwargs["ex"] == 5000
