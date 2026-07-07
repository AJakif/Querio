from pydantic import BaseModel, Field
from typing import Any

import uuid as _uuid

from app.core.logging import get_logger


logger = get_logger("schemas.ask")


class AskRequest(BaseModel):
    question: str
    conversation_id: str | None = None
    clarification_answer: str | None = None
    session_id: str | None = None


class ChartSpecResponse(BaseModel):
    chart_type: str
    title: str
    data: list[dict[str, Any]]
    x_key: str
    y_key: str


class SqlQueryResponse(BaseModel):
    sql: str
    explanation: str


class AnswerResponse(BaseModel):
    type: str = "answer"
    answer: str
    chart: ChartSpecResponse | None = None
    sql: SqlQueryResponse | None = None
    conversation_id: str | None = None


class ClarifyingQuestionResponse(BaseModel):
    type: str = "clarifying_question"
    question: str
    options: list[str] = []
    conversation_id: str = Field(default_factory=lambda: str(_uuid.uuid4()))
