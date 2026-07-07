from fastapi import APIRouter, Depends
import uuid

from app.core.logging import get_logger
from app.schemas.ask import AskRequest, AnswerResponse, ClarifyingQuestionResponse, ChartSpecResponse, SqlQueryResponse
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
    if body.session_id:
        session_schema = f"session_{body.session_id.replace('-', '_')}"

    result = await service.answer(
        question=body.question,
        conversation_id=body.conversation_id,
        clarification_answer=body.clarification_answer,
        request_id=request_id,
        session_schema=session_schema,
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

    logger.info(
        "Returning answer response",
        extra={
            "request_id": request_id,
            "conversation_id": result.conversation_id,
            "has_sql": result.sql is not None,
            "has_chart": result.chart is not None,
        },
    )
    return AnswerResponse(
        answer=result.text,
        chart=chart_response,
        sql=sql_response,
        conversation_id=result.conversation_id,
    )
