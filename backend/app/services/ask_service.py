import time
import uuid
from numbers import Number
from typing import Any, Awaitable, Callable

from app.agent.aggregator import Aggregator, FakeAggregator
from app.agent.contracts import PlanResult
from app.agent.planner import FakePlanner, Planner
from app.agent.validator import Validator
from app.domain.models import Answer, SqlQuery, ClarifyingQuestion, ChartSpec, ChartType, ValidationResult
from app.repositories.base import SchemaRepository, QueryRepository
from app.agent.agent import SqlGenerator, GeneratedSQL
from app.guardrails.sql_validator import validate_sql
from app.services.conversation_store import ConversationStore
from app.core.config import settings
from app.core.logging import get_logger


logger = get_logger("ask_service")

# Invoked after each pipeline stage completes with (stage_name, detail). Purely an
# observation hook for the transport layer (e.g. SSE progress streaming) — AskService
# stays transport-agnostic and never imports anything HTTP/SSE related.
OnStep = Callable[[str, dict[str, Any]], Awaitable[None]]


async def _emit(on_step: "OnStep | None", stage: str, detail: dict[str, Any]) -> None:
    if on_step is not None:
        await on_step(stage, detail)


class AskService:
    def __init__(
        self,
        sql_generator: SqlGenerator,
        schema_repository: SchemaRepository,
        query_repository: QueryRepository,
        conversation_store: ConversationStore | None = None,
        planner: Planner | None = None,
        validator: Validator | None = None,
        aggregator: Aggregator | None = None,
    ):
        self._sql_generator = sql_generator
        self._schema_repo = schema_repository
        self._query_repo = query_repository
        self._conversation_store = conversation_store or ConversationStore()
        self._planner = planner or FakePlanner()
        self._validator = validator or Validator()
        self._aggregator = aggregator or FakeAggregator()

    @property
    def schema_repository(self) -> SchemaRepository:
        return self._schema_repo

    @property
    def query_repository(self) -> QueryRepository:
        return self._query_repo

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
        context_note: str = "",
        on_step: "OnStep | None" = None,
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
                "has_context_note": bool(context_note),
            },
        )

        if context_note:
            question = f"[Dataset context: {context_note}]\n\n{question}"

        plan_result = await self._planner.plan(question, schema_repo_override=schema_repo)
        logger.debug(
            "Planner completed",
            extra={
                "request_id": request_id,
                "ambiguity_score": plan_result.ambiguity_score,
                "unresolved_count": len(plan_result.unresolved_terms),
            },
        )
        await _emit(
            on_step,
            "planner",
            {
                "ambiguity_score": plan_result.ambiguity_score,
                "assumptions": [a.model_dump() for a in plan_result.assumptions],
                "unresolved_terms": plan_result.unresolved_terms,
                "interpretation": plan_result.interpretation,
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
            return await self._execute_answer(combined_question, conversation_id, request_id, started_at, plan_result=plan_result, schema_repo=schema_repo, query_repo=query_repo, on_step=on_step)

        generated = await self._sql_generator.generate(question, schema_repo_override=schema_repo)

        if not generated.requires_clarification:
            await _emit(on_step, "sql_generator", {"sql": generated.sql, "explanation": generated.explanation})

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

        return await self._do_execute(generated, question, conversation_id, request_id, started_at, plan_result=plan_result, query_repo=query_repo, schema_repo=schema_repo, on_step=on_step)

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
        plan_result: PlanResult | None = None,
        on_step: "OnStep | None" = None,
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
            return Answer(text=error, conversation_id=conversation_id, plan=plan_result)

        effective_sql = safe_sql or generated.sql
        validation_result: ValidationResult | None = None
        try:
            validation_result = await self._validator.validate(
                effective_sql, effective_schema_repo, effective_query_repo
            )
        except Exception as exc:
            logger.warning("Validator failed, continuing without validation", extra={"error": str(exc)})

        await _emit(
            on_step,
            "validator",
            {
                "scan_cost": validation_result.scan_cost if validation_result else 0,
                "dependency_count": len(validation_result.dependency_set) if validation_result else 0,
                "fingerprint_count": len(validation_result.fingerprints) if validation_result else 0,
            },
        )

        logger.debug("Executing SQL", extra={"request_id": request_id, "conversation_id": conversation_id, "sql": safe_sql})
        try:
            rows = await effective_query_repo.execute(effective_sql)
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
                    plan_result=plan_result,
                    on_step=on_step,
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
                plan=plan_result,
                validation=validation_result,
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
                plan=plan_result,
                validation=validation_result,
            )

        answer_spec = None
        try:
            answer_spec = await self._aggregator.aggregate(
                question, rows, plan_result or PlanResult()
            )
        except Exception as exc:
            logger.warning("Aggregator failed, continuing without answer_spec", extra={"error": str(exc)})

        await _emit(
            on_step,
            "aggregator",
            {
                "headline": answer_spec.headline.value if answer_spec is not None else None,
                "claims_count": len(answer_spec.claims) if answer_spec is not None else 0,
            },
        )

        if answer_spec is not None:
            try:
                answer_spec, _dropped = self._validator.verify_claims(answer_spec, rows)
            except Exception as exc:
                logger.warning(
                    "Claim verification failed, continuing with unverified claims",
                    extra={"error": str(exc)},
                )

        # Derive legacy text from AnswerSpec for frontend compat; fall back to old formatter
        answer_text = (
            answer_spec.restatement if answer_spec is not None else _format_answer(rows, generated)
        )
        chart = _build_chart(question, rows)
        return Answer(
            text=answer_text,
            chart=chart,
            sql=SqlQuery(sql=generated.sql, explanation=generated.explanation),
            conversation_id=conversation_id,
            plan=plan_result,
            validation=validation_result,
            answer_spec=answer_spec,
        )

    async def _execute_answer(
        self,
        question: str,
        conversation_id: str,
        request_id: str | None = None,
        started_at: float | None = None,
        plan_result: PlanResult | None = None,
        schema_repo: SchemaRepository | None = None,
        query_repo: QueryRepository | None = None,
        on_step: "OnStep | None" = None,
    ) -> Answer | ClarifyingQuestion:
        generated = await self._sql_generator.generate(question, schema_repo_override=schema_repo)
        if not generated.requires_clarification:
            await _emit(on_step, "sql_generator", {"sql": generated.sql, "explanation": generated.explanation})
        return await self._do_execute(generated, question, conversation_id, request_id, started_at, plan_result=plan_result, query_repo=query_repo, schema_repo=schema_repo, on_step=on_step)


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
