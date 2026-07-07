from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from app.core.logging import get_logger
from app.core.config import settings
from app.schemas.upload import (
    UploadPreviewResponse,
    UploadConfirmRequest,
    UploadConfirmResponse,
    ColumnPreview,
)
from app.services.csv_ingestion import parse_csv, parse_json
from app.services.session_manager import SessionManager


router = APIRouter()
logger = get_logger("api.upload")


def get_session_manager() -> SessionManager:
    from app.main import app_state
    if app_state is None:
        raise HTTPException(status_code=503, detail="Application not ready")
    return app_state.session_manager


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
        max_size = 50 * 1024 * 1024
        if len(content) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {max_size // (1024 * 1024)}MB.",
            )

        is_json = filename_lower.endswith(".json")
        preview = parse_json(content) if is_json else parse_csv(content)

        preview_token = session_manager.store_preview(preview)

        logger.info(
            "File preview generated",
            extra={
                "filename": file.filename,
                "file_type": "json" if is_json else "csv",
                "columns": len(preview.columns),
                "total_rows": preview.total_rows,
                "preview_token": preview_token,
            },
        )

        return UploadPreviewResponse(
            columns=[ColumnPreview(name=c.name, inferred_type=c.inferred_type) for c in preview.columns],
            sample_rows=preview.sample_rows,
            total_rows=preview.total_rows,
            preview_token=preview_token,
        )

    except ValueError as exc:
        logger.warning("File parsing failed", extra={"filename": file.filename, "error": str(exc)})
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error during file preview", extra={"filename": file.filename})
        raise HTTPException(status_code=500, detail="Failed to process file")


@router.post("/upload/confirm", response_model=UploadConfirmResponse)
async def upload_confirm(
    body: UploadConfirmRequest,
    session_manager: SessionManager = Depends(get_session_manager),
):
    try:
        session_id, row_count = await session_manager.create_session_schema(body.preview_token)

        logger.info(
            "Upload confirmed and data loaded",
            extra={
                "session_id": session_id,
                "row_count": row_count,
            },
        )

        return UploadConfirmResponse(
            session_id=session_id,
            table_name="uploaded_data",
            row_count=row_count,
        )

    except ValueError as exc:
        logger.warning("Upload confirm failed", extra={"error": str(exc)})
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error during upload confirm")
        raise HTTPException(status_code=500, detail="Failed to load data into database")
