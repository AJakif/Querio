from pydantic_ai import RunContext

from app.repositories.base import SchemaRepository


async def get_schema(ctx: RunContext[SchemaRepository]) -> str:
    """Get the database schema — all public tables and their columns with types."""
    tables = await ctx.deps.get_tables()
    parts = []
    for table in tables:
        columns = await ctx.deps.get_columns(table)
        cols = [f"  - {c.name} ({c.data_type})" for c in columns]
        parts.append(f"Table: {table}\n" + "\n".join(cols))
    return "\n\n".join(parts)
