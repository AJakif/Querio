"""Aggregator: turns query result rows into a structured AnswerSpec.

Mirrors the Planner/SqlGenerator ABC + PydanticAi impl + Fake impl pattern.
No schema tool access needed — the aggregator receives the question, result rows,
and the PlanResult from Slice 1, and produces an AnswerSpec.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from numbers import Number

from pydantic_ai import Agent as PydanticAgent
from pydantic_ai.output import NativeOutput

from app.agent.agent import _build_model
from app.agent.contracts import AnswerSpec, Claim, ChartSpecModel, Headline, PlanResult
from app.agent.prompt_builder import build_dynamic_state, build_static_prefix
from app.agent.prompt_gate import truncate_brief, truncate_for_prompt
from app.agent.prompts import AGGREGATOR_INSTRUCTIONS
from app.core.logging import get_logger


logger = get_logger("agent.aggregator")


class Aggregator(ABC):
    @abstractmethod
    async def aggregate(
        self,
        question: str,
        rows: list[dict],
        plan: PlanResult,
        prior_brief: str = "",
    ) -> AnswerSpec: ...


class PydanticAiAggregator(Aggregator):
    def __init__(
        self,
        model_name: str,
        openai_api_key: str | None = None,
        anthropic_api_key: str | None = None,
        ollama_base_url: str | None = None,
        ollama_num_ctx: int | None = None,
        ollama_request_timeout: float | None = None,
    ):
        logger.info(
            "Initializing Pydantic AI aggregator", extra={"model_name": model_name}
        )
        self._system_prompt = build_static_prefix() + "\n\n" + AGGREGATOR_INSTRUCTIONS
        # The aggregator has no tools to call — it only produces a final structured
        # result — so local models can use the provider's native JSON-schema-constrained
        # decoding instead of function/tool-calling. Verified via direct testing: on
        # qwen2.5:7b, tool-call mode fails 100% of the time (model returns prose instead
        # of a valid tool call against the AnswerSpec schema); NativeOutput mode
        # succeeded 3/3 runs at default retries. Hosted providers keep tool-call mode,
        # which is already reliable there.
        is_ollama = model_name.startswith("ollama:")
        output_type = NativeOutput(AnswerSpec) if is_ollama else AnswerSpec
        self._agent = PydanticAgent(
            _build_model(
                model_name,
                openai_api_key,
                anthropic_api_key,
                ollama_base_url,
                ollama_num_ctx,
                ollama_request_timeout,
            ),
            system_prompt=self._system_prompt,
            output_type=output_type,
            retries=3 if is_ollama else 1,
        )

    async def aggregate(
        self,
        question: str,
        rows: list[dict],
        plan: PlanResult,
        prior_brief: str = "",
    ) -> AnswerSpec:
        from app.core.config import settings

        logger.debug(
            "Running aggregator",
            extra={"question_length": len(question), "row_count": len(rows)},
        )
        user_msg = _build_aggregate_user_msg(
            question, rows, plan, prior_brief=prior_brief
        )
        result = await self._agent.run(user_msg)
        output = getattr(result, "output", None) or getattr(result, "data", None)
        if output is None:
            raise AttributeError(
                "Aggregator AgentRunResult contained no 'output' or 'data'."
            )
        # Always copy assumptions from the plan — not LLM-generated
        output.assumptions_ref = plan.assumptions
        # Hard backstop: truncate brief regardless of what the model emitted.
        # This is the actual guarantee behind T9b acceptance criterion 1.
        output.session_brief = truncate_brief(
            output.session_brief, settings.session_brief_max_tokens
        )
        logger.debug(
            "Aggregator result",
            extra={
                "claim_count": len(output.claims),
                "has_chart": output.chart_spec is not None,
                "session_brief_len": len(output.session_brief),
            },
        )
        return output


class FakeAggregator(Aggregator):
    """Deterministic fallback used when no LLM API key is configured."""

    async def aggregate(
        self,
        question: str,
        rows: list[dict],
        plan: PlanResult,
        prior_brief: str = "",
    ) -> AnswerSpec:
        logger.debug(
            "Using fake aggregator",
            extra={"question_length": len(question), "row_count": len(rows)},
        )
        is_single_value = len(rows) == 1 and len(rows[0]) == 1

        # Headline from first row, first column
        headline = _build_headline(rows)

        # Chart spec: only when there is a genuine comparison axis (>1 row, >=2 columns)
        chart_spec: ChartSpecModel | None = None
        suppression_reason: str | None = None
        if is_single_value:
            suppression_reason = "single value result"
        elif len(rows) < 2:
            suppression_reason = "insufficient rows for comparison"
        else:
            chart_spec = _build_chart_spec_model(rows)
            if chart_spec is None:
                suppression_reason = "no numeric column found for y-axis"

        # Claims: one row-typed claim citing the first cell when result is non-trivial
        claims: list[Claim] = []
        if rows and not is_single_value:
            first_row = rows[0]
            first_col = next(iter(first_row))
            first_val = first_row[first_col]
            claims.append(
                Claim(
                    sentence=f"The first result has {first_col} = {first_val}.",
                    type="row",
                    cells=[{"row": 0, "column": first_col, "value": first_val}],
                )
            )

        return AnswerSpec(
            response_type="chart" if chart_spec is not None else "stat",
            headline=headline,
            restatement=f"Computed {question}.",
            chart_spec=chart_spec,
            suppression_reason=suppression_reason,
            claims=claims,
            followups=[],
            assumptions_ref=list(plan.assumptions),
            dropped_claim_count=0,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_aggregate_user_msg(
    question: str, rows: list[dict], plan: PlanResult, prior_brief: str = ""
) -> str:
    """Build the structured user message for an aggregator run.

    Serialises only the plan's structured fields (ambiguity_score, assumptions,
    unresolved_terms) — explicitly excluding ``plan.interpretation`` to prevent
    LLM-authored prose from being recycled as fact (prose-handoff anti-pattern).
    """
    plan_context = json.dumps(plan.model_dump(exclude={"interpretation"}), default=str)
    safe = truncate_for_prompt(rows)
    stats_text = json.dumps(
        {
            col: stat.model_dump(exclude_none=True)
            for col, stat in safe.column_stats.items()
        },
        default=str,
    )
    result_text = (
        f"Result rows (showing {len(safe.rows)} of {safe.total_row_count} total):\n"
        f"{json.dumps(safe.rows, default=str)}\n\n"
        f"Per-column stats (full result set):\n{stats_text}"
    )
    runtime_data = f"Plan context (structured):\n{plan_context}\n\n{result_text}"
    return build_dynamic_state(
        session_brief=prior_brief, question=question, runtime_data=runtime_data
    )


def _build_headline(rows: list[dict]) -> Headline:
    if not rows:
        return Headline(value="No results", label="result count", sign="neutral")
    first_row = rows[0]
    first_col = next(iter(first_row))
    first_val = first_row[first_col]
    return Headline(
        value=str(first_val),
        label=first_col.replace("_", " "),
        sign="neutral",
    )


def _build_chart_spec_model(rows: list[dict]) -> ChartSpecModel | None:
    """Build a minimal ChartSpecModel from the first two columns, mirroring _build_chart logic."""
    keys = list(rows[0].keys())
    if len(keys) < 2:
        return None

    x_key = keys[0]
    y_key = next(
        (k for k in keys[1:] if all(_is_number(row.get(k)) for row in rows)),
        None,
    )
    if y_key is None:
        return None

    return ChartSpecModel(
        chart_type="bar",
        title="Comparison",
        x_key=x_key,
        y_key=y_key,
        data=rows,
    )


def _is_number(value: object) -> bool:
    return isinstance(value, Number) and not isinstance(value, bool)
