import pytest

from unittest.mock import patch

from app.domain.models import Answer, ClarifyingQuestion, SqlQuery
from app.repositories.memory.schema_repository_memory import InMemorySchemaRepository
from app.repositories.memory.query_repository_memory import InMemoryQueryRepository
from app.agent.agent import FakeSqlGenerator, GeneratedSQL


class FakeSqlGeneratorWithClarification(FakeSqlGenerator):
    async def generate(self, question: str) -> GeneratedSQL:
        return GeneratedSQL(
            sql="", explanation="ambiguous",
            requires_clarification=True,
            clarification_question="Which table?",
            clarification_options=["orders", "customers"],
        )


class FakeSqlGeneratorInvalidSql(FakeSqlGenerator):
    async def generate(self, question: str) -> GeneratedSQL:
        return GeneratedSQL(
            sql="DROP TABLE orders", explanation="malicious"
        )


class FakeSqlGeneratorJoin(FakeSqlGenerator):
    async def generate(self, question: str) -> GeneratedSQL:
        return GeneratedSQL(
            sql="SELECT o.order_id, c.name FROM orders o JOIN customers c ON o.customer_id = c.customer_id LIMIT 5",
            explanation="Joined orders with customers.",
        )


class FakeSqlGeneratorClarifyThenAnswer(FakeSqlGenerator):
    def __init__(self):
        self._called = False

    async def generate(self, question: str) -> GeneratedSQL:
        if not self._called:
            self._called = True
            return GeneratedSQL(
                sql="", explanation="ambiguous",
                requires_clarification=True,
                clarification_question="Which table?",
                clarification_options=["orders", "customers"],
            )
        correct_sql = "SELECT COUNT(*) FROM customers"
        return GeneratedSQL(sql=correct_sql, explanation="Counting customers.")


class FakeSqlGeneratorClarifyAnswer(FakeSqlGenerator):
    async def generate(self, question: str) -> GeneratedSQL:
        return GeneratedSQL(
            sql="SELECT COUNT(*) FROM customers",
            explanation="Counting customers.",
        )


