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

    def test_all_olist_relationships_present(self):
        from app.repositories.memory.schema_repository_memory import InMemorySchemaRepository
        repo = InMemorySchemaRepository()
        import asyncio
        rels = asyncio.run(repo.get_relationships())
        rel_set = {(r.source_table, r.source_column, r.target_table, r.target_column) for r in rels}
        expected = {
            ("orders", "customer_id", "customers", "customer_id"),
            ("order_items", "order_id", "orders", "order_id"),
            ("order_items", "product_id", "products", "product_id"),
            ("order_items", "seller_id", "sellers", "seller_id"),
            ("order_payments", "order_id", "orders", "order_id"),
            ("order_reviews", "order_id", "orders", "order_id"),
        }
        assert rel_set == expected, f"Missing relationships: {expected - rel_set}"

    def test_cross_entity_join_path_resolves(self):
        from app.repositories.memory.schema_repository_memory import InMemorySchemaRepository
        repo = InMemorySchemaRepository()
        import asyncio
        tables = asyncio.run(repo.get_tables())
        assert "orders" in tables
        assert "customers" in tables
        assert "products" in tables
        assert "sellers" in tables
        assert "order_items" in tables
        assert "order_payments" in tables

        rels = asyncio.run(repo.get_relationships())
        source_tables = {r.source_table for r in rels}
        assert "order_items" in source_tables
        assert "order_payments" in source_tables
        assert "orders" in source_tables

        customer_fk = [r for r in rels if r.source_table == "orders" and r.target_table == "customers"]
        assert len(customer_fk) == 1
        assert customer_fk[0].source_column == "customer_id"

    def test_all_tables_have_defined_columns(self):
        from app.repositories.memory.schema_repository_memory import InMemorySchemaRepository
        repo = InMemorySchemaRepository()
        import asyncio
        tables = asyncio.run(repo.get_tables())
        assert len(tables) == 9
        expected_tables = {
            "customers", "geolocation", "products", "sellers",
            "orders", "order_items", "order_payments", "order_reviews",
            "product_categories",
        }
        assert set(tables) == expected_tables
        for t in tables:
            cols = asyncio.run(repo.get_columns(t))
            assert len(cols) > 0, f"Table {t} has no columns"
