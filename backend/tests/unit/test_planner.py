"""Load-bearing tests for Slice 1: Planner ambiguity contracts.

Test budget: 4 (soft ceiling 5). No JUSTIFIED needed.
"""

import pytest
from fastapi.testclient import TestClient

from app.agent.contracts import Assumption, PlanResult
from app.agent.planner import FakePlanner, Planner
from app.repositories.base import SchemaRepository


# ---------------------------------------------------------------------------
# Test double
# ---------------------------------------------------------------------------

class ScriptedPlanner(Planner):
    """Returns a fixed PlanResult regardless of question, for deterministic tests."""

    def __init__(self, result: PlanResult) -> None:
        self._result = result

    async def plan(
        self,
        question: str,
        schema_repo_override: SchemaRepository | None = None,
    ) -> PlanResult:
        return self._result


# ---------------------------------------------------------------------------
# 1. Contract shape: Assumption + PlanResult fields/defaults
# ---------------------------------------------------------------------------

class TestContractShape:
    def test_assumption_and_plan_result_defaults(self) -> None:
        a = Assumption(term="revenue", resolution="payment_value column")
        assert a.alternatives == []
        assert a.close_call is False

        p = PlanResult()
        assert p.ambiguity_score == 0.0
        assert p.assumptions == []
        assert p.unresolved_terms == []
        assert p.interpretation == ""

    def test_close_call_flag_roundtrips(self) -> None:
        a = Assumption(
            term="sales",
            resolution="order_payments.payment_value",
            alternatives=["order_items.price"],
            close_call=True,
        )
        assert a.close_call is True
        assert "order_items.price" in a.alternatives


# ---------------------------------------------------------------------------
# 2. FakePlanner: unambiguous fallback
# ---------------------------------------------------------------------------

class TestFakePlanner:
    @pytest.mark.asyncio
    async def test_fake_planner_returns_low_score_and_empty_fields(self) -> None:
        planner = FakePlanner()
        result = await planner.plan("how many orders are there")
        assert result.ambiguity_score == 0.0
        assert result.assumptions == []
        assert result.unresolved_terms == []
        assert result.interpretation != ""  # echoes question


# ---------------------------------------------------------------------------
# 3. API integration: plan flows through /ask for all three scenarios
# ---------------------------------------------------------------------------

@pytest.fixture
def _make_client_with_planner():
    """Factory: builds a TestClient with a given Planner injected into AskService."""
    from app.main import app
    from app.api.routes.ask import get_ask_service
    from app.agent.agent import FakeSqlGenerator
    from app.repositories.memory.query_repository_memory import InMemoryQueryRepository
    from app.repositories.memory.schema_repository_memory import InMemorySchemaRepository
    from app.services.ask_service import AskService

    def _factory(planner: Planner) -> TestClient:
        schema_repo = InMemorySchemaRepository()
        query_repo = InMemoryQueryRepository()
        query_repo.set_return_rows([{"order_count": 42}])

        async def _override() -> AskService:
            return AskService(
                sql_generator=FakeSqlGenerator(),
                schema_repository=schema_repo,
                query_repository=query_repo,
                planner=planner,
            )

        app.dependency_overrides[get_ask_service] = _override
        client = TestClient(app)
        client.__enter__()
        return client, app, get_ask_service

    return _factory


class TestPlanInApiResponse:
    def test_rich_plan_result_flows_through_ask_response(
        self, _make_client_with_planner
    ) -> None:
        """Assumptions and ambiguity_score flow through to the answer when no unresolved terms."""
        from app.main import app
        from app.api.routes.ask import get_ask_service

        # No unresolved_terms — question is resolvable, so we get an answer (not clarify or gate)
        # Use a score below the ambiguity_threshold (0.6) so the confirm-first gate doesn't fire.
        rich_plan = PlanResult(
            ambiguity_score=0.5,
            assumptions=[
                Assumption(
                    term="revenue",
                    resolution="order_payments.payment_value",
                    alternatives=["order_items.price"],
                    close_call=True,
                )
            ],
            unresolved_terms=[],
            interpretation="Total payment value for all completed orders",
        )

        client, _, override_key = _make_client_with_planner(ScriptedPlanner(rich_plan))
        try:
            resp = client.post("/api/ask", json={"question": "what is our total revenue?"})
            assert resp.status_code == 200
            body = resp.json()
            assert body["type"] == "answer"
            plan = body["plan"]

            assert plan["ambiguity_score"] == pytest.approx(0.5)
            assert plan["unresolved_terms"] == []

            assumption = plan["assumptions"][0]
            assert assumption["term"] == "revenue"
            assert assumption["close_call"] is True
            assert "order_items.price" in assumption["alternatives"]
        finally:
            app.dependency_overrides.pop(override_key, None)

    def test_unresolved_terms_routes_to_clarify(self, _make_client_with_planner) -> None:
        """When the planner reports unresolved terms, the API returns type=clarify (ROUTE-3)."""
        from app.main import app
        from app.api.routes.ask import get_ask_service

        plan_with_unresolved = PlanResult(
            ambiguity_score=0.75,
            assumptions=[],
            unresolved_terms=["profit_margin"],
            interpretation="",
        )

        client, _, override_key = _make_client_with_planner(ScriptedPlanner(plan_with_unresolved))
        try:
            resp = client.post("/api/ask", json={"question": "what is our profit margin?"})
            assert resp.status_code == 200
            body = resp.json()
            assert body["type"] == "clarify"
            assert "profit_margin" in body["unresolved_terms"]
            assert len(body["alternatives"]) >= 2
        finally:
            app.dependency_overrides.pop(override_key, None)


# ---------------------------------------------------------------------------
# 4. Config: ambiguity_threshold default
# ---------------------------------------------------------------------------

class TestConfig:
    def test_ambiguity_threshold_default_is_0_6(self) -> None:
        from app.core.config import settings
        assert settings.ambiguity_threshold == pytest.approx(0.6)
