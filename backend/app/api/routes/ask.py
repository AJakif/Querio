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
    ChartSpecResponse,
    HeadlineResponse,
    SqlQueryResponse,
    AssumptionResponse,
    PlanResultResponse,
    DependencyResponse,
    FingerprintResponse,
    ValidationResultResponse,
)
from app.services.ask_service import AskService
from app.domain.models import Answer, ClarifyingQuestion

router = APIRouter()
logger = get_logger("api.ask")

# Overall wall-clock budget for a single /ask request (streaming or not).
ASK_TIMEOUT_SECONDS = 60.0
# Poll interval while waiting for pipeline step events / client disconnect checks.
SSE_POLL_INTERVAL_SECONDS = 0.1


async def get_ask_service() -> AskService:
    from app.main import app_state
    return app_state.ask_service


def _resolve_session(session_id: str | None) -> tuple[str | None, str]:
    if not session_id:
        return None, ""
    session_schema = f"session_{session_id.replace('-', '_')}"
    from app.main import app_state
    context_note = ""
    if app_state is not None:
        context_note = app_state.session_manager.get_session_note(session_id)
    return session_schema, context_note


def _sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/ask")
async def ask(
    body: AskRequest,
    service: AskService = Depends(get_ask_service),
) -> AnswerResponse | ClarifyingQuestionResponse:
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
    session_schema, context_note = _resolve_session(body.session_id)

    result = await asyncio.wait_for(
        service.answer(
            question=body.question,
            conversation_id=body.conversation_id,
            clarification_answer=body.clarification_answer,
            request_id=request_id,
            session_schema=session_schema,
            context_note=context_note,
        ),
        timeout=ASK_TIMEOUT_SECONDS,
    )

    return _build_response(result, request_id)


@router.get("/ask/stream")
async def ask_stream(
    request: Request,
    question: str,
    conversation_id: str | None = None,
    clarification_answer: str | None = None,
    session_id: str | None = None,
    service: AskService = Depends(get_ask_service),
) -> StreamingResponse:
    """SSE variant of /ask. Emits `event: step` per completed pipeline stage with
    real Planner/Validator/Aggregator data, then a final `event: done` carrying the
    same JSON shape as the non-streaming endpoint. AskService itself knows nothing
    about SSE — this route owns all transport framing via the `on_step` callback.
    """
    request_id = str(uuid.uuid4())
    logger.info(
        "Received /ask/stream request",
        extra={"request_id": request_id, "conversation_id": conversation_id, "question": question},
    )
    session_schema, context_note = _resolve_session(session_id)

    queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()

    async def on_step(stage: str, detail: dict[str, Any]) -> None:
        await queue.put((stage, detail))

    async def run_pipeline() -> Answer | ClarifyingQuestion:
        return await service.answer(
            question=question,
            conversation_id=conversation_id,
            clarification_answer=clarification_answer,
            request_id=request_id,
            session_schema=session_schema,
            context_note=context_note,
            on_step=on_step,
        )

    async def event_generator():
        task = asyncio.ensure_future(run_pipeline())
        try:
            while not task.done():
                if await request.is_disconnected():
                    task.cancel()
                    return
                try:
                    stage, detail = await asyncio.wait_for(queue.get(), timeout=SSE_POLL_INTERVAL_SECONDS)
                    yield _sse_event("step", {"stage": stage, "detail": detail})
                except asyncio.TimeoutError:
                    continue

            while not queue.empty():
                stage, detail = queue.get_nowait()
                yield _sse_event("step", {"stage": stage, "detail": detail})

            try:
                result = await asyncio.wait_for(task, timeout=ASK_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                yield _sse_event("error", {"message": "Request timed out"})
                return

            if isinstance(result, ClarifyingQuestion):
                payload = _build_clarifying_payload(result, request_id)
            else:
                payload = _build_answer_payload(result, request_id)
            yield _sse_event("done", payload)
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


def _build_response(result: Answer | ClarifyingQuestion, request_id: str) -> AnswerResponse | ClarifyingQuestionResponse:
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
    return _build_answer_response(result, request_id)


def _build_clarifying_payload(result: ClarifyingQuestion, request_id: str) -> dict[str, Any]:
    return _build_response(result, request_id).model_dump()


def _build_answer_payload(result: Answer, request_id: str) -> dict[str, Any]:
    return _build_answer_response(result, request_id).model_dump()


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
            ) if spec.chart_spec else None,
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
        dropped_claim_count=result.answer_spec.dropped_claim_count if result.answer_spec else 0,
    )
