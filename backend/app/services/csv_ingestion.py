import csv
import io
import re
from datetime import datetime
from typing import Any

from app.core.logging import get_logger


logger = get_logger("services.csv_ingestion")


class InferredColumn:
    name: str
    inferred_type: str
    values: list[str]

    def __init__(self, name: str, values: list[str]):
        self.name = name
        self.values = values
        self.inferred_type = self._infer_type()

    def _infer_type(self) -> str:
        non_null = [v for v in self.values if v is not None and v.strip() != ""]
        if not non_null:
            return "text"

        if all(_is_integer(v) for v in non_null):
            return "integer"
        if all(_is_numeric(v) for v in non_null):
            return "numeric"
        if all(_is_date(v) for v in non_null):
            return "date"
        if all(_is_timestamp(v) for v in non_null):
            return "timestamp"

        return "text"


class CsvPreviewResult:
    columns: list[InferredColumn]
    sample_rows: list[dict[str, Any]]
    all_rows: list[dict[str, Any]]
    total_rows: int

    def __init__(self, columns: list[InferredColumn], all_rows: list[dict[str, Any]], sample_size: int = 10):
        self.columns = columns
        self.all_rows = all_rows
        self.sample_rows = all_rows[:sample_size]
        self.total_rows = len(all_rows)


def parse_csv(content: bytes, sample_size: int = 10) -> CsvPreviewResult:
    decoded = _decode_content(content)
    reader = csv.DictReader(io.StringIO(decoded))
    if reader.fieldnames is None or len(reader.fieldnames) == 0:
        raise ValueError("CSV file has no columns")

    rows: list[dict[str, Any]] = []
    sanitized_fieldnames = [_sanitize_column_name(h) for h in reader.fieldnames]
    name_map = dict(zip(reader.fieldnames, sanitized_fieldnames))

    for row in reader:
        sanitized = {name_map[k]: v for k, v in row.items()}
        rows.append(sanitized)

    if not rows:
        raise ValueError("CSV file has no data rows")

    columns = []
    for col_name in sanitized_fieldnames:
        col_values = [row.get(col_name, "") for row in rows]
        columns.append(InferredColumn(col_name, col_values))

    logger.info(
        "Parsed CSV file",
        extra={
            "column_count": len(columns),
            "total_rows": len(rows),
            "columns": [{"name": c.name, "type": c.inferred_type} for c in columns],
        },
    )

    return CsvPreviewResult(columns=columns, all_rows=rows, sample_size=sample_size)


def _decode_content(content: bytes) -> str:
    encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            return content.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return content.decode("utf-8", errors="replace")


def _sanitize_column_name(name: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name.strip())
    sanitized = re.sub(r"_+", "_", sanitized)
    sanitized = sanitized.strip("_")
    if not sanitized or sanitized[0].isdigit():
        sanitized = "col_" + sanitized
    if not sanitized:
        sanitized = "column"
    return sanitized.lower()


def _is_integer(v: str) -> bool:
    try:
        int(v.strip())
        return True
    except (ValueError, AttributeError):
        return False


def _is_numeric(v: str) -> bool:
    try:
        float(v.strip())
        return True
    except (ValueError, AttributeError):
        return False


def _is_date(v: str) -> bool:
    date_patterns = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%m-%d-%Y",
    ]
    stripped = v.strip()
    for pattern in date_patterns:
        try:
            datetime.strptime(stripped, pattern)
            return True
        except ValueError:
            continue
    return False


def _is_timestamp(v: str) -> bool:
    ts_patterns = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%f",
    ]
    stripped = v.strip()
    for pattern in ts_patterns:
        try:
            datetime.strptime(stripped, pattern)
            return True
        except ValueError:
            continue
    return False
