import asyncio
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.core.logging import get_logger
from app.schemas.ask import (
    AskRequest,
    AnswerResponse,
    AnswerSpecResponse,
    ClaimResponse,
    ClarifyingQuestionResponse,
    ClarifyResponseResponse,
    ConfirmFirstResponse,
    ConfirmRequest,
    ProxyAlternativeResponse,
    ChartSpecResponse,
    HeadlineResponse,
    SqlQueryResponse,
    AssumptionResponse,
    PlanResultResponse,
    DependencyResponse,
    FingerprintResponse,
    ValidationResultResponse,
)
from app.core.config import settings
from app.api.deps import get_chat_history_service
from app.domain.exceptions import ChatSessionNotFoundError
from app.services.ask_service import AskService
from app.services.chat_history_service import ChatHistoryService
from app.domain.models import Answer, ClarifyingQuestion, ClarifyResponse, ConfirmFirst
from app.repositories.base import SchemaRepository
from app.repositories.combined_schema_repository import CombinedSchemaRepository

router = APIRouter()
logger = get_logger("api.ask")

# Overall wall-clock budget for a single /ask request (streaming or not).
# Local CPU-bound model backends (e.g. Ollama) can take well over a minute for the
# multi-agent pipeline (planner -> SQL gen -> validator -> aggregator), each a
# separate structured-output round trip - 60s clips those runs mid-flight.
ASK_TIMEOUT_SECONDS = 600.0
# Poll interval while waiting for pipeline step events / client disconnect checks.
SSE_POLL_INTERVAL_SECONDS = 0.1
# Idle SSE comment sent when no real step has fired in a while, so nginx's
# proxy_read_timeout (300s) never sees a silent gap during a long single LLM call
# (CPU-bound Ollama round trips can run well past that with zero intermediate output).
SSE_HEARTBEAT_INTERVAL_SECONDS = 15.0

_TIMEOUT_MESSAGE = (
    "Sorry, that request took too long to answer. Please try again or check that "
    "your model provider is responding."
)


async def get_ask_service() -> AskService:
    from app.main import app_state

    return app_state.ask_service


def _resolve_session(
    session_id: str | None,
) -> tuple[str | None, str, SchemaRepository | None]:
    if not session_id:
        return None, "", None
    session_schema = f"session_{session_id.replace('-', '_')}"
    from app.main import app_state

    context_note = ""
    schema_repo_override: SchemaRepository | None = None
    if app_state is not None:
        context_note = app_state.session_manager.get_session_note(session_id)
        join_key = app_state.session_manager.get_join_key(session_id)
        if join_key is not None:
            schema_repo_override = CombinedSchemaRepository(
                primary=app_state.session_manager.get_schema_repo(session_id),
                secondary=app_state.schema_repository,
                secondary_prefix=settings.db_schema,
            )
    return session_schema, context_note, schema_repo_override


def _sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/ask")
async def ask(
    body: AskRequest,
    service: AskService = Depends(get_ask_service),
    chat_history_service: ChatHistoryService = Depends(get_chat_history_service),
) -> (
    AnswerResponse
    | ClarifyingQuestionResponse
    | ClarifyResponseResponse
    | ConfirmFirstResponse
):
    request_id = str(uuid.uuid4())
    logger.info(
        "Received /ask request",
        extra={
            "request_id": request_id,
            "conversation_id": body.conversation_id,
            "has_clarification_answer": body.clarification_answer is not None,
            "question_length": len(body.question),
            "question": body.question,
        },
    )
    session_schema, context_note, schema_repo_override = _resolve_session(
        body.session_id
    )

    prior_brief = ""
    if body.chat_session_id:
        history = await chat_history_service.get_history(body.chat_session_id)
        if history:
            _, turns = history
            if turns:
                last_spec = turns[-1].answer_json.get("answer_spec") or {}
                prior_brief = last_spec.get("session_brief", "") or ""

    timed_out = False
    try:
        result = await asyncio.wait_for(
            service.answer(
                question=body.question,
                conversation_id=body.conversation_id,
                clarification_answer=body.clarification_answer,
                request_id=request_id,
                session_schema=session_schema,
                context_note=context_note,
                schema_repo_override=schema_repo_override,
                session_brief=prior_brief,
            ),
            timeout=ASK_TIMEOUT_SECONDS,
        )
    except (TimeoutError, asyncio.CancelledError):
        logger.warning("Ask request timed out", extra={"request_id": request_id})
        result = Answer(text=_TIMEOUT_MESSAGE, conversation_id=body.conversation_id)
        timed_out = True

    response = _build_response(result, request_id)

    if body.chat_session_id and isinstance(result, Answer) and not timed_out:
        try:
            await chat_history_service.record_turn(
                body.chat_session_id,
                body.question,
                response.model_dump(mode="json"),  # type: ignore[union-attr]
            )
        except ChatSessionNotFoundError:
            logger.warning(
                "chat_session_id not found, skipping persistence",
                extra={"chat_session_id": body.chat_session_id},
            )

    return response


