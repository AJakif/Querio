"""Detects a plausible join key between an uploaded dataset and the seed marts
schema, and produces suggested cross-dataset questions grounded in that key.

Detection is column-name match (case-insensitive) followed by a bounded
sample value-overlap check, to avoid suggesting a join on columns that
merely share a name but hold unrelated data (e.g. two unrelated "id"
columns).
"""

from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.repositories.base import QueryRepository, SchemaRepository

logger = get_logger("services.join_detection")

SAMPLE_LIMIT = 20
MAX_SUGGESTIONS = 3
MIN_SAMPLE_OVERLAP = 1


@dataclass
class JoinSuggestionResult:
    column: str | None
    seed_table: str | None
    questions: list[str] = field(default_factory=list)

    @property
    def detected(self) -> bool:
        return self.column is not None and self.seed_table is not None


@dataclass
class _CandidateMatch:
    column: str
    seed_table: str
    overlap: int


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


async def detect_cross_dataset_join(
    uploaded_table: str,
    uploaded_schema_repo: SchemaRepository,
    uploaded_query_repo: QueryRepository,
    seed_schema_repo: SchemaRepository,
    seed_query_repo: QueryRepository,
) -> JoinSuggestionResult:
    """Compare the uploaded table's columns against every table in the seed
    schema and return the strongest plausible join key, if any."""

    uploaded_columns = await uploaded_schema_repo.get_columns(uploaded_table)
    uploaded_names = {c.name.strip().lower(): c.name for c in uploaded_columns}
    if not uploaded_names:
        return JoinSuggestionResult(column=None, seed_table=None)

    seed_tables = await seed_schema_repo.get_tables()

    best: _CandidateMatch | None = None
    for seed_table in seed_tables:
        seed_columns = await seed_schema_repo.get_columns(seed_table)
        for seed_col in seed_columns:
            key = seed_col.name.strip().lower()
            uploaded_col_name = uploaded_names.get(key)
            if uploaded_col_name is None:
                continue

            overlap = await _sample_value_overlap(
                uploaded_table, uploaded_col_name, uploaded_query_repo,
                seed_table, seed_col.name, seed_query_repo,
            )
            if overlap < MIN_SAMPLE_OVERLAP:
                continue
            if best is None or overlap > best.overlap:
                best = _CandidateMatch(column=uploaded_col_name, seed_table=seed_table, overlap=overlap)

    if best is None:
        logger.info(
            "No plausible cross-dataset join key detected",
            extra={"uploaded_table": uploaded_table},
        )
        return JoinSuggestionResult(column=None, seed_table=None)

    logger.info(
        "Detected cross-dataset join key",
        extra={
            "uploaded_table": uploaded_table,
            "seed_table": best.seed_table,
            "column": best.column,
            "sample_overlap": best.overlap,
        },
    )
    return JoinSuggestionResult(
        column=best.column,
        seed_table=best.seed_table,
        questions=_build_questions(uploaded_table, best.seed_table, best.column),
    )


async def _sample_value_overlap(
    table_a: str, column_a: str, query_repo_a: QueryRepository,
    table_b: str, column_b: str, query_repo_b: QueryRepository,
) -> int:
    sql_a = (
        f"SELECT DISTINCT {_quote_ident(column_a)} AS v FROM {_quote_ident(table_a)} "
        f"WHERE {_quote_ident(column_a)} IS NOT NULL LIMIT {SAMPLE_LIMIT}"
    )
    sql_b = (
        f"SELECT DISTINCT {_quote_ident(column_b)} AS v FROM {_quote_ident(table_b)} "
        f"WHERE {_quote_ident(column_b)} IS NOT NULL LIMIT {SAMPLE_LIMIT}"
    )
    try:
        rows_a = await query_repo_a.execute(sql_a)
        rows_b = await query_repo_b.execute(sql_b)
    except Exception as exc:
        logger.warning(
            "Join key sample overlap check failed",
            extra={"table_a": table_a, "column_a": column_a, "table_b": table_b, "column_b": column_b, "error": str(exc)},
        )
        return 0

    values_a = {str(row.get("v")) for row in rows_a if row.get("v") is not None}
    values_b = {str(row.get("v")) for row in rows_b if row.get("v") is not None}
    return len(values_a & values_b)


def _build_questions(uploaded_table: str, seed_table: str, column: str) -> list[str]:
    return [
        f"How many records in {uploaded_table} match {seed_table} on {column}?",
        f"Show a combined view of {uploaded_table} and {seed_table} joined on {column}.",
        f"What are the top {column} values shared between {uploaded_table} and {seed_table}?",
    ][:MAX_SUGGESTIONS]
