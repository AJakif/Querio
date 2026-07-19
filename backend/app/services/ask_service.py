import time
import uuid
from numbers import Number
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from app.agent.aggregator import Aggregator, FakeAggregator
from app.agent.contracts import PlanResult, Assumption
from app.agent.planner import FakePlanner, Planner
from app.agent.validator import Validator
from app.domain.models import Answer, BadgeState, SqlQuery, ClarifyingQuestion, ClarifyResponse, ConfirmFirst, ProxyAlternative, ChartSpec, ChartType, ValidationResult
from app.repositories.base import SchemaRepository, QueryRepository
from app.agent.agent import SqlGenerator, GeneratedSQL
from app.guardrails.sql_validator import validate_sql
from app.services.conversation_store import ConversationStore
from app.services.confirm_store import ConfirmStore, ConfirmPendingState
from app.core.config import settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.services.verification_service import VerificationService


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
        query_record_service: "VerificationService | None" = None,
    ):
        self._sql_generator = sql_generator
        self._schema_repo = schema_repository
        self._query_repo = query_repository
        self._conversation_store = conversation_store or ConversationStore()
        self._confirm_store = ConfirmStore()
        self._planner = planner or FakePlanner()
        self._validator = validator or Validator()
        self._aggregator = aggregator or FakeAggregator()
        self._query_record_service = query_record_service

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
        schema_repo_override: SchemaRepository | None = None,
    ) -> Answer | ClarifyingQuestion | ClarifyResponse | ConfirmFirst:
        request_id = request_id or str(uuid.uuid4())
        started_at = time.perf_counter()
        if schema_repo_override is not None:
            schema_repo: SchemaRepository | None = schema_repo_override
        else:
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

        # Verified-query cache check — before any LLM call.
        # Only applies to the default (non-session, non-clarification) path.
        if not session_schema and not (conversation_id and clarification_answer is not None):
            cache_answer = await self._try_verified_cache(
                question, conversation_id, request_id, started_at, on_step
            )
            if cache_answer is not None:
                return cache_answer

        if context_note:
            question = f"[Dataset context: {context_note}]\n\n{question}"

        try:
            plan_result = await self._planner.plan(question, schema_repo_override=schema_repo)
        except Exception as exc:
            logger.warning(
                "Planner failed — provider unreachable or invalid output",
                extra={"request_id": request_id, "error": str(exc), "error_type": exc.__class__.__name__},
            )
            return Answer(
                text="Sorry, the AI model is currently unavailable. Please check that your model provider is running and try again.",
                conversation_id=conversation_id,
            )
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

        # ROUTE-3: unresolved terms mean the question asks about data absent from the
        # schema. Route to a ClarifyResponse with schema-grounded proxy alternatives
        # instead of forwarding to the SQL generator, which would guess or fail.
        if plan_result.unresolved_terms and not clarification_answer:
            effective_schema = schema_repo_override or self._schema_repo
            clarify = await _build_clarify_response(
                plan_result.unresolved_terms, effective_schema
            )
            logger.info(
                "Routing to clarify response (unresolved terms)",
                extra={
                    "request_id": request_id,
                    "unresolved_terms": plan_result.unresolved_terms,
                    "alternatives_count": len(clarify.alternatives),
                },
            )
            await _emit(on_step, "clarify", {"unresolved_terms": plan_result.unresolved_terms})
            return clarify

        # Ambiguity gate: return confirm_first before running any SQL
        if plan_result.ambiguity_score > settings.ambiguity_threshold:
            confirm_id = self._confirm_store.create(
                ConfirmPendingState(
                    original_question=question,
                    plan_result=plan_result,
                    schema_repo=schema_repo or self._schema_repo,
                    query_repo=query_repo or self._query_repo,
                    gate_reason="ambiguity",
                )
            )
            logger.info(
                "Ambiguity threshold exceeded — returning confirm_first gate",
                extra={
                    "request_id": request_id,
                    "ambiguity_score": plan_result.ambiguity_score,
                    "threshold": settings.ambiguity_threshold,
                    "confirm_id": confirm_id,
                },
            )
            await _emit(on_step, "confirm_gate", {"gate_reason": "ambiguity", "confirm_id": confirm_id})
            return ConfirmFirst(
                plan=plan_result,
                scan_cost=0,
                conversation_id=confirm_id,
                gate_reason="ambiguity",
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

        try:
            generated = await self._sql_generator.generate(question, schema_repo_override=schema_repo)
        except Exception as exc:
            logger.warning(
                "SQL generator failed — provider unreachable",
                extra={"request_id": request_id, "error": str(exc), "error_type": exc.__class__.__name__},
            )
            return Answer(
                text="Sorry, the AI model is currently unavailable. Please check that your model provider is running and try again.",
                conversation_id=conversation_id,
            )

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

    async def _try_verified_cache(
        self,
        question: str,
        conversation_id: str | None,
        request_id: str | None,
        started_at: float | None,
        on_step: "OnStep | None",
    ) -> Answer | None:
        """Return a fresh-data Answer from the verified-query store on a cache hit, or None.

        Cache hit requires the matched record's badge state to be clean Verified — computed
        live, never from a cached/stale field. Any other state (Needs recheck, Disputed,
        Unverified) returns None so the caller falls through to the full LLM pipeline.
        """
        if self._query_record_service is None:
            return None

        from app.services.verification_service import _normalize_question

        normalized = _normalize_question(question)
        record = await self._query_record_service.find_verified_by_question(normalized)
        if record is None:
            return None

        # Cache hit on a clean Verified record — re-execute stored SQL against live DB.
        logger.info(
            "Verified cache hit — skipping LLM pipeline",
            extra={"request_id": request_id, "query_id": record.id},
        )
        await _emit(on_step, "cache_hit", {"query_id": record.id, "sql": record.sql})

        # Guardrail: stored SQL must still pass validation before execution.
        # Drift or tampering could leave a formerly-valid query in a now-invalid state.
        _safe_sql, _sql_error = validate_sql(record.sql, max_rows=settings.max_result_rows)
        if _sql_error:
            logger.warning(
                "Verified cache SQL failed guardrail; falling through to full pipeline",
                extra={"request_id": request_id, "query_id": record.id, "guardrail_error": _sql_error},
            )
            return None

        try:
            rows = await self._query_repo.execute(_safe_sql or record.sql)
        except Exception as exc:
            logger.warning(
                "Verified cache SQL execution failed; falling through to full pipeline",
                extra={"request_id": request_id, "query_id": record.id, "error": str(exc)},
            )
            return None

        dummy = GeneratedSQL(sql=record.sql, explanation="Verified cached query")
        text = _format_answer(rows, dummy) if rows else "The query returned no results."
        chart = _build_chart(question, rows)
        last_verify = record.last_verification()
        return Answer(
            text=text,
            chart=chart,
            sql=SqlQuery(sql=record.sql, explanation="Verified cached query"),
            conversation_id=conversation_id,
            result_rows=rows,
            verifier_name=last_verify.actor if last_verify else None,
            badge_state=record.badge_state().value,
            query_id=record.id,
        )

    _MAX_REPAIR_ATTEMPTS = 3

    async def _do_execute(
        self,
        generated: GeneratedSQL,
        question: str,
        conversation_id: str | None = None,
        request_id: str | None = None,
        started_at: float | None = None,
        repair_attempt: int = 0,
        query_repo: QueryRepository | None = None,
        schema_repo: SchemaRepository | None = None,
        plan_result: PlanResult | None = None,
        on_step: "OnStep | None" = None,
    ) -> Answer | ClarifyingQuestion | ConfirmFirst:
        effective_query_repo = query_repo or self._query_repo
        effective_schema_repo = schema_repo or self._schema_repo
        safe_sql, error = validate_sql(generated.sql, max_rows=settings.max_result_rows)
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

        # Cost gate: return confirm_first before executing an expensive query
        if validation_result and validation_result.scan_cost > settings.scan_cost_threshold:
            confirm_id = self._confirm_store.create(
                ConfirmPendingState(
                    original_question=question,
                    plan_result=plan_result or PlanResult(),
                    schema_repo=effective_schema_repo,
                    query_repo=effective_query_repo,
                    gate_reason="cost",
                )
            )
            logger.info(
                "Scan cost threshold exceeded — returning confirm_first gate",
                extra={
                    "request_id": request_id,
                    "scan_cost": validation_result.scan_cost,
                    "threshold": settings.scan_cost_threshold,
                    "confirm_id": confirm_id,
                },
            )
            await _emit(on_step, "confirm_gate", {"gate_reason": "cost", "confirm_id": confirm_id})
            return ConfirmFirst(
                plan=plan_result or PlanResult(),
                scan_cost=validation_result.scan_cost,
                conversation_id=confirm_id,
                gate_reason="cost",
            )

        logger.debug("Executing SQL", extra={"request_id": request_id, "conversation_id": conversation_id, "sql": safe_sql})
        try:
            rows = await effective_query_repo.execute(effective_sql)
        except Exception as exc:
            if repair_attempt < self._MAX_REPAIR_ATTEMPTS:
                logger.warning(
                    "SQL execution failed; requesting model correction (attempt %d/%d)",
                    repair_attempt + 1,
                    self._MAX_REPAIR_ATTEMPTS,
                    extra={
                        "request_id": request_id,
                        "conversation_id": conversation_id,
                        "generated_sql": generated.sql,
                        "error_type": exc.__class__.__name__,
                        "execution_time_ms": _elapsed_ms(started_at),
                        "repair_attempt": repair_attempt,
                    },
                )
                try:
                    repaired = await self._sql_generator.generate(
                        _build_repair_prompt(question, generated.sql, exc),
                        schema_repo_override=schema_repo,
                    )
                except Exception as repair_exc:
                    logger.warning(
                        "SQL generator failed during repair — provider unreachable",
                        extra={"request_id": request_id, "error": str(repair_exc), "error_type": repair_exc.__class__.__name__},
                    )
                    return Answer(
                        text="Sorry, the AI model is currently unavailable. Please check that your model provider is running and try again.",
                        conversation_id=conversation_id,
                        plan=plan_result,
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
                    repair_attempt=repair_attempt + 1,
                    query_repo=query_repo,
                    schema_repo=schema_repo,
                    plan_result=plan_result,
                    on_step=on_step,
                )

            logger.exception(
                "SQL execution failed after %d repair attempt(s); giving up",
                self._MAX_REPAIR_ATTEMPTS,
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
            from app.agent.contracts import AnswerSpec, Headline
            empty_spec = AnswerSpec(
                response_type="stat",
                headline=Headline(value="0", label="results", sign="neutral"),
                restatement="The query returned no results.",
                chart_spec=None,
                suppression_reason="empty result set",
                claims=[],
                followups=[],
                assumptions_ref=list(plan_result.assumptions) if plan_result else [],
                dropped_claim_count=0,
            )
            return Answer(
                text="The query returned no results.",
                sql=SqlQuery(sql=generated.sql, explanation=generated.explanation),
                conversation_id=conversation_id,
                plan=plan_result,
                validation=validation_result,
                answer_spec=empty_spec,
            )

        answer_spec = None
        try:
            answer_spec = await self._aggregator.aggregate(
                question, rows, plan_result or PlanResult()
            )
            # Normalize: response_type must be consistent with chart_spec presence.
            # Don't trust the LLM's response_type field blindly.
            if answer_spec is not None:
                correct_type = "chart" if answer_spec.chart_spec is not None else "stat"
                if answer_spec.response_type != correct_type:
                    answer_spec = answer_spec.model_copy(update={"response_type": correct_type})
        except Exception as exc:
            logger.warning("Aggregator failed, continuing without answer_spec", extra={"error": str(exc)})

        await _emit(
            on_step,
            "aggregator",
            {
                "headline": answer_spec.headline.value if answer_spec is not None else None,
                "claims_count": len(answer_spec.claims) if answer_spec is not None else 0,
                "suppression_reason": answer_spec.suppression_reason if answer_spec is not None else None,
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
            result_rows=rows,
        )

    async def _execute_answer(
        self,
        question: str,
        conversation_id: str | None,
        request_id: str | None = None,
        started_at: float | None = None,
        plan_result: PlanResult | None = None,
        schema_repo: SchemaRepository | None = None,
        query_repo: QueryRepository | None = None,
        on_step: "OnStep | None" = None,
    ) -> Answer | ClarifyingQuestion | ConfirmFirst:
        try:
            generated = await self._sql_generator.generate(question, schema_repo_override=schema_repo)
        except Exception as exc:
            logger.warning(
                "SQL generator failed — provider unreachable",
                extra={"request_id": request_id, "error": str(exc), "error_type": exc.__class__.__name__},
            )
            return Answer(
                text="Sorry, the AI model is currently unavailable. Please check that your model provider is running and try again.",
                conversation_id=conversation_id,
            )
        if not generated.requires_clarification:
            await _emit(on_step, "sql_generator", {"sql": generated.sql, "explanation": generated.explanation})
        return await self._do_execute(generated, question, conversation_id, request_id, started_at, plan_result=plan_result, query_repo=query_repo, schema_repo=schema_repo, on_step=on_step)

    async def answer_confirmed(
        self,
        confirm_id: str,
        amendments: list[tuple[str, str]],
        request_id: str | None = None,
        on_step: "OnStep | None" = None,
    ) -> Answer | ClarifyingQuestion | ConfirmFirst:
        """Execute a query whose gate was previously tripped, using the user's original
        or amended assumptions. ``amendments`` is a list of ``(term, new_resolution)``
        pairs; terms not listed keep their original resolution from the stored plan.
        """
        state = self._confirm_store.get(confirm_id)
        if state is None:
            logger.warning("Confirm state not found", extra={"confirm_id": confirm_id})
            return Answer(text="Confirmation session not found. Please ask your question again.")
        self._confirm_store.complete(confirm_id)

        amended_plan = _apply_amendments(state.plan_result, amendments)
        question = _build_confirmed_question(state.original_question, amended_plan)

        return await self._execute_answer(
            question=question,
            conversation_id=None,
            request_id=request_id or str(uuid.uuid4()),
            started_at=time.perf_counter(),
            plan_result=amended_plan,
            schema_repo=state.schema_repo,
            query_repo=state.query_repo,
            on_step=on_step,
        )


async def _build_clarify_response(
    unresolved_terms: list[str],
    schema_repo: SchemaRepository,
) -> ClarifyResponse:
    """Build a ClarifyResponse with schema-grounded proxy alternatives.

    Introspects the active schema to find numeric and categorical columns, then
    generates ≥2 ready-to-submit proxy questions grounded in real column names.
    Never uses placeholder text — all alternatives reference actual tables/columns.
    """
    tables = await schema_repo.get_tables()

    # Columns to skip — IDs and raw timestamps don't make good proxy metrics
    _ID_SUFFIXES = ("_id", "_key", "_hash", "_prefix")
    _SKIP_TYPES = {"timestamp without time zone", "timestamp with time zone", "date", "boolean"}

    numeric_cols: list[tuple[str, str]] = []  # (table, column)
    category_cols: list[tuple[str, str]] = []

    for table in tables:
        cols = await schema_repo.get_columns(table)
        for col in cols:
            name_lower = col.name.lower()
            if col.data_type in _SKIP_TYPES:
                continue
            if any(name_lower.endswith(sfx) for sfx in _ID_SUFFIXES):
                continue
            if col.data_type in ("numeric", "integer", "bigint", "real", "double precision"):
                numeric_cols.append((table, col.name))
            elif col.data_type in ("character varying", "text"):
                category_cols.append((table, col.name))

    alternatives: list[ProxyAlternative] = []

    # Proxy 1: time-series of a numeric metric (most common actionable question)
    if numeric_cols:
        tbl, col = numeric_cols[0]
        label = f"Total {col.replace('_', ' ')} per month"
        alternatives.append(ProxyAlternative(
            label=label,
            question=f"What is the total {col.replace('_', ' ')} per month?",
        ))

    # Proxy 2: numeric metric broken down by a category, or a second numeric metric
    if len(numeric_cols) > 1 and category_cols:
        tbl2, col2 = numeric_cols[1]
        _, cat_col = category_cols[0]
        alternatives.append(ProxyAlternative(
            label=f"Average {col2.replace('_', ' ')} by {cat_col.replace('_', ' ')}",
            question=f"What is the average {col2.replace('_', ' ')} by {cat_col.replace('_', ' ')}?",
        ))
    elif len(numeric_cols) > 1:
        tbl2, col2 = numeric_cols[1]
        alternatives.append(ProxyAlternative(
            label=f"Average {col2.replace('_', ' ')}",
            question=f"What is the average {col2.replace('_', ' ')}?",
        ))

    # Fallback: count-based proxy if fewer than 2 numeric columns exist
    if len(alternatives) < 2 and tables:
        count_table = tables[0]
        alternatives.append(ProxyAlternative(
            label=f"Total number of {count_table}",
            question=f"How many {count_table} are there in total?",
        ))

    terms_str = " and ".join(f'"{t}"' for t in unresolved_terms)
    table_str = ", ".join(tables)
    statement = (
        f"This dataset covers {table_str} — it tracks orders, payments, reviews, "
        f"products, sellers, and customers. "
        f"It doesn't include {terms_str}: that concept isn't present in any table or column. "
        f"You can upload your own data to bring that in, or try one of these questions "
        f"the dataset can answer:"
    )

    return ClarifyResponse(
        statement=statement,
        unresolved_terms=unresolved_terms,
        alternatives=alternatives,
        add_data=True,
    )


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


def _apply_amendments(plan: PlanResult, amendments: list[tuple[str, str]]) -> PlanResult:
    """Return a new PlanResult with amended resolutions merged in."""
    if not amendments:
        return plan
    amendment_map = {term: resolution for term, resolution in amendments}
    updated = [
        Assumption(
            term=a.term,
            resolution=amendment_map.get(a.term, a.resolution),
            alternatives=a.alternatives,
            close_call=a.close_call,
        )
        for a in plan.assumptions
    ]
    return PlanResult(
        ambiguity_score=plan.ambiguity_score,
        assumptions=updated,
        unresolved_terms=plan.unresolved_terms,
        interpretation=plan.interpretation,
    )


def _build_confirmed_question(original: str, plan: PlanResult) -> str:
    """Prepend confirmed assumption context to the question so the SQL generator
    uses the user-approved (possibly amended) resolutions rather than guessing.
    """
    if not plan.assumptions:
        return original
    context = "; ".join(f"{a.term}: {a.resolution}" for a in plan.assumptions)
    return f"{original}\n[Confirmed assumptions: {context}]"
