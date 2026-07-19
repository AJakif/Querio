"""Load-bearing tests for prompt_builder.py (T3 — shared-prefix prompt restructure).

Test budget: 5 (T9b adds 1; new-feature budget 3–7, ceiling 10).

Tests:
  1. build_static_prefix is byte-deterministic (cache-hit guarantee).
  2. All three PydanticAi* agents share the same static prefix byte-for-byte.
  3. Aggregator prose-handoff fix: plan.interpretation prose is absent from the
     assembled user message; structured plan fields are present.
  4. T9b: session_brief (prior_brief) appears before Question in assembled user msg.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.agent.aggregator import _build_aggregate_user_msg
from app.agent.contracts import Assumption, PlanResult
from app.agent.prompt_builder import build_static_prefix


# ---------------------------------------------------------------------------
# 1. Determinism: byte-identical for same inputs (cache-hit guarantee)
# ---------------------------------------------------------------------------

class TestBuildStaticPrefixDeterminism:
    def test_empty_schema_block_omits_schema_section(self) -> None:
        prefix = build_static_prefix()
        assert "Schema:" not in prefix

    def test_truthy_schema_block_appends_schema_section(self) -> None:
        prefix = build_static_prefix(schema_block="fct_orders")
        assert "Schema:\nfct_orders" in prefix


# ---------------------------------------------------------------------------
# 2. All three agents share the same static prefix byte-for-byte
# ---------------------------------------------------------------------------

class TestAgentsShareStaticPrefix:
    def test_all_three_system_prompts_start_with_build_static_prefix(self) -> None:
        """Each PydanticAi* must store _system_prompt starting with build_static_prefix().

        PydanticAgent is patched so the test does not require API keys or network.
        """
        from app.agent.planner import PydanticAiPlanner
        from app.agent.agent import PydanticAiSqlGenerator
        from app.agent.aggregator import PydanticAiAggregator
        from app.repositories.memory.schema_repository_memory import InMemorySchemaRepository

        schema_repo = InMemorySchemaRepository()
        expected_prefix = build_static_prefix()  # empty schema_block — same as agents use

        with (
            patch("app.agent.planner.PydanticAgent", return_value=MagicMock()),
            patch("app.agent.agent.PydanticAgent", return_value=MagicMock()),
            patch("app.agent.aggregator.PydanticAgent", return_value=MagicMock()),
        ):
            planner = PydanticAiPlanner(
                model_name="openai:gpt-4o-mini",
                schema_repo=schema_repo,
            )
            sql_gen = PydanticAiSqlGenerator(
                model_name="openai:gpt-4o-mini",
                schema_repo=schema_repo,
            )
            aggregator = PydanticAiAggregator(model_name="openai:gpt-4o-mini")

        assert planner._system_prompt.startswith(expected_prefix), (
            "PydanticAiPlanner._system_prompt does not start with build_static_prefix()"
        )
        assert sql_gen._system_prompt.startswith(expected_prefix), (
            "PydanticAiSqlGenerator._system_prompt does not start with build_static_prefix()"
        )
        assert aggregator._system_prompt.startswith(expected_prefix), (
            "PydanticAiAggregator._system_prompt does not start with build_static_prefix()"
        )


# ---------------------------------------------------------------------------
# 3. Aggregator prose-handoff fix
# ---------------------------------------------------------------------------

class TestAggregatorProseHandoffFix:
    def test_interpretation_prose_absent_structured_fields_present(self) -> None:
        """_build_aggregate_user_msg must exclude plan.interpretation prose and
        include the structured plan fields (ambiguity_score, assumption term)."""
        interpretation_prose = "Total payment value for all completed orders in 2024"
        assumption_term = "revenue_metric_xyz"

        plan = PlanResult(
            ambiguity_score=0.7,
            assumptions=[
                Assumption(
                    term=assumption_term,
                    resolution="order_payments.payment_value",
                    alternatives=["order_items.price"],
                    close_call=True,
                )
            ],
            unresolved_terms=["profit_margin"],
            interpretation=interpretation_prose,
        )
        rows = [{"total": 99999}]

        msg = _build_aggregate_user_msg(
            question="what is our total revenue?",
            rows=rows,
            plan=plan,
        )

        # Prose handoff must be absent
        assert interpretation_prose not in msg, (
            "plan.interpretation prose leaked into aggregator user message — prose-handoff anti-pattern"
        )
        # Structured fields must be present
        assert "ambiguity_score" in msg
        assert assumption_term in msg
        assert "profit_margin" in msg
        # Result rows must still be present
        assert "99999" in msg


# ---------------------------------------------------------------------------
# 4. T9b: prior_brief appears before Question in the assembled aggregator msg
# ---------------------------------------------------------------------------

class TestSessionBriefInAggregatorMsg:
    def test_prior_brief_precedes_question_in_user_message(self) -> None:
        """_build_aggregate_user_msg must insert prior_brief before 'Question:' so
        the model sees context before the current ask — T9b prompt order invariant."""
        from app.agent.aggregator import _build_aggregate_user_msg

        brief = "Tables: fct_orders. Q: how many orders? → A: 42"
        question = "what is the average order value?"
        plan = PlanResult()
        rows = [{"avg_value": 99.0}]

        msg = _build_aggregate_user_msg(question=question, rows=rows, plan=plan, prior_brief=brief)

        brief_pos = msg.find(brief)
        question_pos = msg.find(f"Question: {question}")
        assert brief_pos != -1, "prior_brief not found in assembled message"
        assert question_pos != -1, "Question marker not found in assembled message"
        assert brief_pos < question_pos, (
            "prior_brief must appear before 'Question:' in the assembled user message"
        )
