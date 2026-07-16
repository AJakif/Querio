from typing import Any, Literal

from pydantic import BaseModel


class Assumption(BaseModel):
    term: str
    resolution: str
    alternatives: list[str] = []
    close_call: bool = False


class PlanResult(BaseModel):
    ambiguity_score: float = 0.0
    assumptions: list[Assumption] = []
    unresolved_terms: list[str] = []
    interpretation: str = ""


# ---------------------------------------------------------------------------
# Aggregator contracts (Slice 3)
# ---------------------------------------------------------------------------


class ChartSpecModel(BaseModel):
    chart_type: str
    title: str
    x_key: str
    y_key: str
    data: list[dict[str, Any]] = []


class Headline(BaseModel):
    value: str
    label: str
    sign: Literal["positive", "negative", "neutral"] = "neutral"


class Claim(BaseModel):
    sentence: str
    type: Literal["row", "computation"]
    cells: list[dict[str, Any]] = []
    operation: str | None = None
    operands: list[float] | None = None
    value: float | None = None


class AnswerSpec(BaseModel):
    headline: Headline
    restatement: str
    chart_spec: ChartSpecModel | None = None
    suppression_reason: str | None = None   # non-null whenever chart_spec is None
    claims: list[Claim] = []
    followups: list[str] = []
    assumptions_ref: list[Assumption] = []  # copied from PlanResult (slice 1)
    dropped_claim_count: int = 0            # slice 4 will set this; defaulted to 0
