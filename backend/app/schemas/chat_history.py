from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.ask import AnswerResponse


class CreateChatSessionRequest(BaseModel):
    account_username: str | None = None
    upload_session_id: str | None = None


class ChatSessionResponse(BaseModel):
    chat_session_id: str
    account_username: str | None
    upload_session_id: str | None
    created_at: datetime
    updated_at: datetime


class StoredTurnResponse(BaseModel):
    turn_index: int
    question: str
    answer: AnswerResponse
    created_at: datetime


class ChatSessionHistoryResponse(BaseModel):
    session: ChatSessionResponse
    turns: list[StoredTurnResponse]


class ChatSessionSummaryResponse(BaseModel):
    chat_session_id: str
    account_username: str | None
    created_at: datetime
    updated_at: datetime
    turn_count: int
    preview_question: str | None
