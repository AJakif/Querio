from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.logging import get_logger
from app.repositories.base import QueryRepository, SchemaRepository
from app.schemas.schema import ExampleQuestionResponse, SchemaSummaryResponse
from app.services.schema_stats import get_schema_summary


router = APIRouter()
logger = get_logger("api.schema")


async def get_summary_repos(
    session_id: str | None = Query(default=None),
) -> tuple[SchemaRepository, QueryRepository]:
    from app.main import app_state

    if app_state is None:
        raise HTTPException(status_code=503, detail="Application not ready")

    if session_id:
        return (
            app_state.session_manager.get_schema_repo(session_id),
            app_state.session_manager.get_query_repo(session_id),
        )

    return app_state.ask_service.schema_repository, app_state.ask_service.query_repository


@router.get("/schema/summary", response_model=SchemaSummaryResponse)
async def schema_summary(
    repos: tuple[SchemaRepository, QueryRepository] = Depends(get_summary_repos),
) -> SchemaSummaryResponse:
    schema_repo, query_repo = repos
    try:
        summary = await get_schema_summary(schema_repo, query_repo)
    except ValueError as exc:
        logger.warning("Schema summary unavailable", extra={"error": str(exc)})
        raise HTTPException(status_code=400, detail=str(exc))

    return SchemaSummaryResponse(
        table_name=summary.table_name,
        row_count=summary.row_count,
        date_span_start=summary.date_span_start,
        date_span_end=summary.date_span_end,
        key_dimension_count=summary.key_dimension_count,
        headline_label=summary.headline_label,
        headline_value=summary.headline_value,
        examples=[
            ExampleQuestionResponse(question=e.question, answer_shape=e.answer_shape, hint=e.hint)
            for e in summary.examples
        ],
    )
