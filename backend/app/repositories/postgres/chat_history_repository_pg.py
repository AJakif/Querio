from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger
from app.domain.models import ChatSession, StoredTurn
from app.repositories.base import ChatHistoryRepository

logger = get_logger("repositories.postgres.chat_history")


class PostgresChatHistoryRepository(ChatHistoryRepository):
    def __init__(self, connection_factory=None) -> None:
        self._conn_factory = connection_factory

    def _get_conn(self):
        if self._conn_factory:
            return self._conn_factory()
        from app.core.db import get_connection
        return get_connection()

    async def create_session(
        self,
        account_username: str | None,
        upload_session_id: str | None,
    ) -> ChatSession:
        def _run() -> ChatSession:
            session_id = str(uuid.uuid4())
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO chat.sessions (id, account_username, upload_session_id)
                        VALUES (%s, %s, %s)
                        RETURNING id, account_username, upload_session_id, created_at, updated_at
                        """,
                        (session_id, account_username, upload_session_id),
                    )
                    row = cur.fetchone()
                    conn.commit()
                    return _row_to_session(row)

        return await asyncio.to_thread(_run)

    async def get_session(self, session_id: str) -> ChatSession | None:
        def _run() -> ChatSession | None:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, account_username, upload_session_id, created_at, updated_at
                        FROM chat.sessions WHERE id = %s
                        """,
                        (session_id,),
                    )
                    row = cur.fetchone()
                    if row is None:
                        return None
                    return _row_to_session(row)

        return await asyncio.to_thread(_run)

    async def append_turn(
        self,
        session_id: str,
        question_text: str,
        answer_json: dict[str, Any],
    ) -> StoredTurn:
        def _run() -> StoredTurn:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Compute turn_index atomically in the same statement.
                    cur.execute(
                        """
                        INSERT INTO chat.messages (session_id, turn_index, question_text, answer_json)
                        SELECT %s,
                               COALESCE(MAX(turn_index) + 1, 0),
                               %s,
                               %s::jsonb
                        FROM chat.messages
                        WHERE session_id = %s
                        RETURNING turn_index, question_text, answer_json, created_at
                        """,
                        (
                            session_id,
                            question_text,
                            json.dumps(answer_json),
                            session_id,
                        ),
                    )
                    row = cur.fetchone()
                    # Update sessions.updated_at
                    cur.execute(
                        "UPDATE chat.sessions SET updated_at = now() WHERE id = %s",
                        (session_id,),
                    )
                    conn.commit()
                    return _row_to_turn(row)

        return await asyncio.to_thread(_run)

    async def list_turns(self, session_id: str) -> list[StoredTurn]:
        def _run() -> list[StoredTurn]:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT turn_index, question_text, answer_json, created_at
                        FROM chat.messages
                        WHERE session_id = %s
                        ORDER BY turn_index
                        """,
                        (session_id,),
                    )
                    return [_row_to_turn(row) for row in cur.fetchall()]

        return await asyncio.to_thread(_run)

    async def list_sessions(self, account_username: str | None) -> list[ChatSession]:
        def _run() -> list[ChatSession]:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    if account_username is not None:
                        cur.execute(
                            """
                            SELECT id, account_username, upload_session_id, created_at, updated_at
                            FROM chat.sessions
                            WHERE account_username = %s
                            ORDER BY created_at DESC
                            """,
                            (account_username,),
                        )
                    else:
                        cur.execute(
                            """
                            SELECT id, account_username, upload_session_id, created_at, updated_at
                            FROM chat.sessions
                            ORDER BY created_at DESC
                            """
                        )
                    return [_row_to_session(row) for row in cur.fetchall()]

        return await asyncio.to_thread(_run)


def _row_to_session(row: Any) -> ChatSession:
    # RealDictCursor rows are dict-like; fallback to index for plain tuples.
    if hasattr(row, "keys"):
        return ChatSession(
            id=str(row["id"]),
            account_username=row["account_username"],
            upload_session_id=row["upload_session_id"],
            created_at=_ensure_tz(row["created_at"]),
            updated_at=_ensure_tz(row["updated_at"]),
        )
    return ChatSession(
        id=str(row[0]),
        account_username=row[1],
        upload_session_id=row[2],
        created_at=_ensure_tz(row[3]),
        updated_at=_ensure_tz(row[4]),
    )


def _row_to_turn(row: Any) -> StoredTurn:
    if hasattr(row, "keys"):
        answer_json = row["answer_json"]
        if isinstance(answer_json, str):
            answer_json = json.loads(answer_json)
        return StoredTurn(
            turn_index=row["turn_index"],
            question_text=row["question_text"],
            answer_json=answer_json,
            created_at=_ensure_tz(row["created_at"]),
        )
    answer_json = row[2]
    if isinstance(answer_json, str):
        answer_json = json.loads(answer_json)
    return StoredTurn(
        turn_index=row[0],
        question_text=row[1],
        answer_json=answer_json,
        created_at=_ensure_tz(row[3]),
    )


def _ensure_tz(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
