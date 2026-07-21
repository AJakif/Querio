import asyncio
from decimal import Decimal

from psycopg2.extras import RealDictCursor

from app.core.logging import get_logger
from app.core.config import settings
from app.repositories.base import QueryRepository

logger = get_logger("repositories.postgres.query")


def _normalize_value(value: object) -> object:
    # psycopg2 returns numeric/decimal columns (e.g. SUM() results) as Decimal.
    # Pydantic serializes Decimal inside dict[str, Any] fields as a JSON string,
    # not a number — which breaks Recharts' numeric axis scale downstream. Cast
    # to float at the repository boundary so every consumer sees a real number.
    if isinstance(value, Decimal):
        return float(value)
    return value


class PostgresQueryRepository(QueryRepository):
    def __init__(self, connection_factory=None, schema_override: str | None = None):
        self._conn_factory = connection_factory
        self._schema_override = schema_override

    def _get_conn(self):
        if self._conn_factory:
            return self._conn_factory()
        from app.core.db import get_connection
        return get_connection()

    @property
    def _effective_schema(self) -> str:
        return self._schema_override or settings.db_schema

    async def execute(self, sql: str) -> list[dict]:
        def _run():
            logger.debug("Opening Postgres connection for query execution")
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SET TRANSACTION READ ONLY")
                    cur.execute("SELECT set_config('search_path', %s, true)", (f"{self._effective_schema},public",))
                    cur.execute("SET LOCAL statement_timeout = %s", (settings.query_timeout_ms,))
                    logger.debug("Executing Postgres query", extra={"sql": sql})
                    cur.execute(sql)
                    rows = [
                        {key: _normalize_value(value) for key, value in row.items()}
                        for row in cur.fetchall()
                    ]
                    logger.info("Postgres query completed", extra={"row_count": len(rows)})
                    return rows
        return await asyncio.to_thread(_run)
