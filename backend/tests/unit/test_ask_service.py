import pytest

from app.domain.models import Answer, ClarifyingQuestion
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
        assert "could not process" in result.text.lower()
