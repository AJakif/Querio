import pytest

from unittest.mock import patch

from app.domain.models import Answer, ClarifyingQuestion, SqlQuery
from app.repositories.memory.schema_repository_memory import InMemorySchemaRepository
from app.repositories.memory.query_repository_memory import InMemoryQueryRepository
from app.agent.agent import FakeSqlGenerator, GeneratedSQL


class FakeSqlGeneratorWithClarification(FakeSqlGenerator):
    async def generate(self, question: str, **kwargs) -> GeneratedSQL:
        return GeneratedSQL(
            sql="", explanation="ambiguous",
            requires_clarification=True,
            clarification_question="Which table?",
            clarification_options=["orders", "customers"],
        )


class FakeSqlGeneratorInvalidSql(FakeSqlGenerator):
    async def generate(self, question: str, **kwargs) -> GeneratedSQL:
        return GeneratedSQL(
            sql="DROP TABLE orders", explanation="malicious"
        )


class FakeSqlGeneratorJoin(FakeSqlGenerator):
    async def generate(self, question: str, **kwargs) -> GeneratedSQL:
        return GeneratedSQL(
            sql="SELECT o.order_id, c.name FROM orders o JOIN customers c ON o.customer_id = c.customer_id LIMIT 5",
            explanation="Joined orders with customers.",
        )


class FakeSqlGeneratorClarifyThenAnswer(FakeSqlGenerator):
    def __init__(self):
        self._called = False

    async def generate(self, question: str, **kwargs) -> GeneratedSQL:
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
    async def generate(self, question: str, **kwargs) -> GeneratedSQL:
        return GeneratedSQL(
            sql="SELECT COUNT(*) FROM customers",
            explanation="Counting customers.",
        )


class FakeSqlGeneratorCapturing(FakeSqlGenerator):
    def __init__(self):
        self.last_question: str = ""

    async def generate(self, question: str, **kwargs) -> GeneratedSQL:
        self.last_question = question
        return GeneratedSQL(
            sql="SELECT COUNT(*) FROM uploaded_data",
            explanation="Counting rows.",
        )


class FakeSqlGeneratorCapturingSchemaTables(FakeSqlGenerator):
    """Records the table names visible via schema_repo_override, so a test can
    assert the generator actually had visibility into a combined schema."""

    def __init__(self):
        self.seen_tables: list[str] = []

    async def generate(self, question: str, **kwargs) -> GeneratedSQL:
        schema_repo_override = kwargs.get("schema_repo_override")
        if schema_repo_override is not None:
            self.seen_tables = await schema_repo_override.get_tables()
        return GeneratedSQL(
            sql="SELECT COUNT(*) FROM uploaded_data",
            explanation="Counting rows.",
        )


class FakeSqlGeneratorRepairing(FakeSqlGenerator):
    def __init__(self):
        self.calls: list[str] = []

    async def generate(self, question: str, **kwargs) -> GeneratedSQL:
        self.calls.append(question)
        if "The previous SQL failed" in question:
            return GeneratedSQL(
                sql="SELECT order_id, total_payment_value FROM fct_orders LIMIT 5",
                explanation="Listing orders by payment value.",
            )
        return GeneratedSQL(
            sql="SELECT f.product_id, SUM(f.total_payment_value) AS total_revenue FROM fct_orders AS f GROUP BY f.product_id LIMIT 5",
            explanation="Summing revenue by product.",
        )


