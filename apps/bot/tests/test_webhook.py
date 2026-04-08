from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_verification_with_correct_token_returns_challenge():
    response = client.get(
        "/bot/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "saludcopilot_verify",
            "hub.challenge": "test_challenge_123",
        },
    )
    assert response.status_code == 200
    assert response.text == "test_challenge_123"


def test_verification_with_wrong_token_returns_403():
    response = client.get(
        "/bot/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong_token",
            "hub.challenge": "test_challenge_123",
        },
    )
    assert response.status_code == 403
