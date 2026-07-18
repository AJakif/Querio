"""Load-bearing tests for Slice 4: Validator.verify_claims anti-hallucination boundary.

Test budget: 7 (5 original + 1 regression Bug-1 + 1 regression Bug-2 = 7; soft ceiling ≤5
exceeded; JUSTIFIED: +2 tests — both add distinct, load-bearing signal: Bug-1 proves
cells-based resolution catches LLM-fabricated operands that the old path let through;
Bug-2 proves row-cite cells are checked against reality, which the old path skipped entirely.
No other existing test covers either failure mode.)
"""
from __future__ import annotations

import pytest

from app.agent.contracts import AnswerSpec, Claim, Headline
from app.agent.validator import Validator


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------


def _spec(*claims: Claim) -> AnswerSpec:
    return AnswerSpec(
        headline=Headline(value="$1.2M", label="revenue", sign="positive"),
        restatement="Revenue grew from last period.",
        claims=list(claims),
    )


def _computation(sentence: str, operation: str, operands: list[float], value: float) -> Claim:
    return Claim(
        sentence=sentence,
        type="computation",
        operation=operation,
        operands=operands,
        value=value,
    )


def _row_claim(sentence: str) -> Claim:
    return Claim(
        sentence=sentence,
        type="row",
        cells=[{"row": 0, "column": "revenue", "value": 1200000}],
    )


_VALIDATOR = Validator()
_EMPTY_ROWS: list[dict] = []
# Real rows used by row-cite tests — cells reference row 0, column "revenue"
_REVENUE_ROWS: list[dict] = [{"revenue": 1200000}]


# ---------------------------------------------------------------------------
# 1. False computation cite is dropped; true one passes; dropped_claim_count correct
# ---------------------------------------------------------------------------


class TestFalseClaimDropped:
    def test_false_computation_dropped_true_kept_count_correct(self) -> None:
        """False computation cite ('revenue grew 40%' when data shows 12%) is dropped;
        a correct sum claim passes through; dropped_claim_count == 1."""
        false_claim = _computation(
            "Revenue grew 40% year-over-year.",
            operation="ratio",
            operands=[1_120_000.0, 1_000_000.0],  # ratio = 1.12, not 1.40
            value=1.40,
        )
        true_claim = _computation(
            "Total revenue is $2.1M.",
            operation="sum",
            operands=[1_200_000.0, 900_000.0],
            value=2_100_000.0,
        )
        spec = _spec(false_claim, true_claim)

        updated, dropped = _VALIDATOR.verify_claims(spec, _EMPTY_ROWS)

        assert dropped == 1
        assert updated.dropped_claim_count == 1
        assert len(updated.claims) == 1
        assert updated.claims[0].sentence == "Total revenue is $2.1M."


# ---------------------------------------------------------------------------
# 2. Row-typed claims are NEVER touched, even if arithmetically implausible
# ---------------------------------------------------------------------------


class TestRowClaimExempt:
    def test_row_claims_pass_through_when_cells_match_reality(self) -> None:
        """Row-typed claims pass when every cited cell matches the real result set."""
        row = _row_claim("First result has revenue = 1200000.")
        # Embed a plausible computation claim too so we know only row is exempt
        true_comp = _computation("Sum is 100.", operation="sum", operands=[100.0], value=100.0)
        spec = _spec(row, true_comp)

        # Provide rows that match the cell data (row 0, column "revenue", value 1200000)
        updated, dropped = _VALIDATOR.verify_claims(spec, _REVENUE_ROWS)

        assert dropped == 0
        assert any(c.type == "row" for c in updated.claims)
        assert len(updated.claims) == 2


# ---------------------------------------------------------------------------
# 3. All computation claims dropped → headline and restatement still present
# ---------------------------------------------------------------------------


class TestAllClaimsDropped:
    def test_all_claims_dropped_headline_and_restatement_preserved(self) -> None:
        """When every computation cite fails, headline and restatement are still present."""
        false1 = _computation("Claim A.", operation="sum", operands=[10.0, 10.0], value=999.0)
        false2 = _computation("Claim B.", operation="count", operands=[1.0, 2.0], value=99.0)
        spec = _spec(false1, false2)

        updated, dropped = _VALIDATOR.verify_claims(spec, _EMPTY_ROWS)

        assert dropped == 2
        assert updated.claims == []
        assert updated.headline.value == "$1.2M"   # unchanged
        assert updated.restatement == "Revenue grew from last period."  # unchanged


