import asyncio
import uuid
from typing import Any

from psycopg2 import extras as psycopg2_extras

from app.core.db import get_connection
from app.core.logging import get_logger
from app.services.csv_ingestion import CsvPreviewResult, InferredColumn
from app.repositories.postgres.schema_repository_pg import PostgresSchemaRepository
from app.repositories.postgres.query_repository_pg import PostgresQueryRepository


logger = get_logger("services.session_manager")


TYPE_MAP = {
    "integer": "BIGINT",
    "numeric": "NUMERIC",
    "date": "DATE",
    "timestamp": "TIMESTAMP",
    "text": "TEXT",
}

UPLOADED_TABLE_NAME = "uploaded_data"
SAMPLE_ROWS_COUNT = 10


class PreviewStore:
    def __init__(self):
        self._store: dict[str, CsvPreviewResult] = {}

    def store(self, result: CsvPreviewResult) -> str:
        token = str(uuid.uuid4())
        self._store[token] = result
        logger.debug("Stored preview data", extra={"token": token, "rows": result.total_rows})
        return token

    def get(self, token: str) -> CsvPreviewResult | None:
        data = self._store.get(token)
        if data is None:
            logger.warning("Preview token not found", extra={"token": token})
        return data

    def remove(self, token: str) -> None:
        self._store.pop(token, None)


class SessionManager:
    def __init__(self, preview_store: PreviewStore | None = None):
        self._preview_store = preview_store or PreviewStore()

    def store_preview(self, result: CsvPreviewResult) -> str:
        return self._preview_store.store(result)

    def get_preview(self, token: str) -> CsvPreviewResult | None:
        return self._preview_store.get(token)

    async def create_session_schema(self, preview_token: str) -> tuple[str, int]:
        preview = self._preview_store.get(preview_token)
        if preview is None:
            raise ValueError("Preview data not found or expired")

        session_id = str(uuid.uuid4())
        schema_name = f"session_{session_id.replace('-', '_')}"

        self._preview_store.remove(preview_token)

        await _create_schema(schema_name)
        table_sql = _build_create_table_sql(schema_name, preview.columns)
        await _execute_ddl(table_sql)
        await _bulk_insert(schema_name, preview.columns, preview.all_rows)

        row_count = preview.total_rows

        logger.info(
            "Created session schema",
            extra={
                "session_id": session_id,
                "schema": schema_name,
                "table": UPLOADED_TABLE_NAME,
                "row_count": row_count,
                "column_count": len(preview.columns),
            },
        )

        return session_id, row_count

    async def drop_session_schema(self, session_id: str) -> None:
        schema_name = _session_id_to_schema(session_id)
        try:
            await _execute_ddl(f"DROP SCHEMA IF EXISTS {_quote_ident(schema_name)} CASCADE")
            logger.info("Dropped session schema", extra={"session_id": session_id, "schema": schema_name})
        except Exception as exc:
            logger.error(
                "Failed to drop session schema",
                extra={"session_id": session_id, "schema": schema_name, "error": str(exc)},
            )

    def get_schema_repo(self, session_id: str) -> PostgresSchemaRepository:
        schema_name = _session_id_to_schema(session_id)
        return PostgresSchemaRepository(schema=schema_name)

    def get_query_repo(self, session_id: str) -> PostgresQueryRepository:
        schema_name = _session_id_to_schema(session_id)
        return PostgresQueryRepository(schema_override=schema_name)


def _session_id_to_schema(session_id: str) -> str:
    return f"session_{session_id.replace('-', '_')}"


def _quote_ident(name: str) -> str:
    return f'"{name}"'


async def _create_schema(schema_name: str) -> None:
    def _run():
        logger.debug("Creating session schema", extra={"schema": schema_name})
        with get_connection() as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(f"CREATE SCHEMA IF NOT EXISTS {_quote_ident(schema_name)}")
    await asyncio.to_thread(_run)


async def _execute_ddl(sql: str) -> None:
    def _run():
        with get_connection() as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(sql)
    await asyncio.to_thread(_run)


def _build_create_table_sql(schema_name: str, columns: list[InferredColumn]) -> str:
    col_defs = []
    for c in columns:
        pg_type = TYPE_MAP.get(c.inferred_type, "TEXT")
        col_defs.append(f"  {_quote_ident(c.name)} {pg_type}")
    cols_sql = ",\n".join(col_defs)
    return (
        f"CREATE TABLE IF NOT EXISTS {_quote_ident(schema_name)}.{_quote_ident(UPLOADED_TABLE_NAME)} (\n"
        f"{cols_sql}\n"
        f")"
    )


async def _bulk_insert(schema_name: str, columns: list[InferredColumn], rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    col_names = [c.name for c in columns]
    quoted_cols = ", ".join(_quote_ident(c) for c in col_names)
    insert_sql = (
        f"INSERT INTO {_quote_ident(schema_name)}.{_quote_ident(UPLOADED_TABLE_NAME)} "
        f"({quoted_cols}) VALUES %s"
    )

    def _run():
        with get_connection() as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                batch = []
                for row in rows:
                    values = [_convert_value(row.get(c.name, ""), c.inferred_type) for c in columns]
                    batch.append(values)
                psycopg2_extras.execute_values(cur, insert_sql, batch, template=None, page_size=1000)

    await asyncio.to_thread(_run)


def _convert_value(value: Any, inferred_type: str) -> Any:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None
    if inferred_type == "integer":
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    if inferred_type == "numeric":
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    if inferred_type in ("date", "timestamp"):
        return str(value)
    return str(value)
