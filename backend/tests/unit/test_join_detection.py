import pytest

from app.repositories.base import ColumnInfo, RelationshipInfo, SchemaRepository
from app.repositories.memory.query_repository_memory import InMemoryQueryRepository
from app.services.join_detection import detect_cross_dataset_join


class _FakeSchemaRepo(SchemaRepository):
    def __init__(self, tables: dict[str, list[ColumnInfo]]):
        self._tables = tables

    async def get_tables(self) -> list[str]:
        return list(self._tables.keys())

    async def get_columns(self, table: str) -> list[ColumnInfo]:
        return self._tables.get(table, [])

    async def get_relationships(self) -> list[RelationshipInfo]:
        return []


@pytest.mark.asyncio
async def test_detects_shared_customer_id_and_suggests_questions():
    uploaded_schema = _FakeSchemaRepo({
        "uploaded_data": [
            ColumnInfo("customer_id", "character varying", False),
            ColumnInfo("loyalty_score", "numeric", True),
        ],
    })
    seed_schema = _FakeSchemaRepo({
        "fct_orders": [ColumnInfo("customer_id", "character varying", False)],
        "dim_customers": [ColumnInfo("customer_id", "character varying", False)],
    })

    uploaded_query = InMemoryQueryRepository()
    uploaded_query.set_return_rows([{"v": "CUST-1"}, {"v": "CUST-2"}])
    seed_query = InMemoryQueryRepository()
    seed_query.set_return_rows([{"v": "CUST-1"}, {"v": "CUST-9"}])

    result = await detect_cross_dataset_join(
        uploaded_table="uploaded_data",
        uploaded_schema_repo=uploaded_schema,
        uploaded_query_repo=uploaded_query,
        seed_schema_repo=seed_schema,
        seed_query_repo=seed_query,
    )

    assert result.detected
    assert result.column == "customer_id"
    assert 2 <= len(result.questions) <= 3
    assert all("customer_id" in q for q in result.questions)


@pytest.mark.asyncio
async def test_no_suggestions_when_no_plausible_join_key():
    uploaded_schema = _FakeSchemaRepo({
        "uploaded_data": [ColumnInfo("favorite_color", "character varying", True)],
    })
    seed_schema = _FakeSchemaRepo({
        "fct_orders": [ColumnInfo("customer_id", "character varying", False)],
    })

    uploaded_query = InMemoryQueryRepository()
    seed_query = InMemoryQueryRepository()

    result = await detect_cross_dataset_join(
        uploaded_table="uploaded_data",
        uploaded_schema_repo=uploaded_schema,
        uploaded_query_repo=uploaded_query,
        seed_schema_repo=seed_schema,
        seed_query_repo=seed_query,
    )

    assert not result.detected
    assert result.questions == []
