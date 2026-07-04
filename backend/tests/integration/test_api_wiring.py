import pytest
from fastapi.testclient import TestClient


class TestAskEndpoint:
    def test_post_ask_returns_answer_shape(self, client: TestClient):
        response = client.post("/api/ask", json={"question": "How many orders?"})
        assert response.status_code == 200
        body = response.json()
        assert body["type"] == "answer"
        assert "answer" in body
        assert isinstance(body["answer"], str)
        assert len(body["answer"]) > 0

    def test_post_ask_sql_is_optional(self, client: TestClient):
        response = client.post("/api/ask", json={"question": "anything"})
        assert response.status_code == 200
        body = response.json()
        assert "sql" in body

    def test_post_ask_chart_is_optional(self, client: TestClient):
        response = client.post("/api/ask", json={"question": "anything"})
        assert response.status_code == 200
        body = response.json()
        assert "chart" in body

    def test_health_returns_ok(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestClarifyRoundTrip:
    @pytest.fixture(autouse=True)
    def _override_service(self, request):
        from app.main import app
        from app.api.routes.ask import get_ask_service
        from app.services.ask_service import AskService
        from app.agent.agent import FakeSqlGenerator, GeneratedSQL
        from app.repositories.memory.schema_repository_memory import InMemorySchemaRepository
        from app.repositories.memory.query_repository_memory import InMemoryQueryRepository
        from app.services.conversation_store import ConversationStore

        class _ClarifyGen(FakeSqlGenerator):
            async def generate(self, question: str) -> GeneratedSQL:
                return GeneratedSQL(
                    sql="", explanation="ambiguous",
                    requires_clarification=True,
                    clarification_question="Which table?",
                    clarification_options=["orders", "customers"],
                )

        store = ConversationStore()
        schema_repo = InMemorySchemaRepository()
        query_repo = InMemoryQueryRepository()
        query_repo.set_return_rows([{"cnt": 25}])

        async def _override() -> AskService:
            return AskService(
                sql_generator=_ClarifyGen(),
                schema_repository=schema_repo,
                query_repository=query_repo,
                conversation_store=store,
            )

        app.dependency_overrides[get_ask_service] = _override
        yield
        app.dependency_overrides.clear()

    def test_clarify_returns_conversation_id(self, client):
        response = client.post("/api/ask", json={"question": "Show me customers"})
        assert response.status_code == 200
        body = response.json()
        assert body["type"] == "clarifying_question"
        assert "conversation_id" in body
        assert len(body["conversation_id"]) > 0


class TestGuardrailRejection:
    @pytest.fixture(autouse=True)
    def _override_service(self):
        from app.main import app
        from app.api.routes.ask import get_ask_service
        from app.services.ask_service import AskService
        from app.repositories.memory.schema_repository_memory import InMemorySchemaRepository
        from app.repositories.memory.query_repository_memory import InMemoryQueryRepository
        from app.agent.agent import FakeSqlGenerator, GeneratedSQL

        class InvalidSqlGen(FakeSqlGenerator):
            async def generate(self, question: str) -> GeneratedSQL:
                return GeneratedSQL(sql="DROP TABLE orders", explanation="malicious")

        async def _override() -> AskService:
            return AskService(
                sql_generator=InvalidSqlGen(),
                schema_repository=InMemorySchemaRepository(),
                query_repository=InMemoryQueryRepository(),
            )

        app.dependency_overrides[get_ask_service] = _override
        yield
        app.dependency_overrides.clear()

    def test_guardrail_rejection_returns_200(self, client: TestClient):
        response = client.post("/api/ask", json={"question": "Delete all orders"})
        assert response.status_code == 200

    def test_guardrail_rejection_has_answer_type(self, client: TestClient):
        response = client.post("/api/ask", json={"question": "Delete all orders"})
        body = response.json()
        assert body.get("type") == "answer"

    def test_guardrail_rejection_friendly_message(self, client: TestClient):
        response = client.post("/api/ask", json={"question": "Delete all orders"})
        body = response.json()
        msg = body.get("answer", "")
        assert "look up data" in msg.lower()
        assert len(msg) > 10
        assert "{" not in msg  # no raw Python dict leak
        assert "Traceback" not in msg  # no stack trace leak
