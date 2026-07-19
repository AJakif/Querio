"""Prompt boundary gate for row data entering LLM prompts.

This module is the SOLE LEGAL PATH for row data entering any LLM prompt.
No other module may serialize a ``rows`` list directly into a prompt string.
Use ``truncate_for_prompt`` to produce a ``PromptSafeResult`` that caps the
row count via ``settings.max_llm_rows`` and attaches honest per-column stats
computed over the FULL result set — not just the truncated sample.
"""

from __future__ import annotations

from datetime import date, datetime
from numbers import Number
from typing import (
    Any,
)  # Any: arbitrary JSON-serializable row/cell data from heterogeneous SQL result columns

from pydantic import BaseModel

from app.core.config import settings


class ColumnStat(BaseModel):
    """Per-column statistics block included in every prompt payload."""

    null_count: int
    # numeric / date columns
    min: str | None = None
    max: str | None = None
    # categorical / string columns
    distinct_count: int | None = None


class PromptSafeResult(BaseModel):
    """Row data that has passed through the prompt boundary gate."""

    # Any: cell types are unknown at compile time — heterogeneous SQL result columns
    rows: list[dict[str, Any]]
    total_row_count: int
    column_stats: dict[str, ColumnStat]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_numeric(value: object) -> bool:
    return isinstance(value, Number) and not isinstance(value, bool)


def _is_date_like(value: object) -> bool:
    return isinstance(value, (date, datetime))


def _distinct_count(values: list[Any]) -> int:
    """Dedup on raw values when hashable; fall back to str-based dedup only when not."""
    try:
        return len(set(values))
    except TypeError:
        return len({str(v) for v in values})


def _compute_column_stats(rows: list[dict[str, Any]]) -> dict[str, ColumnStat]:
    # rows: list[dict[str, Any]] — heterogeneous SQL result data; cell types are unknown at compile time
    """Compute per-column stats over the *full* row set."""
    if not rows:
        return {}

    columns = list(rows[0].keys())
    stats: dict[str, ColumnStat] = {}

    for col in columns:
        values: list[Any] = [row.get(col) for row in rows]
        null_count = sum(1 for v in values if v is None)
        non_null: list[Any] = [v for v in values if v is not None]

        if non_null and all(_is_numeric(v) for v in non_null):
            # Fix 1: use _is_numeric (includes decimal.Decimal) instead of the
            # narrower isinstance(v, (int, float)) filter that excluded Decimal values.
            numeric = [v for v in non_null if _is_numeric(v)]
            stats[col] = ColumnStat(
                null_count=null_count,
                min=str(min(numeric)) if numeric else None,
                max=str(max(numeric)) if numeric else None,
            )
        elif non_null and all(_is_date_like(v) for v in non_null):
            date_vals = [v for v in non_null if isinstance(v, (date, datetime))]
            stats[col] = ColumnStat(
                null_count=null_count,
                min=str(min(date_vals)) if date_vals else None,
                max=str(max(date_vals)) if date_vals else None,
            )
        else:
            stats[col] = ColumnStat(
                null_count=null_count,
                distinct_count=_distinct_count(non_null),
            )

    return stats


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


_CHARS_PER_TOKEN = 4  # rough heuristic; no tiktoken dependency


def truncate_brief(brief: str, max_tokens: int) -> str:
    """Hard backstop: trim *brief* to fit *max_tokens* (heuristic: 4 chars/token).

    Called after every Aggregator LLM call so the brief can never grow unbounded
    regardless of what the model emits.  This is the guarantee behind T9b
    acceptance criterion 1 — no extra LLM round trip, purely deterministic.
    """
    max_chars = max_tokens * _CHARS_PER_TOKEN
    if len(brief) <= max_chars:
        return brief
    # Trim to the last word boundary inside the budget so we don't cut mid-word.
    truncated = brief[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > max_chars // 2:
        truncated = truncated[:last_space]
    return truncated


def truncate_for_prompt(rows: list[dict[str, Any]]) -> PromptSafeResult:
    """Cap rows and compute per-column stats for LLM prompt injection.

    This is the SOLE LEGAL PATH for row data entering any LLM prompt.
    Stats are computed over the FULL row set so the model receives honest
    column summaries regardless of the cap applied to the rows list.

    Reads ``settings.max_llm_rows`` at call time — changing that env var
    changes prompt content with no code edit required.
    """
    cap = settings.max_llm_rows
    column_stats = _compute_column_stats(rows)
    return PromptSafeResult(
        rows=rows[:cap],
        total_row_count=len(rows),
        column_stats=column_stats,
    )
