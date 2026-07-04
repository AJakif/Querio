from fastapi import APIRouter, Depends

from app.schemas.ask import AskRequest, AnswerResponse, ClarifyingQuestionResponse, ChartSpecResponse, SqlQueryResponse
from app.services.ask_service import AskService
from app.domain.models import Answer, ClarifyingQuestion

router = APIRouter()


async def get_ask_service() -> AskService:
    from app.main import app_state
    return app_state.ask_service


@router.post("/ask")
async def ask(
    body: AskRequest,
    service: AskService = Depends(get_ask_service),
) -> AnswerResponse | ClarifyingQuestionResponse:
    result = await service.answer(
        question=body.question,
        conversation_id=body.conversation_id,
        clarification_answer=body.clarification_answer,
    )

    if isinstance(result, ClarifyingQuestion):
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

    return AnswerResponse(
        answer=result.text,
        chart=chart_response,
        sql=sql_response,
        conversation_id=result.conversation_id,
    )
