import asyncio
from psycopg2.extras import RealDictCursor

from app.core.logging import get_logger
from app.core.config import settings
from app.repositories.base import QueryRepository

logger = get_logger("repositories.postgres.query")


class PostgresQueryRepository(QueryRepository):
    def __init__(self, connection_factory=None):
        self._conn_factory = connection_factory

    def _get_conn(self):
        if self._conn_factory:
            return self._conn_factory()
        from app.core.db import get_connection
        return get_connection()

    async def execute(self, sql: str) -> list[dict]:
        def _run():
            logger.debug("Opening Postgres connection for query execution")
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SET TRANSACTION READ ONLY")
                    cur.execute("SET LOCAL statement_timeout = %s", (settings.query_timeout_ms,))
                    logger.debug("Executing Postgres query", extra={"sql": sql})
                    cur.execute(sql)
                    rows = [dict(row) for row in cur.fetchall()]
                    logger.info("Postgres query completed", extra={"row_count": len(rows)})
                    return rows
        return await asyncio.to_thread(_run)
