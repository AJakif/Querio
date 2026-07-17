"""Load-bearing tests for Slice 2: Validator fingerprints and cost.

Test budget: 5 (within soft ceiling — each maps 1:1 to an acceptance criterion).
"""
from __future__ import annotations

import pytest

from app.agent.validator import Validator
from app.domain.models import ValidationResult
from app.repositories.base import ColumnInfo, QueryRepository, RelationshipInfo, SchemaRepository


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class MutableSchemaRepository(SchemaRepository):
    """Writable in-memory schema, allowing column mutations between validate calls."""

    def __init__(self, tables: dict[str, list[ColumnInfo]]) -> None:
        self._tables = tables

    async def get_tables(self) -> list[str]:
        return list(self._tables.keys())

    async def get_columns(self, table: str) -> list[ColumnInfo]:
        return list(self._tables.get(table, []))

    async def get_relationships(self) -> list[RelationshipInfo]:
        return []


class PatternQueryRepository(QueryRepository):
    """Returns specific rows when SQL contains a registered substring; falls back to default."""

    def __init__(self) -> None:
        self._responses: list[tuple[str, list[dict]]] = []
        self._default: list[dict] = []

    def when(self, pattern: str, rows: list[dict]) -> None:
        self._responses.append((pattern.lower(), rows))

    def set_default(self, rows: list[dict]) -> None:
        self._default = rows

    async def execute(self, sql: str) -> list[dict]:
        lower = sql.lower()
        for pattern, rows in self._responses:
            if pattern in lower:
                return list(rows)
        return list(self._default)


# ---------------------------------------------------------------------------
# 1. Full ValidationResult shape
# ---------------------------------------------------------------------------


class TestValidationResultShape:
    @pytest.mark.asyncio
    async def test_result_contains_deps_fingerprints_and_cost(self) -> None:
        """ValidationResult has a populated dependency_set, fingerprints, and scan_cost."""
        schema_repo = MutableSchemaRepository(
            {
                "orders": [
                    ColumnInfo("order_id", "character varying", False),
                    ColumnInfo("order_status", "character varying", True),
                ]
            }
        )
        query_repo = PatternQueryRepository()
        query_repo.when(
            "distinct",
            [{"order_status": "delivered"}, {"order_status": "shipped"}],
        )
        query_repo.set_default([{"order_id": "1", "order_status": "delivered"}])

        result = await Validator().validate(
            "SELECT order_id, order_status FROM orders WHERE order_status = 'delivered'",
            schema_repo,
            query_repo,
        )

        assert isinstance(result, ValidationResult)
        tables_in_deps = {d.table for d in result.dependency_set}
        assert "orders" in tables_in_deps
        assert any(d.column == "order_status" for d in result.dependency_set)
        assert len(result.fingerprints) >= 1
        assert all(fp.schema_hash for fp in result.fingerprints)
        assert isinstance(result.scan_cost, int) and result.scan_cost >= 0


# ---------------------------------------------------------------------------
# 2. schema_hash changes when a dependency column is renamed
# ---------------------------------------------------------------------------


class TestSchemaHashDrift:
    @pytest.mark.asyncio
    async def test_renamed_column_changes_schema_hash(self) -> None:
        """Renaming a column the query depends on produces a different schema_hash."""
        schema_repo = MutableSchemaRepository(
            {"orders": [ColumnInfo("order_status", "character varying", True)]}
        )
        query_repo = PatternQueryRepository()
        query_repo.when("distinct", [{"order_status": "delivered"}])
        query_repo.set_default([])

        validator = Validator()
        sql_before = "SELECT order_status FROM orders WHERE order_status = 'delivered'"
        result_before = await validator.validate(sql_before, schema_repo, query_repo)
        fp_before = next(f for f in result_before.fingerprints if f.column == "order_status")

        # Simulate column rename: schema now has "status" instead of "order_status"
        schema_repo._tables["orders"] = [ColumnInfo("status", "character varying", True)]
        sql_after = "SELECT status FROM orders WHERE status = 'delivered'"
        query_repo2 = PatternQueryRepository()
        query_repo2.when("distinct", [{"status": "delivered"}])
        query_repo2.set_default([])

        result_after = await validator.validate(sql_after, schema_repo, query_repo2)
        fp_after = next(f for f in result_after.fingerprints if f.column == "status")

        assert fp_before.schema_hash != fp_after.schema_hash


