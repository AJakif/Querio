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


class UploadConfirmResponse(BaseModel):
    session_id: str
    table_name: str
    row_count: int


class UploadErrorResponse(BaseModel):
    error: str
