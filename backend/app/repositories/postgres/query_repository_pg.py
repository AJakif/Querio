import asyncio
from psycopg2.extras import RealDictCursor

from app.repositories.base import QueryRepository
from app.core.db import ConnectionFactory


class PostgresQueryRepository(QueryRepository):
    def __init__(self, connection_factory: ConnectionFactory | None = None):
        self._conn_factory = connection_factory or ConnectionFactory()

    async def execute(self, sql: str) -> list[dict]:
        def _run():
            with self._conn_factory() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql)
                    return [dict(row) for row in cur.fetchall()]
        return await asyncio.to_thread(_run)
