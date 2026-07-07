import time
import uuid
from numbers import Number

from app.domain.models import Answer, SqlQuery, ClarifyingQuestion, ChartSpec, ChartType
from app.repositories.base import SchemaRepository, QueryRepository
from app.agent.agent import SqlGenerator, GeneratedSQL
from app.guardrails.sql_validator import validate_sql
from app.services.conversation_store import ConversationStore
from app.core.config import settings
from app.core.logging import get_logger


logger = get_logger("ask_service")


class AskService:
    def __init__(
        self,
        sql_generator: SqlGenerator,
        schema_repository: SchemaRepository,
        query_repository: QueryRepository,
        conversation_store: ConversationStore | None = None,
    ):
        self._sql_generator = sql_generator
        self._schema_repo = schema_repository
        self._query_repo = query_repository
        self._conversation_store = conversation_store or ConversationStore()

    async def _session_schema_repo(self, session_schema: str) -> SchemaRepository | None:
        if not session_schema:
            return None
        from app.repositories.postgres.schema_repository_pg import PostgresSchemaRepository
        return PostgresSchemaRepository(schema=session_schema)

    async def _session_query_repo(self, session_schema: str) -> QueryRepository | None:
        if not session_schema:
            return None
        from app.repositories.postgres.query_repository_pg import PostgresQueryRepository
        return PostgresQueryRepository(schema_override=session_schema)

    async def answer(
        self,
        question: str,
        conversation_id: str | None = None,
        clarification_answer: str | None = None,
        request_id: str | None = None,
        session_schema: str | None = None,
    ) -> Answer | ClarifyingQuestion:
        request_id = request_id or str(uuid.uuid4())
        started_at = time.perf_counter()
        schema_repo = await self._session_schema_repo(session_schema) if session_schema else None
        query_repo = await self._session_query_repo(session_schema) if session_schema else None
        logger.info(
            "Processing ask request",
            extra={
                "request_id": request_id,
                "conversation_id": conversation_id,
                "question": question,
                "selected_provider": settings.effective_model_provider,
                "has_clarification_answer": clarification_answer is not None,
                "session_schema": session_schema,
            },
        )
        if conversation_id and clarification_answer is not None:
            ctx = self._conversation_store.get(conversation_id)
            if ctx is None:
                logger.warning(
                    "Conversation not found",
                    extra={"request_id": request_id, "conversation_id": conversation_id},
                )
                return Answer(text="Sorry, I couldn't find that conversation. Please try asking your question again.")
            self._conversation_store.complete(conversation_id)
            combined_question = _combine_clarification(ctx.original_question, clarification_answer)
            return await self._execute_answer(combined_question, conversation_id, request_id, started_at, schema_repo=schema_repo, query_repo=query_repo)

        generated = await self._sql_generator.generate(question, schema_repo_override=schema_repo)

        if generated.requires_clarification:
            conv_id = self._conversation_store.create(question, generated.clarification_options)
            logger.info(
                "Clarification required",
                extra={
                    "request_id": request_id,
                    "conversation_id": conv_id,
                    "options_count": len(generated.clarification_options),
                },
            )
            return ClarifyingQuestion(
                question=generated.clarification_question or "What did you mean?",
                options=generated.clarification_options,
                conversation_id=conv_id,
            )

        return await self._do_execute(generated, question, conversation_id, request_id, started_at, query_repo=query_repo, schema_repo=schema_repo)

    async def _do_execute(
        self,
        generated: GeneratedSQL,
        question: str,
        conversation_id: str | None = None,
        request_id: str | None = None,
        started_at: float | None = None,
        allow_repair: bool = True,
        query_repo: QueryRepository | None = None,
        schema_repo: SchemaRepository | None = None,
    ) -> Answer | ClarifyingQuestion:
        effective_query_repo = query_repo or self._query_repo
        effective_schema_repo = schema_repo or self._schema_repo
        safe_sql, error = validate_sql(generated.sql, max_rows=settings.max_rows)
        if error:
            logger.warning(
                "SQL blocked by guardrail",
                extra={
                    "request_id": request_id,
                    "conversation_id": conversation_id,
                    "generated_sql": generated.sql,
                    "guardrail_status": "fail",
                    "execution_time_ms": _elapsed_ms(started_at),
                },
            )
            return Answer(text=error, conversation_id=conversation_id)

        logger.debug("Executing SQL", extra={"request_id": request_id, "conversation_id": conversation_id, "sql": safe_sql})
        try:
            rows = await effective_query_repo.execute(safe_sql or generated.sql)
        except Exception as exc:
            if allow_repair and _is_retriable_schema_error(exc):
                logger.warning(
                    "SQL execution failed with retriable schema error; requesting model correction",
                    extra={
                        "request_id": request_id,
                        "conversation_id": conversation_id,
                        "generated_sql": generated.sql,
                        "error_type": exc.__class__.__name__,
                        "execution_time_ms": _elapsed_ms(started_at),
                    },
                )
                repaired = await self._sql_generator.generate(
                    _build_repair_prompt(question, generated.sql, exc),
                    schema_repo_override=schema_repo,
                )
                if repaired.requires_clarification:
                    conv_id = self._conversation_store.create(question, repaired.clarification_options)
                    return ClarifyingQuestion(
                        question=repaired.clarification_question or "What did you mean?",
                        options=repaired.clarification_options,
                        conversation_id=conv_id,
                    )
                return await self._do_execute(
                    repaired,
                    question,
                    conversation_id,
                    request_id,
                    started_at,
                    allow_repair=False,
                    query_repo=query_repo,
                    schema_repo=schema_repo,
                )

            logger.exception(
                "SQL execution failed",
                extra={
                    "request_id": request_id,
                    "conversation_id": conversation_id,
                    "generated_sql": generated.sql,
                    "guardrail_status": "pass",
                    "execution_time_ms": _elapsed_ms(started_at),
                },
            )
            return Answer(
                text="Sorry, I couldn't safely answer that request. Please try rephrasing it.",
                conversation_id=conversation_id,
            )
        logger.info(
            "SQL executed",
            extra={
                "request_id": request_id,
                "conversation_id": conversation_id,
                "question": question,
                "selected_provider": settings.effective_model_provider,
                "generated_sql": generated.sql,
                "guardrail_status": "pass",
                "execution_time_ms": _elapsed_ms(started_at),
                "row_count": len(rows),
            },
        )

        if not rows:
            logger.info("Query returned no rows", extra={"conversation_id": conversation_id})
            return Answer(
                text="The query returned no results.",
                sql=SqlQuery(sql=generated.sql, explanation=generated.explanation),
                conversation_id=conversation_id,
            )

        answer_text = _format_answer(rows, generated)
        chart = _build_chart(question, rows)
        return Answer(
            text=answer_text,
            chart=chart,
            sql=SqlQuery(sql=generated.sql, explanation=generated.explanation),
            conversation_id=conversation_id,
        )

    async def _execute_answer(
        self,
        question: str,
        conversation_id: str,
        request_id: str | None = None,
        started_at: float | None = None,
        schema_repo: SchemaRepository | None = None,
        query_repo: QueryRepository | None = None,
    ) -> Answer | ClarifyingQuestion:
        generated = await self._sql_generator.generate(question, schema_repo_override=schema_repo)
        return await self._do_execute(generated, question, conversation_id, request_id, started_at, query_repo=query_repo, schema_repo=schema_repo)