# ---------------------------------------------------------------------------
# 4. Correct computation cite passes through with dropped_claim_count == 0
# ---------------------------------------------------------------------------


class TestCorrectClaimPreserved:
    def test_correct_avg_passes_through_unchanged(self) -> None:
        """A correctly-stated average claim is not dropped; dropped_claim_count is 0."""
        claim = _computation(
            "Average order value is $250.",
            operation="average",
            operands=[200.0, 250.0, 300.0],
            value=250.0,
        )
        spec = _spec(claim)

        updated, dropped = _VALIDATOR.verify_claims(spec, _EMPTY_ROWS)

        assert dropped == 0
        assert updated.dropped_claim_count == 0
        assert len(updated.claims) == 1
        assert updated.claims[0].sentence == "Average order value is $250."


# ---------------------------------------------------------------------------
# 5. Unrecognized operation is DROPPED, not passed through (regression: bypass fix)
# ---------------------------------------------------------------------------


class TestUnrecognizedOperationDropped:
    def test_unrecognized_operation_is_dropped_not_passed_through(self) -> None:
        """A computation claim with an unrecognized operation gets zero verification
        and must be dropped — not kept — to prevent hallucination bypass."""
        claim = Claim(
            sentence="Some fabricated statistic.",
            type="computation",
            operation="some_unrecognized_op",
            operands=[1.0],
            value=999.0,
        )
        spec = _spec(claim)

        updated, dropped = _VALIDATOR.verify_claims(spec, _EMPTY_ROWS)

        assert dropped == 1
        assert updated.dropped_claim_count == 1
        assert updated.claims == []


# ---------------------------------------------------------------------------
# 6. REGRESSION Bug-1 — cells-based resolution overrides LLM-supplied operands
# ---------------------------------------------------------------------------


class TestComputationCellsOverrideLlmOperands:
    def test_computation_claim_dropped_when_cells_resolve_to_different_operands(self) -> None:
        """Regression: LLM supplies fake operands that are self-consistent but don't match
        the real result rows. The validator MUST resolve operands from cited cells against
        the real rows, not trust claim.operands. A claim whose real cell values produce a
        sum that doesn't match claim.value must be dropped even if the LLM operands would
        have matched."""
        real_rows = [
            {"revenue": 100.0},
            {"revenue": 200.0},
        ]
        # LLM claims sum of 500 and provides fake operands [250.0, 250.0] which sum to 500 — self-consistent.
        # But cells point to row 0 and row 1, whose real values are 100 and 200 (sum = 300, not 500).
        claim = Claim(
            sentence="Total revenue is 500.",
            type="computation",
            operation="sum",
            operands=[250.0, 250.0],  # LLM-fabricated; should NOT be used
            value=500.0,
            cells=[
                {"row": 0, "column": "revenue", "value": 250.0},  # LLM cites 250, reality is 100
                {"row": 1, "column": "revenue", "value": 250.0},  # LLM cites 250, reality is 200
            ],
        )
        spec = _spec(claim)

        updated, dropped = _VALIDATOR.verify_claims(spec, real_rows)

        assert dropped == 1, "Claim must be dropped: real cell values (100+200=300) ≠ claimed value (500)"
        assert updated.claims == []


# ---------------------------------------------------------------------------
# 7. REGRESSION Bug-2 — row-cite claims with mismatched cells are dropped
# ---------------------------------------------------------------------------


class TestRowClaimDroppedOnCellMismatch:
    def test_row_claim_dropped_when_cited_cell_value_differs_from_reality(self) -> None:
        """Regression: row-cite claims were kept unconditionally regardless of whether the
        cited cell value matches the actual result set. A row claim citing revenue=999 when
        the real row has revenue=1200000 must be dropped."""
        real_rows = [{"revenue": 1200000}]
        lying_row_claim = Claim(
            sentence="First row has revenue 999.",
            type="row",
            cells=[{"row": 0, "column": "revenue", "value": 999}],  # wrong value
        )
        spec = _spec(lying_row_claim)

        updated, dropped = _VALIDATOR.verify_claims(spec, real_rows)

        assert dropped == 1, "Row claim must be dropped: cited value 999 ≠ real value 1200000"
        assert updated.claims == []
