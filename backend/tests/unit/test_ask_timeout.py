"""Regression test: a pipeline timeout/cancellation must degrade to a graceful
AnswerResponse, not an unhandled 500. asyncio.CancelledError is a BaseException
(not Exception) in Python 3.8+, so it silently bypasses ask_service's internal
`except Exception` guards and must be caught at the route boundary instead."""

from fastapi.testclient import TestClient

from app.api.routes.ask import get_ask_service
from app.main import app


class _TimesOutService:
    async def answer(self, **kwargs):
        raise TimeoutError("simulated pipeline timeout")

    async def answer_confirmed(self, **kwargs):
        raise TimeoutError("simulated pipeline timeout")


async def _override_timeout_service():
    return _TimesOutService()


def test_ask_returns_graceful_answer_on_timeout_instead_of_500():
    app.dependency_overrides[get_ask_service] = _override_timeout_service
    try:
        with TestClient(app) as client:
            response = client.post("/api/ask", json={"question": "How many orders?"})
        assert response.status_code == 200
        assert "took too long" in response.json()["answer"].lower()
    finally:
        app.dependency_overrides.pop(get_ask_service, None)


def test_ask_confirm_returns_graceful_answer_on_timeout_instead_of_500():
    app.dependency_overrides[get_ask_service] = _override_timeout_service
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/ask/confirm", json={"conversation_id": "abc123", "amendments": []}
            )
        assert response.status_code == 200
        assert "took too long" in response.json()["answer"].lower()
    finally:
        app.dependency_overrides.pop(get_ask_service, None)
