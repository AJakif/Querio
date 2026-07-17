import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.routes.upload import (
    get_seed_query_repository,
    get_seed_schema_repository,
    get_session_manager,
)
from app.repositories.base import ColumnInfo, RelationshipInfo, SchemaRepository
from app.repositories.memory.query_repository_memory import InMemoryQueryRepository
from app.services.session_manager import SessionManager


class _StubSeedSchemaRepo(SchemaRepository):
    """Seed (marts) schema exposing a customer_id column, without touching Postgres."""

    async def get_tables(self) -> list[str]:
        return ["fct_orders"]

    async def get_columns(self, table: str) -> list[ColumnInfo]:
        if table == "fct_orders":
            return [ColumnInfo("customer_id", "character varying", False)]
        return []

    async def get_relationships(self) -> list[RelationshipInfo]:
        return []


class _StubUploadedSchemaRepo(SchemaRepository):
    async def get_tables(self) -> list[str]:
        return ["uploaded_data"]

    async def get_columns(self, table: str) -> list[ColumnInfo]:
        return [ColumnInfo("customer_id", "character varying", False)]

    async def get_relationships(self) -> list[RelationshipInfo]:
        return []


class _StubSessionManager(SessionManager):
    """Skips real DB DDL/inserts; returns fixed session info and in-memory repos."""

    def __init__(self, uploaded_query_repo: InMemoryQueryRepository):
        super().__init__()
        self._uploaded_query_repo = uploaded_query_repo

    async def create_session_schema(self, preview_token, context_note="", current_session_id=""):
        return "fixed-session-id", 2

    def get_schema_repo(self, session_id: str):
        return _StubUploadedSchemaRepo()

    def get_query_repo(self, session_id: str):
        return self._uploaded_query_repo


@pytest.fixture
def client():
    uploaded_query_repo = InMemoryQueryRepository()
    uploaded_query_repo.set_return_rows([{"v": "CUST-1"}])
    seed_query_repo = InMemoryQueryRepository()
    seed_query_repo.set_return_rows([{"v": "CUST-1"}])

    app.dependency_overrides[get_session_manager] = lambda: _StubSessionManager(uploaded_query_repo)
    app.dependency_overrides[get_seed_schema_repository] = lambda: _StubSeedSchemaRepo()
    app.dependency_overrides[get_seed_query_repository] = lambda: seed_query_repo

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.pop(get_session_manager, None)
    app.dependency_overrides.pop(get_seed_schema_repository, None)
    app.dependency_overrides.pop(get_seed_query_repository, None)


def test_upload_confirm_returns_join_key_suggestions(client: TestClient):
    response = client.post(
        "/api/upload/confirm",
        json={"preview_token": "tok-1", "context_note": "", "current_session_id": ""},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["join_key_column"] == "customer_id"
    assert body["join_key_table"] == "fct_orders"
    assert len(body["suggested_questions"]) >= 2
    assert all("customer_id" in q for q in body["suggested_questions"])
