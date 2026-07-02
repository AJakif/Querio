import asyncio
from psycopg2.extras import RealDictCursor

from app.repositories.base import QueryRepository


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
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql)
                    return [dict(row) for row in cur.fetchall()]
        return await asyncio.to_thread(_run)
