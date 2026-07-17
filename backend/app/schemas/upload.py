from pydantic import BaseModel
from typing import Any


class ColumnStats(BaseModel):
    null_percentage: float
    min_value: Any
    max_value: Any
    mean_value: float | None
    top_values: list[dict[str, Any]] | None


class ColumnPreview(BaseModel):
    name: str
    inferred_type: str
    stats: ColumnStats


class UploadPreviewResponse(BaseModel):
    columns: list[ColumnPreview]
    sample_rows: list[dict[str, Any]]
    total_rows: int
    preview_token: str


class UrlPreviewRequest(BaseModel):
    url: str


class UploadConfirmRequest(BaseModel):
    preview_token: str
    context_note: str = ""
    current_session_id: str = ""


class UploadConfirmResponse(BaseModel):
    session_id: str
    table_name: str
    row_count: int
    join_key_column: str | None = None
    join_key_table: str | None = None
    suggested_questions: list[str] = []


class UploadErrorResponse(BaseModel):
    error: str