class FakeQueryRepositorySchemaErrorThenSuccess:
    def __init__(self):
        self.calls: list[str] = []
        self._failed = False

    async def execute(self, sql: str) -> list[dict]:
        self.calls.append(sql)
        # Only fail on the actual broken SELECT, not on EXPLAIN or DISTINCT queries
        # the validator issues. The validator's calls use these prefixes.
        is_instrumentation = (
            sql.strip().upper().startswith("EXPLAIN")
            or sql.strip().upper().startswith("SELECT DISTINCT")
        )
        if not is_instrumentation and not self._failed:
            self._failed = True
            raise RuntimeError('column f.product_id does not exist')
        return [{"order_id": "ORD001", "total_payment_value": 123.45}]


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
        # Slice 3: text derives from answer_spec.restatement; raw value is in headline
        assert result.answer_spec is not None
        assert result.answer_spec.headline.value == "10"

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
        # Validator adds an EXPLAIN call before the real execution; assert the
        # DROP statement was actually dispatched (at least once).
        assert any("DROP" in s for s in query_repo.executed_sql)

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
        # Slice 3: text is now restatement, not raw rows; assert structural correctness
        assert result.answer_spec is not None
        assert result.answer_spec.restatement
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
        # Slice 3: raw value is in answer_spec.headline, not result.text
        assert result.answer_spec is not None
        assert result.answer_spec.headline.value == "25"
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

    @pytest.mark.asyncio
    async def test_context_note_is_prepended_to_question(self, schema_repo, query_repo):
        gen = FakeSqlGeneratorCapturing()
        from app.services.ask_service import AskService
        service = AskService(
            sql_generator=gen,
            schema_repository=schema_repo,
            query_repository=query_repo,
        )
        query_repo.set_return_rows([{"cnt": 50}])
        result = await service.answer(
            question="How many records?",
            context_note="amt_2 is refund amount in USD",
        )
        assert isinstance(result, Answer)
        assert "Dataset context: amt_2 is refund amount in USD" in gen.last_question
        assert "How many records?" in gen.last_question

    @pytest.mark.asyncio
    async def test_context_note_blank_does_not_alter_question(self, schema_repo, query_repo):
        gen = FakeSqlGeneratorCapturing()
        from app.services.ask_service import AskService
        service = AskService(
            sql_generator=gen,
            schema_repository=schema_repo,
            query_repository=query_repo,
        )
        query_repo.set_return_rows([{"cnt": 50}])
        result = await service.answer("How many records?", context_note="")
        assert isinstance(result, Answer)
        assert gen.last_question == "How many records?"

    @pytest.mark.asyncio
    async def test_context_note_helps_ambiguous_question(self, schema_repo, query_repo):
        gen = FakeSqlGeneratorCapturing()
        from app.services.ask_service import AskService
        service = AskService(
            sql_generator=gen,
            schema_repository=schema_repo,
            query_repository=query_repo,
        )
        query_repo.set_return_rows([{"cnt": 100}])
        result = await service.answer(
            question="What is the total amount?",
            context_note="amount is in USD and refers to refund values",
        )
        assert isinstance(result, Answer)
        assert "Dataset context: amount is in USD" in gen.last_question
        assert "total amount" in gen.last_question

    @pytest.mark.asyncio
    async def test_schema_repo_override_gives_visibility_into_both_schemas(self, query_repo):
        """Regression for Epic 8 Slice 16 bug: when a session has a detected
        cross-dataset join key, the SQL generator must see the uploaded session's
        table AND the seed schema's tables (qualified), not just the session's own
        table -- otherwise cross-dataset suggestion chips ask unanswerable questions."""
        from app.repositories.combined_schema_repository import CombinedSchemaRepository
        from app.services.ask_service import AskService

        session_repo = InMemorySchemaRepository()  # stands in for the upload session's schema
        seed_repo = InMemorySchemaRepository()  # stands in for the seed `marts` schema
        combined = CombinedSchemaRepository(primary=session_repo, secondary=seed_repo, secondary_prefix="marts")

        gen = FakeSqlGeneratorCapturingSchemaTables()
        service = AskService(
            sql_generator=gen,
            schema_repository=session_repo,
            query_repository=query_repo,
        )

        await service.answer(
            question="How many records match on customer_id?",
            schema_repo_override=combined,
        )

        assert "customers" in gen.seen_tables  # primary/session tables stay unqualified
        assert "marts.orders" in gen.seen_tables  # secondary/seed tables are qualified

    @pytest.mark.asyncio
    async def test_schema_error_triggers_single_sql_repair_attempt(self, schema_repo):
        from app.services.ask_service import AskService

        sql_gen = FakeSqlGeneratorRepairing()
        query_repo = FakeQueryRepositorySchemaErrorThenSuccess()
        service = AskService(
            sql_generator=sql_gen,
            schema_repository=schema_repo,
            query_repository=query_repo,
        )

        result = await service.answer("What were the top 5 products by revenue last quarter?")

        assert isinstance(result, Answer)
        # Slice 3: text is restatement; verify repair happened and answer_spec is populated
        assert result.answer_spec is not None
        assert len(sql_gen.calls) == 2
        assert "The previous SQL failed" in sql_gen.calls[1]
        # Validator issues EXPLAIN/DISTINCT calls in addition to the two main executions.
        assert len(query_repo.calls) >= 2


# ---------------------------------------------------------------------------
# Epic 9 Slice 6 — Verified-query cache path
# ---------------------------------------------------------------------------


class CountingSqlGenerator(FakeSqlGenerator):
    """Records how many times generate() is called."""

    def __init__(self) -> None:
        self.call_count: int = 0

    async def generate(self, question: str, **kwargs) -> GeneratedSQL:
        self.call_count += 1
        return await super().generate(question, **kwargs)


@pytest.mark.asyncio
async def test_verified_cache_hit_skips_all_agent_calls():
    """Cache hit on a Verified query makes zero Planner/SqlGenerator/Aggregator calls.

    AC: Matching a Verified query skips agent inference, serves from stored SQL.
    AC: Cache re-executes stored SQL against live DB (not a stale result set).
    """
    from app.repositories.memory.query_record_repository_memory import (
        InMemoryQueryRecordRepository,
    )
    from app.repositories.memory.schema_repository_memory import InMemorySchemaRepository
    from app.repositories.memory.query_repository_memory import InMemoryQueryRepository
    from app.services.ask_service import AskService
    from app.services.verification_service import VerificationService
    from app.domain.models import Fingerprint

    # Set up verified store with one clean Verified query
    qr_repo = InMemoryQueryRecordRepository()
    v_svc = VerificationService(repo=qr_repo)
    fps: list[Fingerprint] = []
    await v_svc.register_query(
        query_id="q-cached",
        sql="SELECT COUNT(*) AS total FROM fct_orders LIMIT 100",
        author="alice",
        question="how many orders?",
        fingerprints=fps,
    )
    await v_svc.verify("q-cached", "bob", fps)

    schema_repo = InMemorySchemaRepository()
    query_repo = InMemoryQueryRepository()
    query_repo.set_return_rows([{"total": 42}])

    counting_gen = CountingSqlGenerator()
    service = AskService(
        sql_generator=counting_gen,
        schema_repository=schema_repo,
        query_repository=query_repo,
        query_record_service=v_svc,
    )

    result = await service.answer("how many orders?")

    assert isinstance(result, Answer)
    # Stored SQL was executed — fresh data returned
    assert "42" in result.text
    # Zero LLM calls (SqlGenerator not called)
    assert counting_gen.call_count == 0


