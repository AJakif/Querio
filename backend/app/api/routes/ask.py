from fastapi import APIRouter, Depends
import uuid

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


async def get_ask_service() -> AskService:
    from app.main import app_state
    return app_state.ask_service


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
    session_schema = None
    context_note = ""
    if body.session_id:
        session_schema = f"session_{body.session_id.replace('-', '_')}"
        from app.main import app_state
        if app_state is not None:
            context_note = app_state.session_manager.get_session_note(body.session_id)

    result = await service.answer(
        question=body.question,
        conversation_id=body.conversation_id,
        clarification_answer=body.clarification_answer,
        request_id=request_id,
        session_schema=session_schema,
        context_note=context_note,
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
