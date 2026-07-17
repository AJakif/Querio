"""Routing test: unresolved-term question -> ClarifyResponse with >=2 alternatives."""
import pytest

from app.agent.agent import FakeSqlGenerator
from app.agent.contracts import PlanResult
from app.agent.planner import FakePlanner, Planner
from app.domain.models import ClarifyResponse
from app.repositories.memory.query_repository_memory import InMemoryQueryRepository
from app.repositories.memory.schema_repository_memory import InMemorySchemaRepository
from app.services.ask_service import AskService


class UnresolvedTermPlanner(FakePlanner):
    """Planner stub that marks every question as having unresolved terms."""

    def __init__(self, terms: list[str]) -> None:
        self._terms = terms

    async def plan(self, question: str, **kwargs) -> PlanResult:
        return PlanResult(
            ambiguity_score=0.0,
            assumptions=[],
            unresolved_terms=self._terms,
            interpretation=question,
        )


@pytest.mark.asyncio
async def test_unresolved_term_routes_to_clarify_with_alternatives() -> None:
    """ROUTE-3: unresolved terms cause a ClarifyResponse, not an Answer or error."""
    schema_repo = InMemorySchemaRepository()
    service = AskService(
        sql_generator=FakeSqlGenerator(),
        schema_repository=schema_repo,
        query_repository=InMemoryQueryRepository(),
        planner=UnresolvedTermPlanner(terms=["churn"]),
    )

    result = await service.answer("What is the churn rate?")

    assert isinstance(result, ClarifyResponse), (
        f"Expected ClarifyResponse, got {type(result).__name__}"
    )
    assert len(result.alternatives) >= 2, (
        f"Expected >=2 proxy alternatives, got {len(result.alternatives)}"
    )
    assert result.add_data is True
    assert "churn" in result.unresolved_terms
    # Verify alternatives are schema-grounded (reference real column/table names)
    schema_tables = await schema_repo.get_tables()
    all_columns: list[str] = []
    for t in schema_tables:
        cols = await schema_repo.get_columns(t)
        all_columns.extend(col.name.replace("_", " ") for col in cols)
    combined_text = " ".join(a.question + " " + a.label for a in result.alternatives).lower()
    assert any(col.lower() in combined_text for col in all_columns), (
        "Proxy alternatives should reference at least one real column name"
    )
    # No apology or stack-trace language
    assert "sorry" not in result.statement.lower()
    assert "error" not in result.statement.lower()
    assert "traceback" not in result.statement.lower()