@pytest.mark.asyncio
async def test_drift_to_needs_recheck_bypasses_cache():
    """After fingerprint drift moves a Verified query to Needs recheck, the same
    question must NOT hit the cache — the full pipeline must run instead.

    AC: Needs recheck state always falls through to full pipeline.
    """
    from app.repositories.memory.query_record_repository_memory import (
        InMemoryQueryRecordRepository,
    )
    from app.repositories.memory.schema_repository_memory import InMemorySchemaRepository
    from app.repositories.memory.query_repository_memory import InMemoryQueryRepository
    from app.services.ask_service import AskService
    from app.services.verification_service import VerificationService
    from app.domain.models import Fingerprint

    qr_repo = InMemoryQueryRecordRepository()
    v_svc = VerificationService(repo=qr_repo)

    baseline_fps = [Fingerprint(table="fct_orders", column="status", schema_hash="h1")]
    await v_svc.register_query(
        query_id="q-drift",
        sql="SELECT COUNT(*) AS total FROM fct_orders LIMIT 100",
        author="alice",
        question="how many orders?",
        fingerprints=baseline_fps,
    )
    await v_svc.verify("q-drift", "bob", baseline_fps)

    # Simulate schema drift — moves record to Needs recheck
    drifted_fps = [Fingerprint(table="fct_orders", column="status", schema_hash="h2")]
    record, reasons = await v_svc.check_drift("q-drift", drifted_fps)
    assert reasons, "Expected drift to be detected"

    schema_repo = InMemorySchemaRepository()
    query_repo = InMemoryQueryRepository()
    query_repo.set_return_rows([{"total": 99}])

    counting_gen = CountingSqlGenerator()
    service = AskService(
        sql_generator=counting_gen,
        schema_repository=schema_repo,
        query_repository=query_repo,
        query_record_service=v_svc,
    )

    result = await service.answer("how many orders?")

    assert isinstance(result, Answer)
    # Full pipeline ran — SqlGenerator was called at least once
    assert counting_gen.call_count >= 1


# ---------------------------------------------------------------------------
# BUG-1 regression — verified-query cache dead in production (main.py wiring)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verified_cache_fires_when_wired_as_main_py_does():
    """Regression: main.py must pass query_record_service=verification_service to
    AskService.  Without that kwarg the service has _query_record_service=None and
    _try_verified_cache always returns None — the full LLM pipeline always runs.

    This test mirrors the AppState construction pattern in main.py: one
    VerificationService instance is created and shared between AppState AND
    AskService(query_record_service=).  After fixing main.py a Verified question
    should hit the cache (SqlGenerator call_count == 0).
    """
    from app.repositories.memory.query_record_repository_memory import InMemoryQueryRecordRepository
    from app.repositories.memory.schema_repository_memory import InMemorySchemaRepository
    from app.repositories.memory.query_repository_memory import InMemoryQueryRepository
    from app.services.ask_service import AskService
    from app.services.verification_service import VerificationService
    from app.domain.models import Fingerprint

    # Mirror main.py: single VerificationService instance shared with AskService
    qr_repo = InMemoryQueryRecordRepository()
    verification_service = VerificationService(repo=qr_repo)
    fps: list[Fingerprint] = []
    await verification_service.register_query(
        query_id="q-main-wiring",
        sql="SELECT COUNT(*) AS total FROM fct_orders LIMIT 100",
        author="alice",
        question="total orders please",
        fingerprints=fps,
    )
    await verification_service.verify("q-main-wiring", "bob", fps)

    schema_repo = InMemorySchemaRepository()
    query_repo = InMemoryQueryRepository()
    query_repo.set_return_rows([{"total": 7}])

    counting_gen = CountingSqlGenerator()
    # The fix: query_record_service= receives the SAME VerificationService that
    # received the verify() call above.  Pre-fix this kwarg was absent → None.
    service = AskService(
        sql_generator=counting_gen,
        schema_repository=schema_repo,
        query_repository=query_repo,
        query_record_service=verification_service,
    )

    result = await service.answer("total orders please")

    assert isinstance(result, Answer)
    # Cache hit → LLM pipeline must not have run
    assert counting_gen.call_count == 0, (
        "SqlGenerator was called, meaning the cache was NOT consulted — "
        "check that main.py passes query_record_service=verification_service to AskService"
    )
