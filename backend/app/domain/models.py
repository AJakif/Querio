from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
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
    result_rows: list[dict[str, Any]] | None = None
    verifier_name: str | None = None
    badge_state: str | None = None
    query_id: str | None = None


@dataclass
class ClarifyingQuestion:
    question: str
    options: list[str] = field(default_factory=list)
    conversation_id: str | None = None


@dataclass
class ConfirmFirst:
    """Returned when ambiguity score or scan cost exceeds configured threshold.

    The frontend shows the plan's assumptions as editable chips and waits for
    the user to confirm (or amend) before any SQL executes.
    ``conversation_id`` is the confirm-store key; pass it to POST /ask/confirm.
    """

    plan: "PlanResult"
    scan_cost: int
    conversation_id: str
    gate_reason: str  # "ambiguity" | "cost"


@dataclass
class ProxyAlternative:
    label: str
    question: str


@dataclass
class ClarifyResponse:
    """ROUTE-3: question asked about data absent from the schema.

    Contains a plain-language dataset statement, ≥2 schema-grounded proxy
    alternatives the user can submit as follow-up questions, and an add_data
    flag signalling that the upload flow is available as an escape hatch.
    """

    statement: str
    unresolved_terms: list[str]
    alternatives: list[ProxyAlternative]
    add_data: bool = True
    conversation_id: str | None = None


@dataclass
class ExampleQuestion:
    question: str
    answer_shape: str
    hint: str


class BadgeState(str, Enum):
    unverified = "unverified"
    verified = "verified"
    needs_recheck = "needs_recheck"
    disputed = "disputed"


class VerificationEventType(str, Enum):
    verified = "verified"
    disputed = "disputed"
    needs_recheck = "needs_recheck"


@dataclass
class VerificationEvent:
    event_type: VerificationEventType
    actor: str
    timestamp: datetime
    fingerprints: list[Fingerprint] = field(default_factory=list)
    drift_reason: str | None = None


@dataclass
class QueryRecord:
    id: str
    sql: str
    author: str
    question: str = ""
    fingerprints_at_run: list[Fingerprint] = field(default_factory=list)
    history: list[VerificationEvent] = field(default_factory=list)

    def badge_state(self) -> BadgeState:
        """Compute badge state by replaying append-only history. Never mutated directly."""
        state = BadgeState.unverified
        for event in self.history:
            if event.event_type == VerificationEventType.verified:
                state = BadgeState.verified
            elif event.event_type == VerificationEventType.disputed:
                if state == BadgeState.verified:
                    state = BadgeState.disputed
            elif event.event_type == VerificationEventType.needs_recheck:
                if state == BadgeState.verified:
                    state = BadgeState.needs_recheck
        return state

    def last_verification(self) -> VerificationEvent | None:
        for event in reversed(self.history):
            if event.event_type == VerificationEventType.verified:
                return event
        return None


@dataclass
class Account:
    username: str
    password_hash: str
    is_owner: bool = False


@dataclass
class ChatSession:
    id: str
    account_username: str | None
    upload_session_id: str | None
    created_at: datetime
    updated_at: datetime
    dataset_expired_at: datetime | None = None


@dataclass
class StoredTurn:
    turn_index: int
    question_text: str
    answer_json: dict[str, Any]
    created_at: datetime


@dataclass
class SchemaSummary:
    table_name: str
    row_count: int
    date_span_start: str | None
    date_span_end: str | None
    key_dimension_count: int
    headline_label: str
    headline_value: float
    examples: list[ExampleQuestion] = field(default_factory=list)
