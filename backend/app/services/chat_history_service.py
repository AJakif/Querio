from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.domain.exceptions import ChatSessionNotFoundError
from app.domain.models import ChatSession, StoredTurn
from app.repositories.base import ChatHistoryRepository

logger = get_logger("services.chat_history")


class ChatHistoryService:
    def __init__(self, repo: ChatHistoryRepository) -> None:
        self._repo = repo

    async def start_session(
        self,
        account_username: str | None,
        upload_session_id: str | None,
    ) -> ChatSession:
        session = await self._repo.create_session(account_username, upload_session_id)
        logger.info("Chat session created", extra={"session_id": session.id})
        return session

    async def record_turn(
        self,
        session_id: str,
        question_text: str,
        answer_json: dict[str, Any],
    ) -> StoredTurn:
        session = await self._repo.get_session(session_id)
        if session is None:
            raise ChatSessionNotFoundError(
                f"Chat session {session_id!r} not found; cannot record turn."
            )
        turn = await self._repo.append_turn(session_id, question_text, answer_json)
        logger.info(
            "Turn recorded",
            extra={"session_id": session_id, "turn_index": turn.turn_index},
        )
        return turn

    async def get_history(
        self, session_id: str
    ) -> tuple[ChatSession, list[StoredTurn]] | None:
        session = await self._repo.get_session(session_id)
        if session is None:
            return None
        turns = await self._repo.list_turns(session_id)
        return session, turns

    async def list_sessions(
        self, account_username: str | None
    ) -> list[ChatSession]:
        return await self._repo.list_sessions(account_username)

    async def list_session_summaries(
        self, account_username: str | None
    ) -> list[tuple[ChatSession, int, str | None]]:
        """Return (session, turn_count, first_question) for listing/summary use."""
        sessions = await self._repo.list_sessions(account_username)
        summaries: list[tuple[ChatSession, int, str | None]] = []
        for session in sessions:
            turns = await self._repo.list_turns(session.id)
            preview = turns[0].question_text if turns else None
            summaries.append((session, len(turns), preview))
        return summaries
