import os

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.services.ask_service import AskService
from app.repositories.postgres.schema_repository_pg import PostgresSchemaRepository
from app.repositories.postgres.query_repository_pg import PostgresQueryRepository
from app.agent.agent import PydanticAiSqlGenerator
from app.guardrails.sql_validator import validate_sql
from app.core.db import ConnectionFactory


def _is_db_available() -> bool:
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


def _has_api_key() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"))


requires_db = pytest.mark.skipif(not _is_db_available(), reason="DATABASE_URL not set or unreachable")
requires_llm = pytest.mark.skipif(not _has_api_key(), reason="No LLM API key (OPENAI_API_KEY / ANTHROPIC_API_KEY)")


def _build_app() -> FastAPI:
    from app.main import app as _app
    return _app


def _build_test_service() -> AskService:
    conn_factory = ConnectionFactory()
    schema_repo = PostgresSchemaRepository(conn_factory)
    query_repo = PostgresQueryRepository(conn_factory)
    model_name = os.environ.get("MODEL_NAME", "openai:gpt-4o-mini")
    sql_gen = PydanticAiSqlGenerator(model_name, schema_repo)
    return AskService(
        sql_generator=sql_gen,
        schema_repository=schema_repo,
        query_repository=query_repo,
    )


@pytest.mark.integration
@requires_db
class TestSchemaRepository:
    def test_get_tables_returns_public_tables(self):
        conn_factory = ConnectionFactory()
        repo = PostgresSchemaRepository(conn_factory)
        tables = []
        import asyncio
        tables = asyncio.run(repo.get_tables())
        assert "orders" in tables
        assert "customers" in tables

    def test_get_columns_returns_columns_for_table(self):
        conn_factory = ConnectionFactory()
        repo = PostgresSchemaRepository(conn_factory)
        import asyncio
        cols = asyncio.run(repo.get_columns("orders"))
        names = [c.name for c in cols]
        assert "order_id" in names
        assert "customer_id" in names
        assert "total" in names
        assert "status" in names
        assert "created_at" in names


@pytest.mark.integration
@requires_db
class TestQueryRepository:
    def test_execute_select_returns_rows(self):
        conn_factory = ConnectionFactory()
        repo = PostgresQueryRepository(conn_factory)
        import asyncio
        rows = asyncio.run(repo.execute("SELECT COUNT(*) AS cnt FROM orders"))
        assert len(rows) == 1
        assert rows[0]["cnt"] == 10

    def test_execute_join_query(self):
        conn_factory = ConnectionFactory()
        repo = PostgresQueryRepository(conn_factory)
        import asyncio
        rows = asyncio.run(repo.execute(
            "SELECT c.name, COUNT(o.order_id) AS order_count "
            "FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id "
            "GROUP BY c.name ORDER BY order_count DESC"
        ))
        assert len(rows) == 5


@pytest.mark.integration
@requires_db
@requires_llm
class TestAskEndpoint:
    def test_ask_single_table_count(self):
        service = _build_test_service()
        import asyncio
        result = asyncio.run(service.answer("How many orders are there?"))
        assert result.text is not None
        assert "10" in result.text or "ten" in result.text.lower() or "answer" in result.text.lower()
        assert result.sql is not None

    def test_ask_single_table_sum(self):
        service = _build_test_service()
        import asyncio
        result = asyncio.run(service.answer("What is the total revenue from all orders?"))
        assert result.text is not None
        assert result.sql is not None
