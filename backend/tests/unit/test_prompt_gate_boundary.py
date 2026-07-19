"""Load-bearing tests for the prompt boundary gate (T2).

Test budget: 6 (JUSTIFIED: +2 over original 4 — Fix 1 Decimal regression test [hard
ceiling 1 per single-function bug fix, required by testing.md]; Fix 2 CI pattern
negative-verification test [explicitly mandated by the review issue]; all pass the
Load-Bearing Filter).
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from app.agent.prompt_gate import truncate_for_prompt, PromptSafeResult


# ---------------------------------------------------------------------------
# 1. Capping: rows are truncated, total_row_count reflects the full set
# ---------------------------------------------------------------------------


def test_truncate_caps_rows_to_max_llm_rows() -> None:
    """truncate_for_prompt must cap rows at max_llm_rows and report the true total.

    If capping breaks, the LLM receives uncapped row data — the core invariant
    this gate exists to enforce.
    """
    rows = [{"id": i, "val": float(i)} for i in range(200)]

    with patch("app.agent.prompt_gate.settings") as mock_settings:
        mock_settings.max_llm_rows = 10
        result = truncate_for_prompt(rows)

    assert isinstance(result, PromptSafeResult)
    assert len(result.rows) == 10
    assert result.total_row_count == 200


# ---------------------------------------------------------------------------
# 2. Stats are computed over the FULL row set, not the truncated sample
# ---------------------------------------------------------------------------


def test_stats_computed_over_full_row_set() -> None:
    """Column stats must reflect all rows, not just the capped subset.

    If stats used only the capped rows, the model would receive dishonest
    column summaries (e.g. min/max covering only a fraction of the data).
    """
    # 20 rows; cap at 5 — stats must still see all 20
    rows = [{"amount": float(i * 100)} for i in range(20)]

    with patch("app.agent.prompt_gate.settings") as mock_settings:
        mock_settings.max_llm_rows = 5
        result = truncate_for_prompt(rows)

    stat = result.column_stats["amount"]
    assert stat.min == "0.0"
    assert stat.max == "1900.0"  # max of the FULL 20-row set, not just first 5


# ---------------------------------------------------------------------------
# 3. Numeric vs categorical stat shape
# ---------------------------------------------------------------------------


def test_numeric_and_categorical_columns_produce_correct_stat_shapes() -> None:
    """Numeric columns get min/max; categorical columns get distinct_count.

    If classification breaks, the model gets the wrong kind of stat — e.g.
    a distinct_count on a numeric column instead of an actionable min/max.
    """
    rows = [
        {"price": 10.0, "category": "A"},
        {"price": 20.0, "category": "B"},
        {"price": 10.0, "category": "A"},
    ]

    with patch("app.agent.prompt_gate.settings") as mock_settings:
        mock_settings.max_llm_rows = 100
        result = truncate_for_prompt(rows)

    price_stat = result.column_stats["price"]
    assert price_stat.min == "10.0"
    assert price_stat.max == "20.0"
    assert price_stat.distinct_count is None

    cat_stat = result.column_stats["category"]
    assert cat_stat.distinct_count == 2  # "A" and "B"
    assert cat_stat.min is None
    assert cat_stat.max is None


# ---------------------------------------------------------------------------
# 4. Regression: decimal.Decimal columns must produce correct min/max (Fix 1)
# ---------------------------------------------------------------------------


def test_decimal_column_gets_correct_min_max() -> None:
    """Columns of decimal.Decimal values (common from Postgres NUMERIC/SUM/AVG)
    must produce string min/max, not None.

    Before Fix 1, _is_numeric accepted Decimal (via numbers.Number) but the inner
    filter used isinstance(v, (int, float)), so numeric ended up empty and min/max
    were None — silently wrong stats for the most common aggregate column type.
    """
    rows = [
        {"total": Decimal("99.99")},
        {"total": Decimal("0.01")},
        {"total": Decimal("10.50")},
    ]

    with patch("app.agent.prompt_gate.settings") as mock_settings:
        mock_settings.max_llm_rows = 100
        result = truncate_for_prompt(rows)

    stat = result.column_stats["total"]
    assert stat.min == "0.01", f"Expected min='0.01', got {stat.min!r}"
    assert stat.max == "99.99", f"Expected max='99.99', got {stat.max!r}"


# ---------------------------------------------------------------------------
# 5. CI/lint: no raw rows serialization outside prompt_gate.py
# ---------------------------------------------------------------------------


def test_ci_no_raw_rows_serialization_outside_prompt_gate() -> None:
    """No file under backend/app/ (except prompt_gate.py) may serialize raw rows
    into a prompt string without going through truncate_for_prompt.

    Pattern catches: json.dumps(rows...), json.dumps({"rows": rows}), f-string {rows}.
    Deliberately does NOT flag json.dumps(safe.rows) — that is the correct gate usage.
    """
    app_root = Path(__file__).resolve().parents[2] / "app"
    gate_file = app_root / "agent" / "prompt_gate.py"

    # Broadened pattern (Fix 2):
    #   alt 1 — json.dumps(rows...) direct variable (not safe.rows / result.rows)
    #   alt 2 — json.dumps({...rows...}) dict-wrapped bypass
    #   alt 3 — f-string {rows} or {obj.rows} — simple interpolation only;
    #            \{(?:\w+\.)?rows\} avoids false-positives on complex expressions
    #            like {json.dumps(safe.rows, ...)} which is the correct gate usage
    pattern = re.compile(
        r"json\.dumps\(\s*rows\b"
        r"|json\.dumps\(\{[^}]*\brows\b"
        r"|\{(?:\w+\.)?rows\}"
    )

    violations: list[str] = []
    for py_file in app_root.rglob("*.py"):
        if py_file.resolve() == gate_file.resolve():
            continue
        text = py_file.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                violations.append(
                    f"{py_file.relative_to(app_root)}:{lineno}: {line.strip()}"
                )

    assert not violations, (
        "Found raw rows serialization outside prompt_gate.py — "
        "use truncate_for_prompt() instead:\n" + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# 6. CI grep pattern self-verification: broader shapes fire (Fix 2)
# ---------------------------------------------------------------------------


def test_ci_grep_pattern_fires_on_dict_wrapped_rows_bypass() -> None:
    """The broadened grep pattern must fire on json.dumps({"rows": rows}) —
    a bypass shape the original r'json\\.dumps\\(rows' would silently miss.

    This verifies the pattern itself is not too narrow, without touching real files.
    """
    pattern = re.compile(
        r"json\.dumps\(\s*rows\b"
        r"|json\.dumps\(\{[^}]*\brows\b"
        r"|\{(?:\w+\.)?rows\}"
    )
    # Dict-wrapped bypass — old pattern missed this entirely
    assert pattern.search('payload = json.dumps({"rows": rows})'), (
        "Pattern must catch dict-wrapped json.dumps({'rows': rows}) bypass"
    )
    # Direct argument — old pattern already caught this (sanity check)
    assert pattern.search("json.dumps(rows, default=str)")
    # F-string interpolation bypass — old pattern never looked for this
    assert pattern.search('f"Result: {rows}"')
    # Must NOT flag the legitimate gate usage (safe = truncate_for_prompt(rows))
    assert not pattern.search("json.dumps(safe.rows, default=str)"), (
        "Pattern must not flag json.dumps(safe.rows) — that is the correct gate usage"
    )
