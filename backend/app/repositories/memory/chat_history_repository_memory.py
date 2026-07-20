from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.domain.models import ChatSession, StoredTurn
from app.repositories.base import ChatHistoryRepository


class InMemoryChatHistoryRepository(ChatHistoryRepository):
    def __init__(self) -> None:
        self._sessions: dict[str, ChatSession] = {}
        self._turns: dict[str, list[StoredTurn]] = {}

    async def create_session(
        self,
        account_username: str | None,
        upload_session_id: str | None,
    ) -> ChatSession:
        now = datetime.now(timezone.utc)
        session = ChatSession(
            id=str(uuid.uuid4()),
            account_username=account_username,
            upload_session_id=upload_session_id,
            created_at=now,
            updated_at=now,
        )
        self._sessions[session.id] = session
        self._turns[session.id] = []
        return session

    async def get_session(self, session_id: str) -> ChatSession | None:
        return self._sessions.get(session_id)

    async def append_turn(
        self,
        session_id: str,
        question_text: str,
        answer_json: dict[str, Any],
    ) -> StoredTurn:
        turns = self._turns.get(session_id)
        if turns is None:
            raise KeyError(f"session {session_id!r} not found")
        turn_index = len(turns)
        now = datetime.now(timezone.utc)
        turn = StoredTurn(
            turn_index=turn_index,
            question_text=question_text,
            answer_json=answer_json,
            created_at=now,
        )
        turns.append(turn)
        # update session's updated_at
        session = self._sessions[session_id]
        self._sessions[session_id] = ChatSession(
            id=session.id,
            account_username=session.account_username,
            upload_session_id=session.upload_session_id,
            created_at=session.created_at,
            updated_at=now,
        )
        return turn

    async def list_turns(self, session_id: str) -> list[StoredTurn]:
        return list(self._turns.get(session_id, []))

    async def list_sessions(self, account_username: str | None) -> list[ChatSession]:
        sessions = list(self._sessions.values())
        if account_username is not None:
            sessions = [s for s in sessions if s.account_username == account_username]
        return sessions

    async def mark_dataset_expired(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        now = datetime.now(timezone.utc)
        self._sessions[session_id] = ChatSession(
            id=session.id,
            account_username=session.account_username,
            upload_session_id=session.upload_session_id,
            created_at=session.created_at,
            updated_at=session.updated_at,
            dataset_expired_at=now,
        )

    async def list_sessions_with_expired_datasets(
        self, ttl_days: int
    ) -> list[ChatSession]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=ttl_days)
        return [
            s
            for s in self._sessions.values()
            if s.upload_session_id is not None
            and s.dataset_expired_at is None
            and s.updated_at < cutoff
        ]
