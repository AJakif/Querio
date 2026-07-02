from pydantic import BaseModel
from typing import Any


class AskRequest(BaseModel):
    question: str


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


class ClarifyingQuestionResponse(BaseModel):
    type: str = "clarifying_question"
    question: str
    options: list[str] = []
