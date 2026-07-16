from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.agent.contracts import AnswerSpec, PlanResult


logger = get_logger("domain.models")


@dataclass
class Dependency:
    table: str
    column: str


@dataclass
class Fingerprint:
    table: str
    column: str
    schema_hash: str
    value_hash: str | None = None


@dataclass
class ValidationResult:
    dependency_set: list[Dependency]
    fingerprints: list[Fingerprint]
    scan_cost: int


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
    plan: PlanResult | None = None
    validation: ValidationResult | None = None
    answer_spec: AnswerSpec | None = None


@dataclass
class ClarifyingQuestion:
    question: str
    options: list[str] = field(default_factory=list)
    conversation_id: str | None = None
