"""Wraps two SchemaRepository instances so the agent can see both an active
upload session's table(s) and a secondary (the seed `marts`) schema's tables in
a single schema listing, for cross-dataset questions (Epic 8 Slice 16).

Only used when a session has a detected join key against the seed schema --
the single-dataset path is untouched. Query execution needs no wrapping: SQL
generated against schema-qualified secondary-table names (e.g. `marts.fct_orders`)
resolves regardless of the session's `search_path`, since search_path only
affects unqualified identifiers (see `PostgresQueryRepository.execute`).
"""

from app.repositories.base import ColumnInfo, RelationshipInfo, SchemaRepository


class CombinedSchemaRepository(SchemaRepository):
    """Primary (the upload session) tables are exposed unqualified, exactly as
    before, so existing single-dataset questions don't regress. Secondary (seed
    schema) tables are exposed prefixed with ``{secondary_prefix}.`` so the LLM
    can reference them as schema-qualified SQL identifiers.
    """

    def __init__(
        self,
        primary: SchemaRepository,
        secondary: SchemaRepository,
        secondary_prefix: str,
    ) -> None:
        self._primary = primary
        self._secondary = secondary
        self._secondary_prefix = secondary_prefix

    def _qualify(self, table: str) -> str:
        return f"{self._secondary_prefix}.{table}"

    async def get_tables(self) -> list[str]:
        primary_tables = await self._primary.get_tables()
        secondary_tables = await self._secondary.get_tables()
        return list(primary_tables) + [self._qualify(t) for t in secondary_tables]

    async def get_columns(self, table: str) -> list[ColumnInfo]:
        prefix = f"{self._secondary_prefix}."
        if table.startswith(prefix):
            return await self._secondary.get_columns(table[len(prefix):])
        return await self._primary.get_columns(table)

    async def get_relationships(self) -> list[RelationshipInfo]:
        # Cross-schema relationships aren't introspected here (low value for
        # this feature) -- fall back to the primary dataset's own relationships.
        return await self._primary.get_relationships()
