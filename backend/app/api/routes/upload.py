import asyncio

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from app.core.logging import get_logger
from app.core.config import settings
from app.schemas.upload import (
    UploadPreviewResponse,
    UrlPreviewRequest,
    UploadConfirmRequest,
    UploadConfirmResponse,
    ColumnPreview,
    ColumnStats,
)
from app.repositories.base import QueryRepository, SchemaRepository
from app.services.csv_ingestion import parse_csv, parse_json
from app.services.join_detection import JoinSuggestionResult, detect_cross_dataset_join
from app.services.session_manager import UPLOADED_TABLE_NAME, SessionManager
from app.services.ssrf_guard import fetch_url, SSRFError


router = APIRouter()
logger = get_logger("api.upload")

MAX_UPLOAD_SIZE = 50 * 1024 * 1024


def get_session_manager() -> SessionManager:
    from app.main import app_state
    if app_state is None:
        raise HTTPException(status_code=503, detail="Application not ready")
    return app_state.session_manager


def get_seed_schema_repository() -> SchemaRepository:
    from app.main import app_state
    if app_state is None:
        raise HTTPException(status_code=503, detail="Application not ready")
    return app_state.schema_repository


def get_seed_query_repository() -> QueryRepository:
    from app.main import app_state
    if app_state is None:
        raise HTTPException(status_code=503, detail="Application not ready")
    return app_state.query_repository


@router.post("/upload/preview", response_model=UploadPreviewResponse)
async def upload_preview(
    file: UploadFile = File(...),
    session_manager: SessionManager = Depends(get_session_manager),
):
    if not settings.has_env("DATABASE_URL"):
        raise HTTPException(
            status_code=400,
            detail="Upload requires a PostgreSQL database connection. DATABASE_URL is not configured.",
        )

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename provided.",
        )

    filename_lower = file.filename.lower()
    if not (filename_lower.endswith(".csv") or filename_lower.endswith(".json")):
        raise HTTPException(
            status_code=400,
            detail="Only .csv and .json files are supported. Please upload a CSV or JSON file.",
        )

    try:
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        if len(content) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024 * 1024)}MB.",
            )

        is_json = filename_lower.endswith(".json")
        preview = parse_json(content) if is_json else parse_csv(content)

        preview_token = session_manager.store_preview(preview)

        logger.info(
            "File preview generated",
            extra={
                "file_name": file.filename,
                "file_type": "json" if is_json else "csv",
                "columns": len(preview.columns),
                "total_rows": preview.total_rows,
                "preview_token": preview_token,
            },
        )

        return UploadPreviewResponse(
            columns=[ColumnPreview(name=c.name, inferred_type=c.inferred_type, stats=ColumnStats(**c.stats)) for c in preview.columns],
            sample_rows=preview.sample_rows,
            total_rows=preview.total_rows,
            preview_token=preview_token,
        )

    except HTTPException:
        raise
    except ValueError as exc:
        logger.warning("File parsing failed", extra={"file_name": file.filename, "error": str(exc)})
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error during file preview", extra={"file_name": file.filename})
        raise HTTPException(status_code=500, detail="Failed to process file")


@router.post("/upload/preview-from-url", response_model=UploadPreviewResponse)
async def upload_preview_from_url(
    body: UrlPreviewRequest,
    session_manager: SessionManager = Depends(get_session_manager),
):
    if not settings.has_env("DATABASE_URL"):
        raise HTTPException(
            status_code=400,
            detail="Upload requires a PostgreSQL database connection. DATABASE_URL is not configured.",
        )

    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required.")

    try:
        content, content_type = await asyncio.to_thread(
            fetch_url, url, 50 * 1024 * 1024
        )

        if "json" in content_type:
            is_json = True
        elif "csv" in content_type:
            is_json = False
        else:
            is_json = url.lower().endswith(".json")

        if is_json:
            preview = parse_json(content)
        else:
            preview = parse_csv(content)

        preview_token = session_manager.store_preview(preview)

        logger.info(
            "URL preview generated",
            extra={
                "url": url,
                "content_type": content_type,
                "file_type": "json" if is_json else "csv",
                "columns": len(preview.columns),
                "total_rows": preview.total_rows,
                "preview_token": preview_token,
            },
        )

        return UploadPreviewResponse(
            columns=[ColumnPreview(name=c.name, inferred_type=c.inferred_type, stats=ColumnStats(**c.stats)) for c in preview.columns],
            sample_rows=preview.sample_rows,
            total_rows=preview.total_rows,
            preview_token=preview_token,
        )

    except SSRFError as exc:
        logger.warning("URL fetch rejected by SSRF guard", extra={"url": url, "error": str(exc)})
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        logger.warning("URL content parsing failed", extra={"url": url, "error": str(exc)})
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error during URL preview", extra={"url": url})
        raise HTTPException(status_code=500, detail="Failed to fetch or process URL")


@router.post("/upload/confirm", response_model=UploadConfirmResponse)
async def upload_confirm(
    body: UploadConfirmRequest,
    session_manager: SessionManager = Depends(get_session_manager),
    seed_schema_repo: SchemaRepository = Depends(get_seed_schema_repository),
    seed_query_repo: QueryRepository = Depends(get_seed_query_repository),
):
    try:
        session_id, row_count = await session_manager.create_session_schema(
            body.preview_token,
            context_note=body.context_note,
            current_session_id=body.current_session_id,
        )

        logger.info(
            "Upload confirmed and data loaded",
            extra={
                "session_id": session_id,
                "row_count": row_count,
            },
        )

        join_result = JoinSuggestionResult(column=None, seed_table=None)
        try:
            join_result = await detect_cross_dataset_join(
                uploaded_table=UPLOADED_TABLE_NAME,
                uploaded_schema_repo=session_manager.get_schema_repo(session_id),
                uploaded_query_repo=session_manager.get_query_repo(session_id),
                seed_schema_repo=seed_schema_repo,
                seed_query_repo=seed_query_repo,
            )
        except Exception as exc:
            logger.warning(
                "Cross-dataset join detection failed; continuing without suggestions",
                extra={"session_id": session_id, "error": str(exc)},
            )

        if join_result.detected and join_result.column is not None and join_result.seed_table is not None:
            session_manager.set_join_key(session_id, join_result.column, join_result.seed_table)

        return UploadConfirmResponse(
            session_id=session_id,
            table_name="uploaded_data",
            row_count=row_count,
            join_key_column=join_result.column,
            join_key_table=join_result.seed_table,
            suggested_questions=join_result.questions,
        )

    except ValueError as exc:
        logger.warning("Upload confirm failed", extra={"error": str(exc)})
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error during upload confirm")
        raise HTTPException(status_code=500, detail="Failed to load data into database")
