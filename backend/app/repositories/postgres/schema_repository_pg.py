import asyncio

from app.repositories.base import SchemaRepository, ColumnInfo, RelationshipInfo


class PostgresSchemaRepository(SchemaRepository):
    def __init__(self, connection_factory=None):
        self._conn_factory = connection_factory

    def _get_conn(self):
        if self._conn_factory:
            return self._conn_factory()
        from app.core.db import get_connection
        return get_connection()

    async def get_tables(self) -> list[str]:
        def _run():
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT table_name FROM information_schema.tables
                        WHERE table_schema = 'public'
                        ORDER BY table_name
                    """)
                    return [row[0] for row in cur.fetchall()]
        return await asyncio.to_thread(_run)

    async def get_columns(self, table: str) -> list[ColumnInfo]:
        def _run():
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT column_name, data_type, is_nullable
                        FROM information_schema.columns
                        WHERE table_schema = 'public' AND table_name = %s
                        ORDER BY ordinal_position
                    """, (table,))
                    return [
                        ColumnInfo(
                            name=row[0],
                            data_type=row[1],
                            is_nullable=row[2] == "YES",
                        )
                        for row in cur.fetchall()
                    ]
        return await asyncio.to_thread(_run)

    async def get_relationships(self) -> list[RelationshipInfo]:
        def _run():
            with self._get_conn() as conn:
                with conn.cursor() as cur:
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
                            AND tc.table_schema = 'public'
                        ORDER BY tc.table_name, kcu.ordinal_position
                    """)
                    return [
                        RelationshipInfo(
                            source_table=row[0],
                            source_column=row[1],
                            target_table=row[2],
                            target_column=row[3],
                        )
                        for row in cur.fetchall()
                    ]
        return await asyncio.to_thread(_run)
