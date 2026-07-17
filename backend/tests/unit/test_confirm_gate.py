"""Load-bearing tests for the confirm-first gate (Epic 9 Slice 12).

Gate fires when ambiguity_score > ambiguity_threshold  OR
scan_cost > scan_cost_threshold; both are read from config so tests
patch them directly rather than hardcoding numbers.
"""

import pytest

from app.agent.contracts import PlanResult, Assumption
from app.agent.planner import Planner
from app.agent.validator import Validator
from app.domain.models import Answer, ConfirmFirst, ValidationResult, Dependency, Fingerprint
from app.repositories.memory.schema_repository_memory import InMemorySchemaRepository
from app.repositories.memory.query_repository_memory import InMemoryQueryRepository
from app.agent.agent import FakeSqlGenerator
from app.services.ask_service import AskService


class HighAmbiguityPlanner(Planner):
    async def plan(self, question: str, schema_repo_override=None) -> PlanResult:
        return PlanResult(
            ambiguity_score=0.9,
            assumptions=[Assumption(term="recent", resolution="last 30 days")],
            unresolved_terms=[],
            interpretation="showing recent orders",
        )


class HighCostValidator(Validator):
    async def validate(self, sql: str, schema_repo, query_repo) -> ValidationResult:
        return ValidationResult(
            dependency_set=[Dependency(table="orders", column="order_id")],
            fingerprints=[Fingerprint(table="orders", column="order_id", schema_hash="abc")],
            scan_cost=2_000_000,
        )


def _make_service(planner=None, validator=None) -> AskService:
    schema_repo = InMemorySchemaRepository()
    query_repo = InMemoryQueryRepository()
    query_repo.set_return_rows([{"count": 1}])
    return AskService(
        sql_generator=FakeSqlGenerator(),
        schema_repository=schema_repo,
        query_repository=query_repo,
        planner=planner,
        validator=validator,
    )


@pytest.mark.asyncio
async def test_high_ambiguity_returns_confirm_first_gate():
    """A question whose ambiguity_score > threshold must return ConfirmFirst, not Answer."""
    service = _make_service(planner=HighAmbiguityPlanner())
    # Default threshold is 0.6; planner returns 0.9
    result = await service.answer("show me recent orders")
    assert isinstance(result, ConfirmFirst)
    assert result.gate_reason == "ambiguity"
    assert result.plan.ambiguity_score == 0.9
    assert result.conversation_id  # confirm store key present


@pytest.mark.asyncio
async def test_high_cost_returns_confirm_first_gate():
    """A query whose scan_cost > threshold must return ConfirmFirst, not Answer."""
    service = _make_service(validator=HighCostValidator())
    # Default threshold is 1_000_000; validator returns 2_000_000
    result = await service.answer("count all orders")
    assert isinstance(result, ConfirmFirst)
    assert result.gate_reason == "cost"
    assert result.scan_cost == 2_000_000


@pytest.mark.asyncio
async def test_low_ambiguity_low_cost_returns_answer():
    """Normal question with low ambiguity and low cost must skip gate and return Answer."""
    service = _make_service()  # FakePlanner returns 0.0 ambiguity; no validator override
    result = await service.answer("how many orders")
    assert isinstance(result, Answer)


@pytest.mark.asyncio
async def test_confirm_without_amendments_returns_answer():
    """Confirming with no amendments must execute and return an Answer."""
    service = _make_service(planner=HighAmbiguityPlanner())
    gate = await service.answer("show me recent orders")
    assert isinstance(gate, ConfirmFirst)

    result = await service.answer_confirmed(
        confirm_id=gate.conversation_id,
        amendments=[],
    )
    assert isinstance(result, Answer)


@pytest.mark.asyncio
async def test_confirm_with_amendment_reflects_amended_resolution():
    """Confirming with an amendment must apply the new resolution to the plan returned in the answer."""
    service = _make_service(planner=HighAmbiguityPlanner())
    gate = await service.answer("show me recent orders")
    assert isinstance(gate, ConfirmFirst)

    result = await service.answer_confirmed(
        confirm_id=gate.conversation_id,
        amendments=[("recent", "last 7 days")],
    )
    assert isinstance(result, Answer)
    # Amended plan should carry the new resolution
    assert result.plan is not None
    assumption = next((a for a in result.plan.assumptions if a.term == "recent"), None)
    assert assumption is not None
    assert assumption.resolution == "last 7 days"
