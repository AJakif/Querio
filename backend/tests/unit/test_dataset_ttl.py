"""Load-bearing tests for Dataset TTL cleanup (T9c).

Budget: new feature ≤10 tests (target 3–7). Using 5.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from app.core.config import Settings
from app.domain.models import ChatSession
from app.repositories.memory.chat_history_repository_memory import (
    InMemoryChatHistoryRepository,
)
from app.services.dataset_ttl_service import DatasetTTLService


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_session(
    *,
    upload_session_id: str | None = "upload-abc",
    days_old: int = 35,
    dataset_expired_at: datetime | None = None,
) -> ChatSession:
    now = datetime.now(timezone.utc)
    return ChatSession(
        id="chat-session-1",
        account_username=None,
        upload_session_id=upload_session_id,
        created_at=now - timedelta(days=days_old),
        updated_at=now - timedelta(days=days_old),
        dataset_expired_at=dataset_expired_at,
    )


# ---------------------------------------------------------------------------
# Test 1: Config default and env override
# ---------------------------------------------------------------------------


def test_config_dataset_ttl_default() -> None:
    """dataset_ttl_days defaults to 30 and is overridable via env var."""
    s = Settings()
    assert s.dataset_ttl_days == 30

    s2 = Settings(dataset_ttl_days=7)
    assert s2.dataset_ttl_days == 7


# ---------------------------------------------------------------------------
# Test 2: Cleanup drops schema and marks session expired
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cleanup_marks_expired_and_drops_schema() -> None:
    """run_cleanup: expired session gets schema dropped and dataset_expired_at set."""
    repo = InMemoryChatHistoryRepository()
    session = _make_session(days_old=35)  # 35 days old, TTL is 30 → eligible
    repo._sessions[session.id] = session
    repo._turns[session.id] = []

    mock_session_manager = MagicMock()
    mock_session_manager.drop_session_schema = AsyncMock(return_value=None)

    service = DatasetTTLService(
        chat_history_repo=repo, session_manager=mock_session_manager
    )
    cleaned = await service.run_cleanup(ttl_days=30)

    assert cleaned == [session.id]
    mock_session_manager.drop_session_schema.assert_called_once_with(
        session.upload_session_id
    )

    updated = await repo.get_session(session.id)
    assert updated is not None
    assert updated.dataset_expired_at is not None


# ---------------------------------------------------------------------------
# Test 3: Cleanup skips sessions within TTL
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cleanup_skips_fresh_session() -> None:
    """run_cleanup: session updated recently (within TTL) is NOT touched."""
    repo = InMemoryChatHistoryRepository()
    fresh_session = _make_session(days_old=10)  # only 10 days old, TTL is 30 → skip
    repo._sessions[fresh_session.id] = fresh_session
    repo._turns[fresh_session.id] = []

    mock_session_manager = MagicMock()
    mock_session_manager.drop_session_schema = AsyncMock(return_value=None)

    service = DatasetTTLService(
        chat_history_repo=repo, session_manager=mock_session_manager
    )
    cleaned = await service.run_cleanup(ttl_days=30)

    assert cleaned == []
    mock_session_manager.drop_session_schema.assert_not_called()

    session_after = await repo.get_session(fresh_session.id)
    assert session_after is not None
    assert session_after.dataset_expired_at is None


# ---------------------------------------------------------------------------
# Test 4: Ask against expired dataset returns re-upload prompt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ask_expired_dataset_returns_reupload_prompt(client) -> None:
    """POST /ask with session_id + expired chat session returns the re-upload prompt."""
    from app.api.deps import get_chat_history_service
    from app.main import app
    from app.repositories.memory.chat_history_repository_memory import (
        InMemoryChatHistoryRepository,
    )
    from app.services.chat_history_service import ChatHistoryService

    # Create an expired chat session in a fresh repo
    repo = InMemoryChatHistoryRepository()
    expired_session = _make_session(
        upload_session_id="upload-expired",
        days_old=40,
        dataset_expired_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    repo._sessions[expired_session.id] = expired_session
    repo._turns[expired_session.id] = []

    chat_service = ChatHistoryService(repo=repo)

    def _override_chat():
        return chat_service

    app.dependency_overrides[get_chat_history_service] = _override_chat
    try:
        response = client.post(
            "/api/ask",
            json={
                "question": "how many rows?",
                "session_id": "upload-expired",
                "chat_session_id": expired_session.id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "answer"
        assert "re-upload" in data["answer"].lower()
    finally:
        app.dependency_overrides.pop(get_chat_history_service, None)


# ---------------------------------------------------------------------------
# Test 5: Replay (history read) for expired session works read-only
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_replay_expired_session_returns_stored_turns() -> None:
    """get_history returns stored turns even after dataset_expired_at is set.

    This confirms the replay path never touches the live Postgres schema —
    it reads only from chat.sessions / chat.messages (in-memory here).
    """
    repo = InMemoryChatHistoryRepository()
    from app.services.chat_history_service import ChatHistoryService

    # Create a session with an upload_session_id, record a turn, then expire it.
    session = await repo.create_session(
        account_username=None, upload_session_id="upload-xyz"
    )
    await repo.append_turn(
        session.id,
        question_text="how many orders?",
        answer_json={"type": "answer", "answer": "42"},
    )
    # Simulate TTL expiry
    await repo.mark_dataset_expired(session.id)

    service = ChatHistoryService(repo=repo)
    result = await service.get_history(session.id)

    assert result is not None
    chat_session, turns = result
    assert chat_session.dataset_expired_at is not None  # expired
    assert len(turns) == 1
    assert turns[0].question_text == "how many orders?"
    assert turns[0].answer_json["answer"] == "42"
