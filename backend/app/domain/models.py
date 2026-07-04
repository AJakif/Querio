from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ChartType(str, Enum):
    bar = "bar"
    line = "line"
    histogram = "histogram"


@dataclass
class ChartSpec:
    chart_type: ChartType
    title: str
    data: list[dict[str, Any]]
    x_key: str
    y_key: str


@dataclass
class SqlQuery:
    sql: str
    explanation: str


@dataclass
class Question:
    text: str


@dataclass
class Answer:
    text: str
    chart: ChartSpec | None = None
    sql: SqlQuery | None = None
    conversation_id: str | None = None


@dataclass
class ClarifyingQuestion:
    question: str
    options: list[str] = field(default_factory=list)
    conversation_id: str | None = None
