"""Load-bearing tests for Slice 4: Validator.verify_claims anti-hallucination boundary.

Test budget: 5 (within soft ceiling of 5).
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
    def test_row_claims_pass_through_unconditionally(self) -> None:
        """Row-typed claims are exempt from arithmetic verification."""
        row = _row_claim("First result has revenue = 1200000.")
        # Embed a plausible computation claim too so we know only row is exempt
        true_comp = _computation("Sum is 100.", operation="sum", operands=[100.0], value=100.0)
        spec = _spec(row, true_comp)

        updated, dropped = _VALIDATOR.verify_claims(spec, _EMPTY_ROWS)

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
