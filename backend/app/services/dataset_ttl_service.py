"""Dataset TTL cleanup service (T9c).

Finds chat sessions whose uploaded datasets have exceeded the configured TTL,
drops the session-scoped Postgres schema, and marks the session as expired so
the ask flow can return a user-friendly re-upload prompt instead of a raw DB error.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.repositories.base import ChatHistoryRepository
from app.services.session_manager import SessionManager

logger = get_logger("services.dataset_ttl")


class DatasetTTLService:
    def __init__(
        self,
        chat_history_repo: ChatHistoryRepository,
        session_manager: SessionManager,
    ) -> None:
        self._repo = chat_history_repo
        self._session_manager = session_manager

    async def run_cleanup(self, ttl_days: int) -> list[str]:
        """Drop schemas and mark expiry for all sessions past their TTL.

        Returns the list of chat session IDs that were cleaned up.
        Sessions without an upload_session_id are skipped (nothing to drop).
        """
        candidates = await self._repo.list_sessions_with_expired_datasets(ttl_days)
        cleaned: list[str] = []

        for session in candidates:
            if not session.upload_session_id:
                continue  # safety: skip sessions with no dataset

            logger.info(
                "Expiring dataset for session",
                extra={
                    "chat_session_id": session.id,
                    "upload_session_id": session.upload_session_id,
                    "ttl_days": ttl_days,
                    "updated_at": session.updated_at.isoformat(),
                },
            )

            # Drop the session-scoped Postgres schema.  SessionManager already
            # owns this DDL path (used on upload replace) — we reuse it here.
            await self._session_manager.drop_session_schema(session.upload_session_id)

            # Mark expiry so the ask flow can detect it without re-querying Postgres.
            await self._repo.mark_dataset_expired(session.id)
            cleaned.append(session.id)

        logger.info(
            "Dataset TTL cleanup complete",
            extra={"cleaned_count": len(cleaned), "ttl_days": ttl_days},
        )
        return cleaned
