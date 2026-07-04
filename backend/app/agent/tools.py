from pydantic_ai import RunContext

from app.repositories.base import SchemaRepository


async def format_schema(repo: SchemaRepository) -> str:
    tables = await repo.get_tables()
    parts = []
    for table in tables:
        columns = await repo.get_columns(table)
        cols = [f"  - {c.name} ({c.data_type})" for c in columns]
        parts.append(f"Table: {table}\n" + "\n".join(cols))

    rels = await repo.get_relationships()
    if rels:
        rel_lines = []
        for r in rels:
            rel_lines.append(f"  {r.source_table}.{r.source_column} -> {r.target_table}.{r.target_column}")
        parts.append("Relationships:\n" + "\n".join(rel_lines))

    return "\n\n".join(parts)


async def get_schema(ctx: RunContext[SchemaRepository]) -> str:
    return await format_schema(ctx.deps)