@router.post("/ask/confirm")
async def ask_confirm(
    body: ConfirmRequest,
    service: AskService = Depends(get_ask_service),
    chat_history_service: ChatHistoryService = Depends(get_chat_history_service),
) -> (
    AnswerResponse
    | ClarifyingQuestionResponse
    | ClarifyResponseResponse
    | ConfirmFirstResponse
):
    """Execute a previously gated query using the user's confirmed (or amended) assumptions."""
    request_id = str(uuid.uuid4())
    logger.info(
        "Received /ask/confirm request",
        extra={
            "request_id": request_id,
            "conversation_id": body.conversation_id,
            "amendment_count": len(body.amendments),
        },
    )

    prior_brief = ""
    if body.chat_session_id:
        history = await chat_history_service.get_history(body.chat_session_id)
        if history:
            _, turns = history
            if turns:
                last_spec = turns[-1].answer_json.get("answer_spec") or {}
                prior_brief = last_spec.get("session_brief", "") or ""

    # Peek at the original question before answer_confirmed consumes the confirm state.
    original_question = service.get_confirm_question(body.conversation_id) or ""

    amendments = [(a.term, a.resolution) for a in body.amendments]
    timed_out = False
    try:
        result = await asyncio.wait_for(
            service.answer_confirmed(
                confirm_id=body.conversation_id,
                amendments=amendments,
                request_id=request_id,
                prior_brief=prior_brief,
            ),
            timeout=ASK_TIMEOUT_SECONDS,
        )
    except (TimeoutError, asyncio.CancelledError):
        logger.warning("Confirm request timed out", extra={"request_id": request_id})
        result = Answer(text=_TIMEOUT_MESSAGE, conversation_id=body.conversation_id)
        timed_out = True

    response = _build_response(result, request_id)

    if body.chat_session_id and isinstance(result, Answer) and not timed_out:
        try:
            await chat_history_service.record_turn(
                body.chat_session_id,
                original_question,
                response.model_dump(mode="json"),  # type: ignore[union-attr]
            )
        except ChatSessionNotFoundError:
            logger.warning(
                "chat_session_id not found, skipping persistence (confirm)",
                extra={"chat_session_id": body.chat_session_id},
            )

    return response


