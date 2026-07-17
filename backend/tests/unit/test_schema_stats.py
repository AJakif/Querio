"""Load-bearing tests for Epic 8 Slice 14: EDA strip / example-question generation.

Test budget: 3 (new service method -- 1 happy, 1 failure, 1 grounding check).
"""
from __future__ import annotations

import pytest

from app.repositories.base import ColumnInfo, QueryRepository, RelationshipInfo, SchemaRepository
from app.repositories.memory.query_repository_memory import InMemoryQueryRepository
from app.services.schema_stats import get_schema_summary


class FixtureSchemaRepository(SchemaRepository):
    """A single-table fixture with one numeric, one date, and one dimension column."""

    def __init__(self, tables: dict[str, list[ColumnInfo]]) -> None:
        self._tables = tables

    async def get_tables(self) -> list[str]:
        return list(self._tables.keys())

    async def get_columns(self, table: str) -> list[ColumnInfo]:
        return list(self._tables.get(table, []))

    async def get_relationships(self) -> list[RelationshipInfo]:
        return []


def _orders_repo() -> FixtureSchemaRepository:
    return FixtureSchemaRepository(
        {
            "orders": [
                ColumnInfo("order_id", "character varying", False),
                ColumnInfo("order_date", "timestamp without time zone", True),
                ColumnInfo("amount", "numeric", True),
                ColumnInfo("customer_segment", "character varying", True),
            ]
        }
    )


@pytest.mark.asyncio
async def test_get_schema_summary_returns_real_stats_not_placeholders() -> None:
    query_repo = InMemoryQueryRepository()
    query_repo.set_return_rows(
        [{"row_count": 1234, "date_min": "2020-01-01", "date_max": "2023-06-15", "headline_total": 98765.43}]
    )

    summary = await get_schema_summary(_orders_repo(), query_repo)

    assert summary.table_name == "orders"
    assert summary.row_count == 1234
    assert summary.date_span_start == "2020-01-01"
    assert summary.date_span_end == "2023-06-15"
    assert summary.headline_label == "Total amount"
    assert summary.headline_value == 98765.43
    assert summary.key_dimension_count == 2  # order_id + customer_segment


@pytest.mark.asyncio
async def test_get_schema_summary_raises_when_schema_has_no_tables() -> None:
    empty_repo = FixtureSchemaRepository({})
    query_repo = InMemoryQueryRepository()

    with pytest.raises(ValueError):
        await get_schema_summary(empty_repo, query_repo)


@pytest.mark.asyncio
async def test_examples_are_grounded_in_real_schema_columns() -> None:
    query_repo = InMemoryQueryRepository()
    query_repo.set_return_rows([{"row_count": 10, "date_min": None, "date_max": None, "headline_total": 5.0}])

    summary = await get_schema_summary(_orders_repo(), query_repo)

    assert 4 <= len(summary.examples) <= 6
    joined = " ".join(e.question for e in summary.examples)
    assert "amount" in joined
    assert "orders" in joined
    # customer_segment is a genuine categorical dimension and should be picked...
    assert "customer_segment" in joined
    # ...while order_id is an identifier column and must never be picked as a
    # grouping dimension (it produced garbage "by order_id" questions before the fix).
    assert "order_id" not in joined
    shapes = {e.answer_shape for e in summary.examples}
    assert "number" in shapes
    assert "chart" in shapes
