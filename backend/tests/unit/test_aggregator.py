"""Load-bearing tests for Slice 3: Aggregator → AnswerSpec contract.

Test budget: 5 (soft ceiling 5). No JUSTIFIED needed.
"""
import pytest

from app.agent.aggregator import FakeAggregator
from app.agent.contracts import Assumption, AnswerSpec, PlanResult


# ---------------------------------------------------------------------------
# 1. Full AnswerSpec shape — stat-only (1×1 result)
# ---------------------------------------------------------------------------

class TestSingleValueResult:
    @pytest.mark.asyncio
    async def test_single_value_produces_null_chart_and_suppression_reason(self) -> None:
        """1×1 result must suppress chart_spec and provide a non-empty suppression_reason."""
        agg = FakeAggregator()
        rows = [{"total_orders": 42}]
        plan = PlanResult()

        spec = await agg.aggregate("how many orders are there", rows, plan)

        assert isinstance(spec, AnswerSpec)
        assert spec.restatement  # always present
        assert spec.chart_spec is None
        assert spec.suppression_reason, "suppression_reason must be non-empty when chart_spec is None"
        assert spec.headline.value == "42"
        assert spec.headline.label == "total orders"


# ---------------------------------------------------------------------------
# 2. Multi-row / category result → non-null chart_spec
# ---------------------------------------------------------------------------

class TestMultiRowResult:
    @pytest.mark.asyncio
    async def test_category_comparison_produces_chart_spec(self) -> None:
        """Multi-row result with a numeric column must emit a non-null chart_spec."""
        agg = FakeAggregator()
        rows = [
            {"category": "electronics", "revenue": 1000},
            {"category": "clothing", "revenue": 800},
            {"category": "books", "revenue": 300},
        ]
        plan = PlanResult()

        spec = await agg.aggregate("revenue by category", rows, plan)

        assert spec.chart_spec is not None
        assert spec.chart_spec.x_key == "category"
        assert spec.chart_spec.y_key == "revenue"
        assert len(spec.chart_spec.data) == 3
        assert spec.suppression_reason is None


# ---------------------------------------------------------------------------
# 3. Row-typed claims carry cells[]
# ---------------------------------------------------------------------------

class TestClaimsTyping:
    @pytest.mark.asyncio
    async def test_row_typed_claim_cites_real_cells(self) -> None:
        """Row-typed claims must carry cells[] referencing actual result-set cells."""
        agg = FakeAggregator()
        rows = [
            {"product": "Widget A", "units_sold": 500},
            {"product": "Widget B", "units_sold": 300},
        ]
        plan = PlanResult()

        spec = await agg.aggregate("units sold by product", rows, plan)

        row_claims = [c for c in spec.claims if c.type == "row"]
        assert row_claims, "Expected at least one row-typed claim for non-trivial results"
        first_claim = row_claims[0]
        assert first_claim.cells, "Row-typed claims must carry cells[]"
        # cells must reference a real column from the result
        assert first_claim.cells[0]["column"] in rows[0]


# ---------------------------------------------------------------------------
# 4. assumptions_ref mirrors plan.assumptions
# ---------------------------------------------------------------------------

class TestAssumptionsRef:
    @pytest.mark.asyncio
    async def test_assumptions_ref_copied_from_plan(self) -> None:
        """assumptions_ref must be an exact copy of plan.assumptions."""
        agg = FakeAggregator()
        assumption = Assumption(
            term="revenue",
            resolution="order_payments.payment_value",
            alternatives=["order_items.price"],
            close_call=True,
        )
        plan = PlanResult(assumptions=[assumption])
        rows = [{"total": 99999}]

        spec = await agg.aggregate("total revenue", rows, plan)

        assert len(spec.assumptions_ref) == 1
        ref = spec.assumptions_ref[0]
        assert ref.term == "revenue"
        assert ref.close_call is True
        assert "order_items.price" in ref.alternatives


# ---------------------------------------------------------------------------
# 5. API integration: answer_spec flows through /ask response
# ---------------------------------------------------------------------------

class TestAnswerSpecInApiResponse:
    def test_answer_spec_present_in_ask_response(self) -> None:
        """Full /ask round-trip: answer_spec is non-null and has the correct shape."""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.api.routes.ask import get_ask_service
        from app.agent.agent import FakeSqlGenerator
        from app.repositories.memory.query_repository_memory import InMemoryQueryRepository
        from app.repositories.memory.schema_repository_memory import InMemorySchemaRepository
        from app.services.ask_service import AskService

        schema_repo = InMemorySchemaRepository()
        query_repo = InMemoryQueryRepository()
        # Multi-row result so chart_spec is populated
        query_repo.set_return_rows([
            {"category": "A", "sales": 100},
            {"category": "B", "sales": 200},
        ])

        async def _override() -> AskService:
            return AskService(
                sql_generator=FakeSqlGenerator(),
                schema_repository=schema_repo,
                query_repository=query_repo,
            )

        app.dependency_overrides[get_ask_service] = _override
        try:
            with TestClient(app) as client:
                resp = client.post("/api/ask", json={"question": "sales by category"})
            assert resp.status_code == 200
            body = resp.json()
            spec = body["answer_spec"]
            assert spec is not None
            assert spec["restatement"]
            assert spec["headline"]["value"]
            assert spec["chart_spec"] is not None
            assert spec["chart_spec"]["x_key"] == "category"
            assert spec["chart_spec"]["y_key"] == "sales"
        finally:
            app.dependency_overrides.pop(get_ask_service, None)
