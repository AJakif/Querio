from pydantic import BaseModel, Field
from typing import Any, Literal

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
    emphasis_target: str | None = None
    y_keys: list[str] | None = None


class SqlQueryResponse(BaseModel):
    sql: str
    explanation: str


class AssumptionResponse(BaseModel):
    term: str
    resolution: str
    alternatives: list[str] = []
    close_call: bool = False


class PlanResultResponse(BaseModel):
    ambiguity_score: float = 0.0
    assumptions: list[AssumptionResponse] = []
    unresolved_terms: list[str] = []
    interpretation: str = ""


class DependencyResponse(BaseModel):
    table: str
    column: str


class FingerprintResponse(BaseModel):
    table: str
    column: str
    schema_hash: str
    value_hash: str | None = None


class ValidationResultResponse(BaseModel):
    dependency_set: list[DependencyResponse] = []
    fingerprints: list[FingerprintResponse] = []
    scan_cost: int = 0


class HeadlineResponse(BaseModel):
    value: str
    label: str
    sign: str = "neutral"


class ClaimResponse(BaseModel):
    sentence: str
    type: str
    cells: list[dict[str, Any]] = []
    operation: str | None = None
    operands: list[float] | None = None
    value: float | None = None


class AnswerSpecResponse(BaseModel):
    response_type: Literal['stat', 'chart'] = 'stat'
    headline: HeadlineResponse
    restatement: str
    chart_spec: ChartSpecResponse | None = None
    suppression_reason: str | None = None
    claims: list[ClaimResponse] = []
    followups: list[str] = []
    assumptions_ref: list[AssumptionResponse] = []
    dropped_claim_count: int = 0


class AnswerResponse(BaseModel):
    type: str = "answer"
    answer: str
    chart: ChartSpecResponse | None = None
    sql: SqlQueryResponse | None = None
    conversation_id: str | None = None
    plan: PlanResultResponse | None = None
    validation: ValidationResultResponse | None = None
    answer_spec: AnswerSpecResponse | None = None
    dropped_claim_count: int = 0
    result_rows: list[dict[str, Any]] | None = None


class ClarifyingQuestionResponse(BaseModel):
    type: str = "clarifying_question"
    question: str
    options: list[str] = []
    conversation_id: str = Field(default_factory=lambda: str(_uuid.uuid4()))


class ProxyAlternativeResponse(BaseModel):
    label: str
    question: str


class ClarifyResponseResponse(BaseModel):
    type: str = "clarify"
    statement: str
    unresolved_terms: list[str] = []
    alternatives: list[ProxyAlternativeResponse] = []
    add_data: bool = True
    conversation_id: str | None = None


class ConfirmFirstResponse(BaseModel):
    type: str = "confirm_first"
    conversation_id: str
    plan: PlanResultResponse
    scan_cost: int = 0
    gate_reason: str  # "ambiguity" | "cost"


class AssumptionAmendment(BaseModel):
    term: str
    resolution: str


class ConfirmRequest(BaseModel):
    conversation_id: str
    amendments: list[AssumptionAmendment] = []