@router.get("/ask/stream")
async def ask_stream(
    request: Request,
    question: str,
    conversation_id: str | None = None,
    clarification_answer: str | None = None,
    session_id: str | None = None,
    chat_session_id: str | None = None,
    service: AskService = Depends(get_ask_service),
    chat_history_service: ChatHistoryService = Depends(get_chat_history_service),
) -> StreamingResponse:
    """SSE variant of /ask. Emits `event: step` per completed pipeline stage with
    real Planner/Validator/Aggregator data, then a final `event: done` carrying the
    same JSON shape as the non-streaming endpoint. AskService itself knows nothing
    about SSE — this route owns all transport framing via the `on_step` callback.
    """
    request_id = str(uuid.uuid4())
    logger.info(
        "Received /ask/stream request",
        extra={
            "request_id": request_id,
            "conversation_id": conversation_id,
            "question": question,
        },
    )
    session_schema, context_note, schema_repo_override = _resolve_session(session_id)

    prior_brief = ""
    if chat_session_id:
        history = await chat_history_service.get_history(chat_session_id)
        if history:
            _, turns = history
            if turns:
                last_spec = turns[-1].answer_json.get("answer_spec") or {}
                prior_brief = last_spec.get("session_brief", "") or ""

    queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()

    async def on_step(stage: str, detail: dict[str, Any]) -> None:
        await queue.put((stage, detail))

    async def run_pipeline() -> (
        Answer | ClarifyingQuestion | ClarifyResponse | ConfirmFirst
    ):
        return await service.answer(
            question=question,
            conversation_id=conversation_id,
            clarification_answer=clarification_answer,
            request_id=request_id,
            session_schema=session_schema,
            context_note=context_note,
            on_step=on_step,
            schema_repo_override=schema_repo_override,
            session_brief=prior_brief,
        )

    async def event_generator():
        task = asyncio.ensure_future(run_pipeline())
        started_at = asyncio.get_running_loop().time()
        last_sent_at = started_at
        try:
            while not task.done():
                if await request.is_disconnected():
                    task.cancel()
                    return

                now = asyncio.get_running_loop().time()
                if now - started_at > ASK_TIMEOUT_SECONDS:
                    task.cancel()
                    yield _sse_event("error", {"message": "Request timed out"})
                    return

                try:
                    stage, detail = await asyncio.wait_for(
                        queue.get(), timeout=SSE_POLL_INTERVAL_SECONDS
                    )
                    yield _sse_event("step", {"stage": stage, "detail": detail})
                    last_sent_at = asyncio.get_running_loop().time()
                except asyncio.TimeoutError:
                    now = asyncio.get_running_loop().time()
                    if now - last_sent_at > SSE_HEARTBEAT_INTERVAL_SECONDS:
                        yield ": keep-alive\n\n"
                        last_sent_at = now
                    continue

            while not queue.empty():
                stage, detail = queue.get_nowait()
                yield _sse_event("step", {"stage": stage, "detail": detail})

            result = await task
            response = _build_response(result, request_id)
            if chat_session_id and isinstance(result, Answer):
                try:
                    await chat_history_service.record_turn(
                        chat_session_id,
                        question,
                        response.model_dump(mode="json"),  # type: ignore[union-attr]
                    )
                except ChatSessionNotFoundError:
                    logger.warning(
                        "chat_session_id not found, skipping persistence (stream)",
                        extra={"chat_session_id": chat_session_id},
                    )
            yield _sse_event("done", response.model_dump(mode="json"))
        except asyncio.CancelledError:
            raise
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _build_response(
    result: Answer | ClarifyingQuestion | ClarifyResponse | ConfirmFirst,
    request_id: str,
) -> (
    AnswerResponse
    | ClarifyingQuestionResponse
    | ClarifyResponseResponse
    | ConfirmFirstResponse
):
    if isinstance(result, ClarifyResponse):
        return ClarifyResponseResponse(
            statement=result.statement,
            unresolved_terms=result.unresolved_terms,
            alternatives=[
                ProxyAlternativeResponse(label=a.label, question=a.question)
                for a in result.alternatives
            ],
            add_data=result.add_data,
            conversation_id=result.conversation_id,
        )
    if isinstance(result, ClarifyingQuestion):
        logger.info(
            "Returning clarification response",
            extra={
                "request_id": request_id,
                "conversation_id": result.conversation_id,
                "options_count": len(result.options),
            },
        )
        return ClarifyingQuestionResponse(
            question=result.question,
            options=result.options,
            conversation_id=result.conversation_id or "",
        )
    if isinstance(result, ConfirmFirst):
        logger.info(
            "Returning confirm_first gate response",
            extra={
                "request_id": request_id,
                "conversation_id": result.conversation_id,
                "gate_reason": result.gate_reason,
                "scan_cost": result.scan_cost,
            },
        )
        return _build_confirm_first_response(result)
    return _build_answer_response(result, request_id)


def _build_confirm_first_response(result: ConfirmFirst) -> ConfirmFirstResponse:
    plan = result.plan
    return ConfirmFirstResponse(
        conversation_id=result.conversation_id,
        plan=PlanResultResponse(
            ambiguity_score=plan.ambiguity_score,
            assumptions=[
                AssumptionResponse(
                    term=a.term,
                    resolution=a.resolution,
                    alternatives=a.alternatives,
                    close_call=a.close_call,
                )
                for a in plan.assumptions
            ],
            unresolved_terms=plan.unresolved_terms,
            interpretation=plan.interpretation,
        ),
        scan_cost=result.scan_cost,
        gate_reason=result.gate_reason,
    )


