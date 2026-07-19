"""Load-bearing tests for chat history persistence (T9a).

Budget: new feature ≤10 tests.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.domain.exceptions import ChatSessionNotFoundError
from app.repositories.memory.chat_history_repository_memory import (
    InMemoryChatHistoryRepository,
)
from app.services.chat_history_service import ChatHistoryService


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def repo() -> InMemoryChatHistoryRepository:
    return InMemoryChatHistoryRepository()


@pytest.fixture
def service(repo: InMemoryChatHistoryRepository) -> ChatHistoryService:
    return ChatHistoryService(repo=repo)


_FAKE_ANSWER: dict = {"type": "answer", "answer": "42", "chart": None, "sql": None}


# ---------------------------------------------------------------------------
# Repository round-trip
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_repo_round_trip_session_and_turns(repo: InMemoryChatHistoryRepository) -> None:
    """create_session + append_turn(x2) => list_turns returns both in order."""
    session = await repo.create_session(account_username=None, upload_session_id=None)

    t0 = await repo.append_turn(session.id, "q0", _FAKE_ANSWER)
    t1 = await repo.append_turn(session.id, "q1", _FAKE_ANSWER)

    assert t0.turn_index == 0
    assert t1.turn_index == 1

    turns = await repo.list_turns(session.id)
    assert len(turns) == 2
    assert turns[0].question_text == "q0"
    assert turns[1].question_text == "q1"


@pytest.mark.asyncio
async def test_repo_get_session_returns_none_for_unknown(
    repo: InMemoryChatHistoryRepository,
) -> None:
    result = await repo.get_session("nonexistent-id")
    assert result is None


# ---------------------------------------------------------------------------
# Service: record_turn raises on unknown session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_service_record_turn_raises_for_unknown_session(
    service: ChatHistoryService,
) -> None:
    with pytest.raises(ChatSessionNotFoundError):
        await service.record_turn("ghost-id", "question?", _FAKE_ANSWER)


# ---------------------------------------------------------------------------
# End-to-end via HTTP: create session -> ask -> GET history
# ---------------------------------------------------------------------------

@pytest.fixture
def chat_client(client: TestClient) -> TestClient:
    """Reuse the base conftest `client` fixture (ask + chat history deps overridden)."""
    return client


def test_e2e_create_session_ask_get_history(chat_client: TestClient) -> None:
    """POST /session/chat -> POST /ask (with chat_session_id) -> GET /session/chat/{id}
    must return the persisted turn with the same answer shape — no second LLM call.
    """
    # 1. Create a chat session
    resp = chat_client.post("/api/session/chat", json={})
    assert resp.status_code == 201
    session_data = resp.json()
    chat_session_id = session_data["chat_session_id"]
    assert chat_session_id

    # 2. Ask a question referencing the session
    ask_resp = chat_client.post(
        "/api/ask",
        json={"question": "How many orders?", "chat_session_id": chat_session_id},
    )
    assert ask_resp.status_code == 200
    live_answer = ask_resp.json()
    assert live_answer["type"] == "answer"

    # 3. Fetch history — must contain the persisted turn without calling the LLM again
    hist_resp = chat_client.get(f"/api/session/chat/{chat_session_id}")
    assert hist_resp.status_code == 200
    hist = hist_resp.json()

    assert hist["session"]["chat_session_id"] == chat_session_id
    assert len(hist["turns"]) == 1
    turn = hist["turns"][0]
    assert turn["turn_index"] == 0
    assert turn["question"] == "How many orders?"
    # answer shape must match the live response exactly
    assert turn["answer"]["answer"] == live_answer["answer"]
    assert turn["answer"]["type"] == "answer"


def test_get_history_404_for_unknown_session(chat_client: TestClient) -> None:
    resp = chat_client.get("/api/session/chat/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_list_sessions_returns_created_session(chat_client: TestClient) -> None:
    resp = chat_client.post("/api/session/chat", json={})
    assert resp.status_code == 201
    session_id = resp.json()["chat_session_id"]

    list_resp = chat_client.get("/api/session/chat")
    assert list_resp.status_code == 200
    ids = [s["chat_session_id"] for s in list_resp.json()]
    assert session_id in ids


def test_ask_without_chat_session_id_still_works(chat_client: TestClient) -> None:
    """Persistence is opt-in; omitting chat_session_id must not break /ask."""
    resp = chat_client.post("/api/ask", json={"question": "Total revenue?"})
    assert resp.status_code == 200
    assert resp.json()["type"] == "answer"
