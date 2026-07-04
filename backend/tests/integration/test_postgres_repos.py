import os
import pytest

from app.repositories.base import ColumnInfo, SchemaRepository, QueryRepository

# Module-level import + instantiation: fails RED if module doesn't exist
# or abstract methods (get_relationships) are not implemented.
from app.repositories.postgres.schema_repository_pg import PostgresSchemaRepository  # noqa: F401
from app.repositories.postgres.query_repository_pg import PostgresQueryRepository  # noqa: F401

# Instantiate at module level to verify all ABC methods are implemented
# This will raise TypeError if get_relationships() is missing.
_ = PostgresSchemaRepository()  # noqa: F811
_ = PostgresQueryRepository()  # noqa: F811


def _db_available() -> bool:
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        return False
    try:
        import psycopg2
        conn = psycopg2.connect(dsn)
        conn.close()
        return True
    except Exception:
        return False


requires_db = pytest.mark.skipif(not _db_available(), reason="DATABASE_URL not set or unreachable")


@requires_db
class TestPostgresSchemaRepository:
    def test_implements_schema_repository_interface(self):
        from app.repositories.postgres.schema_repository_pg import PostgresSchemaRepository
        repo = PostgresSchemaRepository()
        assert isinstance(repo, SchemaRepository)

    @pytest.mark.asyncio
    async def test_get_tables_returns_public_tables(self):
        from app.repositories.postgres.schema_repository_pg import PostgresSchemaRepository
        repo = PostgresSchemaRepository()
        tables = await repo.get_tables()
        assert len(tables) > 0
        assert all(isinstance(t, str) for t in tables)

    @pytest.mark.asyncio
    async def test_get_columns_returns_column_info(self):
        from app.repositories.postgres.schema_repository_pg import PostgresSchemaRepository
        repo = PostgresSchemaRepository()
        tables = await repo.get_tables()
        assert len(tables) > 0
        cols = await repo.get_columns(tables[0])
        assert len(cols) > 0
        assert all(isinstance(c, ColumnInfo) for c in cols)


@requires_db
class TestPostgresSchemaRepositoryRelationships:
    @pytest.mark.asyncio
    async def test_get_relationships_returns_foreign_keys(self):
        from app.repositories.postgres.schema_repository_pg import PostgresSchemaRepository
        repo = PostgresSchemaRepository()
        rels = await repo.get_relationships()
        assert len(rels) > 0
        has_customer_fk = any(
            r.source_table == "orders" and r.target_table == "customers"
            for r in rels
        )
        assert has_customer_fk, "Expected FK from orders.customer_id → customers.customer_id"


@requires_db
class TestPostgresQueryRepository:
    @pytest.mark.asyncio
    async def test_implements_query_repository_interface(self):
        from app.repositories.postgres.query_repository_pg import PostgresQueryRepository
        repo = PostgresQueryRepository()
        assert isinstance(repo, QueryRepository)

    @pytest.mark.asyncio
    async def test_execute_select_returns_rows(self):
        from app.repositories.postgres.query_repository_pg import PostgresQueryRepository
        repo = PostgresQueryRepository()
        rows = await repo.execute("SELECT 1 AS val")
        assert len(rows) == 1
        assert rows[0]["val"] == 1
