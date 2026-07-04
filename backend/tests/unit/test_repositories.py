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


class TestRelationshipInfo:
    def test_relationship_info_fields(self):
        from app.repositories.base import RelationshipInfo
        rel = RelationshipInfo(
            source_table="orders", source_column="customer_id",
            target_table="customers", target_column="customer_id",
        )
        assert rel.source_table == "orders"
        assert rel.source_column == "customer_id"
        assert rel.target_table == "customers"
        assert rel.target_column == "customer_id"


class TestSchemaRepositoryRelationships:
    def test_relationships_returns_list(self):
        from app.repositories.memory.schema_repository_memory import InMemorySchemaRepository
        repo = InMemorySchemaRepository()
        import asyncio
        rels = asyncio.run(repo.get_relationships())
        assert len(rels) > 0
        assert all(
            hasattr(r, "source_table") and hasattr(r, "target_table")
            for r in rels
        )