def _format_answer(rows: list[dict], generated: GeneratedSQL) -> str:
    if len(rows) == 1 and len(rows[0]) == 1:
        val = list(rows[0].values())[0]
        return f"The answer is **{val}**."

    count = len(rows)
    if count <= 5:
        lines = [f"- {dict(r)}" for r in rows]
        return f"Here are the results ({count} row(s)):\n" + "\n".join(lines)

    return f"Found **{count}** results. {generated.explanation}"


def _combine_clarification(original_question: str, clarification_answer: str) -> str:
    return (
        "Original question: "
        f"{original_question}\n"
        "Clarification answer: "
        f"{clarification_answer}\n"
        "Answer the original question using the clarification."
    )


def _is_retriable_schema_error(exc: Exception) -> bool:
    error_name = exc.__class__.__name__.lower()
    message = str(exc).lower()
    schema_error_markers = (
        "undefinedcolumn",
        "undefinedtable",
        "ambiguouscolumn",
        "ambiguousalias",
        "undefined function",
        "column",
        "relation",
        "does not exist",
    )
    return any(marker in error_name or marker in message for marker in schema_error_markers)


def _build_repair_prompt(question: str, failed_sql: str, exc: Exception) -> str:
    return (
        f"Original user question:\n{question}\n\n"
        f"The previous SQL failed:\n{failed_sql}\n\n"
        f"Database error:\n{exc}\n\n"
        "Correct the SQL using only tables and columns that exist in the schema tool. "
        "If the question cannot be answered with the available schema, set requires_clarification to true."
    )


def _build_chart(question: str, rows: list[dict]) -> ChartSpec | None:
    if len(rows) < 2:
        return None

    keys = list(rows[0].keys())
    if len(keys) < 2:
        return None

    x_key = keys[0]
    y_key = next((key for key in keys[1:] if all(_is_number(row.get(key)) for row in rows)), None)
    if y_key is None:
        return None

    lowered = question.lower()
    chart_type = ChartType.line if any(token in lowered for token in ["trend", "month", "year", "over time"]) else ChartType.bar
    title = "Trend" if chart_type == ChartType.line else "Comparison"
    return ChartSpec(
        chart_type=chart_type,
        title=title,
        data=rows,
        x_key=x_key,
        y_key=y_key,
    )


def _is_number(value: object) -> bool:
    return isinstance(value, Number) and not isinstance(value, bool)


def _elapsed_ms(started_at: float | None) -> int | None:
    if started_at is None:
        return None
    return round((time.perf_counter() - started_at) * 1000)