# ---------------------------------------------------------------------------
# 3. value_hash changes when a new distinct value appears
# ---------------------------------------------------------------------------


class TestValueHashDrift:
    @pytest.mark.asyncio
    async def test_new_distinct_value_changes_value_hash(self) -> None:
        """Adding a distinct value to a low-card WHERE column changes its value_hash."""
        schema_repo = MutableSchemaRepository(
            {"orders": [ColumnInfo("order_status", "character varying", True)]}
        )
        sql = "SELECT order_status FROM orders WHERE order_status = 'delivered'"

        query_repo_v1 = PatternQueryRepository()
        query_repo_v1.when(
            "distinct",
            [{"order_status": "delivered"}, {"order_status": "shipped"}],
        )
        query_repo_v1.set_default([])

        validator = Validator()
        result_v1 = await validator.validate(sql, schema_repo, query_repo_v1)
        fp_v1 = next(f for f in result_v1.fingerprints if f.column == "order_status")
        assert fp_v1.value_hash is not None, "expected value_hash for WHERE column"

        # New distinct value added
        query_repo_v2 = PatternQueryRepository()
        query_repo_v2.when(
            "distinct",
            [
                {"order_status": "cancelled"},
                {"order_status": "delivered"},
                {"order_status": "shipped"},
            ],
        )
        query_repo_v2.set_default([])

        result_v2 = await validator.validate(sql, schema_repo, query_repo_v2)
        fp_v2 = next(f for f in result_v2.fingerprints if f.column == "order_status")

        assert fp_v1.value_hash != fp_v2.value_hash


# ---------------------------------------------------------------------------
# 4. Unrelated schema change does NOT affect fingerprint
# ---------------------------------------------------------------------------


class TestFingerprintStability:
    @pytest.mark.asyncio
    async def test_unrelated_column_change_leaves_fingerprint_unchanged(self) -> None:
        """Changing a column the query doesn't touch leaves the fingerprint identical."""
        schema_repo = MutableSchemaRepository(
            {
                "orders": [
                    ColumnInfo("order_status", "character varying", True),
                    ColumnInfo("order_id", "character varying", False),
                ]
            }
        )
        query_repo = PatternQueryRepository()
        query_repo.when("distinct", [{"order_status": "delivered"}])
        query_repo.set_default([])

        validator = Validator()
        sql = "SELECT order_status FROM orders WHERE order_status = 'delivered'"

        result_before = await validator.validate(sql, schema_repo, query_repo)
        fp_before = next(f for f in result_before.fingerprints if f.column == "order_status")

        # Mutate an unrelated column (order_id: nullable changes False -> True)
        schema_repo._tables["orders"] = [
            ColumnInfo("order_status", "character varying", True),
            ColumnInfo("order_id", "character varying", True),
        ]

        result_after = await validator.validate(sql, schema_repo, query_repo)
        fp_after = next(f for f in result_after.fingerprints if f.column == "order_status")

        assert fp_before.schema_hash == fp_after.schema_hash
        assert fp_before.value_hash == fp_after.value_hash


# ---------------------------------------------------------------------------
# 5. scan_cost present and sane
# ---------------------------------------------------------------------------


class TestScanCost:
    @pytest.mark.asyncio
    async def test_scan_cost_is_non_negative_int(self) -> None:
        """scan_cost is always a non-negative integer."""
        schema_repo = MutableSchemaRepository(
            {"orders": [ColumnInfo("order_id", "character varying", False)]}
        )
        query_repo = PatternQueryRepository()
        query_repo.set_default(
            [{"order_id": "1"}, {"order_id": "2"}, {"order_id": "3"}]
        )

        result = await Validator().validate(
            "SELECT order_id FROM orders", schema_repo, query_repo
        )

        assert isinstance(result.scan_cost, int)
        assert result.scan_cost >= 0
