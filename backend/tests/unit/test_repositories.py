import pytest

from app.repositories.base import SchemaRepository, QueryRepository, ColumnInfo


class TestSchemaRepository:
    def test_abc_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            SchemaRepository()

    def test_concrete_implementation_returns_tables(self):
        from app.repositories.memory.schema_repository_memory import InMemorySchemaRepository
        repo = InMemorySchemaRepository()
        import asyncio
        tables = asyncio.run(repo.get_tables())
        assert "orders" in tables
        assert "customers" in tables

    def test_concrete_implementation_returns_columns(self):
        from app.repositories.memory.schema_repository_memory import InMemorySchemaRepository
        repo = InMemorySchemaRepository()
        import asyncio
        cols = asyncio.run(repo.get_columns("orders"))
        assert len(cols) > 0
        assert all(isinstance(c, ColumnInfo) for c in cols)


class TestQueryRepository:
    def test_abc_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            QueryRepository()

    def test_concrete_implementation_executes_and_returns_rows(self):
        from app.repositories.memory.query_repository_memory import InMemoryQueryRepository
        repo = InMemoryQueryRepository()
        repo.set_return_rows([{"cnt": 5}])
        import asyncio
        rows = asyncio.run(repo.execute("SELECT count(*) FROM orders"))
        assert rows == [{"cnt": 5}]
        assert repo.executed_sql == ["SELECT count(*) FROM orders"]


class TestColumnInfo:
    def test_column_info_fields(self):
        col = ColumnInfo(name="id", data_type="integer", is_nullable=False)
        assert col.name == "id"
        assert col.data_type == "integer"
        assert col.is_nullable is False
