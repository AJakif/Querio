"""Load-bearing test for Epic 8 Slice 16 bug fix: cross-dataset suggestion chips
promise questions spanning the upload session AND the seed `marts` schema, but
the agent's schema tool only ever saw the session schema. CombinedSchemaRepository
fixes this by exposing both, qualifying only the secondary (seed) schema's tables.
"""
from __future__ import annotations

import pytest

from app.repositories.base import ColumnInfo, RelationshipInfo, SchemaRepository
from app.repositories.combined_schema_repository import CombinedSchemaRepository


class _FixtureSchemaRepository(SchemaRepository):
    def __init__(self, tables: dict[str, list[ColumnInfo]]) -> None:
        self._tables = tables

    async def get_tables(self) -> list[str]:
        return list(self._tables.keys())

    async def get_columns(self, table: str) -> list[ColumnInfo]:
        return list(self._tables.get(table, []))

    async def get_relationships(self) -> list[RelationshipInfo]:
        return []


@pytest.mark.asyncio
async def test_get_tables_qualifies_secondary_but_not_primary() -> None:
    primary = _FixtureSchemaRepository({"uploaded_data": [ColumnInfo("customer_id", "text", True)]})
    secondary = _FixtureSchemaRepository(
        {
            "fct_orders": [ColumnInfo("order_id", "character varying", False)],
            "dim_customers": [ColumnInfo("customer_id", "character varying", False)],
        }
    )
    combined = CombinedSchemaRepository(primary=primary, secondary=secondary, secondary_prefix="marts")

    tables = await combined.get_tables()

    assert "uploaded_data" in tables
    assert "marts.fct_orders" in tables
    assert "marts.dim_customers" in tables
    # The primary session table must stay unqualified so single-dataset
    # questions (existing behavior) don't regress.
    assert "fct_orders" not in tables


@pytest.mark.asyncio
async def test_get_columns_strips_secondary_prefix_before_delegating() -> None:
    primary = _FixtureSchemaRepository({"uploaded_data": [ColumnInfo("customer_id", "text", True)]})
    secondary = _FixtureSchemaRepository(
        {"fct_orders": [ColumnInfo("order_id", "character varying", False), ColumnInfo("total_items", "integer", True)]}
    )
    combined = CombinedSchemaRepository(primary=primary, secondary=secondary, secondary_prefix="marts")

    columns = await combined.get_columns("marts.fct_orders")

    assert [c.name for c in columns] == ["order_id", "total_items"]
