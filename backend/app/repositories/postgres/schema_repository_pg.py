import asyncio
from collections.abc import Mapping, Sequence

from psycopg2.extras import RealDictCursor

from app.core.logging import get_logger
from app.repositories.base import SchemaRepository, ColumnInfo, RelationshipInfo
from app.core.config import settings

logger = get_logger("repositories.postgres.schema")


def _row_value(row, key: str, index: int):
    if isinstance(row, Mapping):
        return row[key]
    if isinstance(row, Sequence) and not isinstance(row, (str, bytes, bytearray)):
        return row[index]
    raise TypeError(f"Unsupported row type returned from schema query: {type(row)!r}")


class PostgresSchemaRepository(SchemaRepository):
    def __init__(self, connection_factory=None, schema: str | None = None):
        self._conn_factory = connection_factory
        self._schema = schema or settings.db_schema

    def _get_conn(self):
        if self._conn_factory:
            return self._conn_factory()
        from app.core.db import get_connection
        return get_connection()

    async def get_tables(self) -> list[str]:
        def _run():
            logger.debug("Loading schema tables", extra={"schema": self._schema})
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT table_name FROM information_schema.tables
                        WHERE table_schema = %s
                        ORDER BY table_name
                    """, (self._schema,))
                    rows = [_row_value(row, "table_name", 0) for row in cur.fetchall()]
                    logger.info("Loaded schema tables", extra={"schema": self._schema, "table_count": len(rows)})
                    return rows
        return await asyncio.to_thread(_run)

    async def get_columns(self, table: str) -> list[ColumnInfo]:
        def _run():
            logger.debug("Loading table columns", extra={"schema": self._schema, "table": table})
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT column_name, data_type, is_nullable
                        FROM information_schema.columns
                        WHERE table_schema = %s AND table_name = %s
                        ORDER BY ordinal_position
                    """, (self._schema, table))
                    columns = [
                        ColumnInfo(
                            name=_row_value(row, "column_name", 0),
                            data_type=_row_value(row, "data_type", 1),
                            is_nullable=_row_value(row, "is_nullable", 2) == "YES",
                        )
                        for row in cur.fetchall()
                    ]
                    logger.info(
                        "Loaded table columns",
                        extra={"schema": self._schema, "table": table, "column_count": len(columns)},
                    )
                    return columns
        return await asyncio.to_thread(_run)

    async def get_relationships(self) -> list[RelationshipInfo]:
        def _run():
            logger.debug("Loading schema relationships", extra={"schema": self._schema})
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT
                            kcu.table_name AS source_table,
                            kcu.column_name AS source_column,
                            ccu.table_name AS target_table,
                            ccu.column_name AS target_column
                        FROM information_schema.table_constraints AS tc
                        JOIN information_schema.key_column_usage AS kcu
                            ON tc.constraint_name = kcu.constraint_name
                            AND tc.table_schema = kcu.table_schema
                        JOIN information_schema.constraint_column_usage AS ccu
                            ON ccu.constraint_name = tc.constraint_name
                            AND ccu.table_schema = tc.table_schema
                        WHERE tc.constraint_type = 'FOREIGN KEY'
                            AND tc.table_schema = %s
                        ORDER BY tc.table_name, kcu.ordinal_position
                    """, (self._schema,))
                    relationships = [
                        RelationshipInfo(
                            source_table=_row_value(row, "source_table", 0),
                            source_column=_row_value(row, "source_column", 1),
                            target_table=_row_value(row, "target_table", 2),
                            target_column=_row_value(row, "target_column", 3),
                        )
                        for row in cur.fetchall()
                    ]
                    logger.info(
                        "Loaded schema relationships",
                        extra={"schema": self._schema, "relationship_count": len(relationships)},
                    )
                    return relationships
        return await asyncio.to_thread(_run)