class TestAskService:
    @pytest.fixture
    def schema_repo(self):
        return InMemorySchemaRepository()

    @pytest.fixture
    def query_repo(self):
        repo = InMemoryQueryRepository()
        repo.set_return_rows([{"order_count": 10}])
        return repo

    @pytest.fixture
    def sql_gen(self):
        return FakeSqlGenerator()

    @pytest.fixture
    def service(self, sql_gen, schema_repo, query_repo):
        from app.services.ask_service import AskService
        return AskService(
            sql_generator=sql_gen,
            schema_repository=schema_repo,
            query_repository=query_repo,
        )

    @pytest.mark.asyncio
    async def test_answer_returns_answer_with_text(self, service):
        result = await service.answer("How many orders?")
        assert isinstance(result, Answer)
        assert result.text is not None
        assert len(result.text) > 0

    @pytest.mark.asyncio
    async def test_answer_includes_sql(self, service):
        result = await service.answer("How many orders?")
        assert isinstance(result, Answer)
        assert result.sql is not None
        assert "COUNT" in result.sql.sql

    @pytest.mark.asyncio
    async def test_answer_includes_query_result(self, service):
        result = await service.answer("How many orders?")
        assert isinstance(result, Answer)
        assert "10" in result.text

    @pytest.mark.asyncio
    async def test_clarifying_question_returned_when_ambiguous(self, schema_repo, query_repo):
        gen = FakeSqlGeneratorWithClarification()
        from app.services.ask_service import AskService
        service = AskService(
            sql_generator=gen,
            schema_repository=schema_repo,
            query_repository=query_repo,
        )
        result = await service.answer("Show me customers")
        assert isinstance(result, ClarifyingQuestion)
        assert "Which table?" in result.question

    @pytest.mark.asyncio
    async def test_guardrail_blocks_invalid_sql(self, schema_repo, query_repo):
        gen = FakeSqlGeneratorInvalidSql()
        from app.services.ask_service import AskService
        service = AskService(
            sql_generator=gen,
            schema_repository=schema_repo,
            query_repository=query_repo,
        )
        result = await service.answer("Drop something")
        assert isinstance(result, Answer)
        assert "look up data" in result.text.lower()

    @pytest.mark.asyncio
    async def test_guardrail_blocked_would_succeed_without_guardrail(self, schema_repo, query_repo):
        from app.services.ask_service import AskService
        gen = FakeSqlGeneratorInvalidSql()
        query_repo.set_return_rows([{"dropped": True}])
        service = AskService(
            sql_generator=gen,
            schema_repository=schema_repo,
            query_repository=query_repo,
        )
        result = await service.answer("Drop something")
        assert isinstance(result, Answer)
        assert "look up data" in result.text.lower()
        assert query_repo.executed_sql == []

    @pytest.mark.asyncio
    async def test_bypassing_guardrail_executes_query(self, schema_repo, query_repo):
        from app.services.ask_service import AskService
        from app.guardrails.sql_validator import validate_sql as real_validate
        gen = FakeSqlGeneratorInvalidSql()
        query_repo.set_return_rows([{"dropped": True}])
        with patch("app.services.ask_service.validate_sql", return_value=("DROP TABLE orders", None)):
            service = AskService(
                sql_generator=gen,
                schema_repository=schema_repo,
                query_repository=query_repo,
            )
            result = await service.answer("Drop something")
        assert isinstance(result, Answer)
        assert "look up data" not in result.text.lower()
        assert len(query_repo.executed_sql) == 1
        assert "DROP" in query_repo.executed_sql[0]

    @pytest.mark.asyncio
    async def test_multi_table_join_returns_joined_data(self, schema_repo, query_repo):
        gen = FakeSqlGeneratorJoin()
        query_repo.set_return_rows([
            {"order_id": 1, "name": "Alice"},
            {"order_id": 2, "name": "Bob"},
        ])
        from app.services.ask_service import AskService
        service = AskService(
            sql_generator=gen,
            schema_repository=schema_repo,
            query_repository=query_repo,
        )
        result = await service.answer("Show me orders with customer names")
        assert isinstance(result, Answer)
        assert "Alice" in result.text
        assert "Bob" in result.text
        assert "JOIN" in result.sql.sql
        assert result.sql.explanation == "Joined orders with customers."

    @pytest.mark.asyncio
    async def test_clarifying_question_includes_conversation_id(self, schema_repo, query_repo):
        gen = FakeSqlGeneratorWithClarification()
        from app.services.ask_service import AskService
        from app.services.conversation_store import ConversationStore
        store = ConversationStore()
        service = AskService(
            sql_generator=gen,
            schema_repository=schema_repo,
            query_repository=query_repo,
            conversation_store=store,
        )
        result = await service.answer("Show me customers")
        assert isinstance(result, ClarifyingQuestion)
        assert result.conversation_id is not None
        assert len(result.conversation_id) > 0
        ctx = store.get(result.conversation_id)
        assert ctx is not None
        assert ctx.original_question == "Show me customers"

    @pytest.mark.asyncio
    async def test_clarification_answer_returns_correct_result(self, schema_repo, query_repo):
        query_repo.set_return_rows([{"cnt": 25}])
        from app.services.ask_service import AskService
        from app.services.conversation_store import ConversationStore
        store = ConversationStore()
        conv_id = store.create("Show me customers", ["orders", "customers"])
        gen = FakeSqlGeneratorClarifyAnswer()
        service = AskService(
            sql_generator=gen,
            schema_repository=schema_repo,
            query_repository=query_repo,
            conversation_store=store,
        )
        result = await service.answer(
            question="customers",
            conversation_id=conv_id,
            clarification_answer="customers",
        )
        assert isinstance(result, Answer)
        assert "25" in result.text
        assert result.conversation_id is not None

    @pytest.mark.asyncio
    async def test_invalid_conversation_id_returns_clear_error(self, schema_repo, query_repo):
        from app.services.ask_service import AskService
        from app.services.conversation_store import ConversationStore
        store = ConversationStore()
        service = AskService(
            sql_generator=FakeSqlGenerator(),
            schema_repository=schema_repo,
            query_repository=query_repo,
            conversation_store=store,
        )
        result = await service.answer(
            question="count",
            conversation_id="bad-id",
            clarification_answer="count",
        )
        assert isinstance(result, Answer)
        assert "conversation" in result.text.lower() or "try again" in result.text.lower()