def _build_answer_response(result: Answer, request_id: str) -> AnswerResponse:
    chart_response: ChartSpecResponse | None = None
    if result.chart is not None:
        chart_response = ChartSpecResponse(
            chart_type=result.chart.chart_type.value,
            title=result.chart.title,
            data=result.chart.data,
            x_key=result.chart.x_key,
            y_key=result.chart.y_key,
        )

    sql_response: SqlQueryResponse | None = None
    if result.sql is not None:
        sql_response = SqlQueryResponse(
            sql=result.sql.sql,
            explanation=result.sql.explanation,
        )

    plan_response: PlanResultResponse | None = None
    if result.plan is not None:
        plan_response = PlanResultResponse(
            ambiguity_score=result.plan.ambiguity_score,
            assumptions=[
                AssumptionResponse(
                    term=a.term,
                    resolution=a.resolution,
                    alternatives=a.alternatives,
                    close_call=a.close_call,
                )
                for a in result.plan.assumptions
            ],
            unresolved_terms=result.plan.unresolved_terms,
            interpretation=result.plan.interpretation,
        )

    validation_response: ValidationResultResponse | None = None
    if result.validation is not None:
        v = result.validation
        validation_response = ValidationResultResponse(
            dependency_set=[
                DependencyResponse(table=d.table, column=d.column)
                for d in v.dependency_set
            ],
            fingerprints=[
                FingerprintResponse(
                    table=f.table,
                    column=f.column,
                    schema_hash=f.schema_hash,
                    value_hash=f.value_hash,
                )
                for f in v.fingerprints
            ],
            scan_cost=v.scan_cost,
        )

    answer_spec_response: AnswerSpecResponse | None = None
    if result.answer_spec is not None:
        spec = result.answer_spec
        answer_spec_response = AnswerSpecResponse(
            response_type=spec.response_type,
            headline=HeadlineResponse(
                value=spec.headline.value,
                label=spec.headline.label,
                sign=spec.headline.sign,
            ),
            restatement=spec.restatement,
            chart_spec=ChartSpecResponse(
                chart_type=spec.chart_spec.chart_type,
                title=spec.chart_spec.title,
                data=spec.chart_spec.data,
                x_key=spec.chart_spec.x_key,
                y_key=spec.chart_spec.y_key,
                emphasis_target=spec.chart_spec.emphasis_target,
                y_keys=spec.chart_spec.y_keys,
            )
            if spec.chart_spec
            else None,
            suppression_reason=spec.suppression_reason,
            claims=[
                ClaimResponse(
                    sentence=c.sentence,
                    type=c.type,
                    cells=c.cells,
                    operation=c.operation,
                    operands=c.operands,
                    value=c.value,
                )
                for c in spec.claims
            ],
            followups=spec.followups,
            assumptions_ref=[
                AssumptionResponse(
                    term=a.term,
                    resolution=a.resolution,
                    alternatives=a.alternatives,
                    close_call=a.close_call,
                )
                for a in spec.assumptions_ref
            ],
            dropped_claim_count=spec.dropped_claim_count,
            session_brief=spec.session_brief,
        )

    logger.info(
        "Returning answer response",
        extra={
            "request_id": request_id,
            "conversation_id": result.conversation_id,
            "has_sql": result.sql is not None,
            "has_chart": result.chart is not None,
            "has_answer_spec": result.answer_spec is not None,
            "ambiguity_score": result.plan.ambiguity_score if result.plan else None,
        },
    )
    return AnswerResponse(
        answer=result.text,
        chart=chart_response,
        sql=sql_response,
        conversation_id=result.conversation_id,
        plan=plan_response,
        validation=validation_response,
        answer_spec=answer_spec_response,
        dropped_claim_count=result.answer_spec.dropped_claim_count
        if result.answer_spec
        else 0,
        result_rows=result.result_rows,
        verifier_name=result.verifier_name,
        badge_state=result.badge_state,
        query_id=result.query_id,
    )
