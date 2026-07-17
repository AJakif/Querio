"""Computes real EDA-style stats and grounded example questions from schema introspection.

Used by the empty-state EDA strip (no static/placeholder content): row count, date span,
key dimension count, and a headline total are all derived from the live schema + one
read-only aggregate query, so the same code works for the seeded `marts` dataset and any
uploaded CSV/JSON session.
"""

from app.core.logging import get_logger
from app.domain.models import ExampleQuestion, SchemaSummary
from app.repositories.base import ColumnInfo, QueryRepository, SchemaRepository


logger = get_logger("services.schema_stats")

_NUMERIC_HINTS = ("int", "numeric", "double", "real", "decimal", "float", "serial")
_DATE_HINTS = ("date", "time")

_MIN_EXAMPLES = 4
_MAX_EXAMPLES = 6


def _is_numeric(data_type: str) -> bool:
    lower = data_type.lower()
    return any(hint in lower for hint in _NUMERIC_HINTS)


def _is_date(data_type: str) -> bool:
    lower = data_type.lower()
    return any(hint in lower for hint in _DATE_HINTS)


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _pick_primary_table(table_columns: dict[str, list[ColumnInfo]]) -> str:
    # Heuristic: the "main" table for a single-dataset EDA summary is the widest one
    # (most columns) -- for the seeded marts schema this picks the fact table
    # (fct_orders) over the dimension table (dim_customers); for an uploaded CSV/JSON
    # session there is only ever one table, so this is a no-op there.
    return max(table_columns, key=lambda t: len(table_columns[t]))


def _generate_examples(
    table: str,
    columns: list[ColumnInfo],
    date_col: str | None,
    numeric_col: str | None,
) -> list[ExampleQuestion]:
    dimension_cols = [
        c.name for c in columns if not _is_numeric(c.data_type) and not _is_date(c.data_type)
    ]
    dimension_col = dimension_cols[0] if dimension_cols else None
    second_dimension_col = dimension_cols[1] if len(dimension_cols) > 1 else None

    candidates: list[ExampleQuestion] = [
        ExampleQuestion(
            question=f"How many {table} are there in total?",
            answer_shape="number",
            hint="Returns a single number.",
        )
    ]

    if numeric_col:
        candidates.append(
            ExampleQuestion(
                question=f"What is the total {numeric_col} across all {table}?",
                answer_shape="number",
                hint="Returns a single number.",
            )
        )

    if numeric_col and dimension_col:
        candidates.append(
            ExampleQuestion(
                question=f"What is the total {numeric_col} by {dimension_col}?",
                answer_shape="chart",
                hint=f"Returns a chart broken down by {dimension_col}.",
            )
        )
        candidates.append(
            ExampleQuestion(
                question=f"What are the top 10 {table} by {numeric_col}?",
                answer_shape="list",
                hint="Returns a list of the top matching rows.",
            )
        )

    if numeric_col and date_col:
        candidates.append(
            ExampleQuestion(
                question=f"How has {numeric_col} trended over {date_col}?",
                answer_shape="chart",
                hint="Returns a chart over time.",
            )
        )

    if dimension_col:
        candidates.append(
            ExampleQuestion(
                question=f"How many {table} are there per {dimension_col}?",
                answer_shape="chart",
                hint=f"Returns a chart broken down by {dimension_col}.",
            )
        )

    if second_dimension_col:
        candidates.append(
            ExampleQuestion(
                question=f"What are the most common values of {second_dimension_col}?",
                answer_shape="list",
                hint="Returns a list of the most frequent values.",
            )
        )

    # De-duplicate while preserving order, then clamp to the 4-6 range.
    seen: set[str] = set()
    unique: list[ExampleQuestion] = []
    for candidate in candidates:
        if candidate.question in seen:
            continue
        seen.add(candidate.question)
        unique.append(candidate)

    return unique[:_MAX_EXAMPLES]


async def get_schema_summary(schema_repo: SchemaRepository, query_repo: QueryRepository) -> SchemaSummary:
    tables = await schema_repo.get_tables()
    if not tables:
        raise ValueError("No tables were found in the configured schema.")

    table_columns = {table: await schema_repo.get_columns(table) for table in tables}
    primary_table = _pick_primary_table(table_columns)
    columns = table_columns[primary_table]

    date_col = next((c.name for c in columns if _is_date(c.data_type)), None)
    numeric_col = next((c.name for c in columns if _is_numeric(c.data_type)), None)
    key_dimension_count = sum(
        1 for c in columns if not _is_numeric(c.data_type) and not _is_date(c.data_type)
    )

    select_parts = ["COUNT(*) AS row_count"]
    if date_col:
        select_parts.append(f"MIN({_quote_ident(date_col)}) AS date_min")
        select_parts.append(f"MAX({_quote_ident(date_col)}) AS date_max")
    if numeric_col:
        select_parts.append(f"SUM({_quote_ident(numeric_col)}) AS headline_total")

    sql = f"SELECT {', '.join(select_parts)} FROM {_quote_ident(primary_table)}"
    rows = await query_repo.execute(sql)
    row = rows[0] if rows else {}

    row_count = int(row.get("row_count") or 0)
    date_span_start = str(row["date_min"]) if row.get("date_min") is not None else None
    date_span_end = str(row["date_max"]) if row.get("date_max") is not None else None

    if numeric_col and row.get("headline_total") is not None:
        headline_label = f"Total {numeric_col}"
        headline_value = float(row["headline_total"])
    else:
        headline_label = "Total records"
        headline_value = float(row_count)

    examples = _generate_examples(primary_table, columns, date_col, numeric_col)

    logger.info(
        "Computed schema summary",
        extra={
            "table": primary_table,
            "row_count": row_count,
            "key_dimension_count": key_dimension_count,
            "example_count": len(examples),
        },
    )

    return SchemaSummary(
        table_name=primary_table,
        row_count=row_count,
        date_span_start=date_span_start,
        date_span_end=date_span_end,
        key_dimension_count=key_dimension_count,
        headline_label=headline_label,
        headline_value=headline_value,
        examples=examples,
    )
