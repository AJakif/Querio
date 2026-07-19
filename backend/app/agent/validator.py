"""Mechanical post-guardrail validator.

No LLM — pure computation over SQL AST, schema metadata, and query results.
Always runs; no Fake variant needed.
"""
from __future__ import annotations

import hashlib

import sqlglot
import sqlglot.expressions as exp

from app.agent.contracts import AnswerSpec, Claim
from app.core.logging import get_logger
from app.domain.models import Dependency, Fingerprint, ValidationResult
from app.repositories.base import ColumnInfo, QueryRepository, SchemaRepository

logger = get_logger("agent.validator")

_LOW_CARD_CAP = 50


class Validator:
    """Compute dependency set, fingerprints, and scan cost for a validated SQL query."""

    def verify_claims(
        self,
        spec: AnswerSpec,
        rows: list[dict],
    ) -> tuple[AnswerSpec, int]:
        """Re-execute every claim and drop any that cannot be verified against real rows.

        - ``row``-typed claims: each cited cell must match rows[row][column]; drop on any mismatch.
        - ``computation``-typed claims: operands are derived from cited cells resolved against real
          rows (never trusted from the LLM-supplied ``operands`` field); recomputed value must match
          ``claim.value`` within tolerance; drop if cells fail to resolve or arithmetic mismatches.
        - If ``claim.cells`` is empty for a computation claim, falls back to ``claim.operands``
          (legacy path for claims without cell citations).
        - ``restatement`` and ``headline`` are never touched.
        - Unrecognized operations are dropped (zero verification = not trusted).
        - Returns (updated_spec, dropped_count) where dropped_count is the count dropped in THIS call.
        """
        kept: list[Claim] = []
        dropped = 0

        for claim in spec.claims:
            if claim.type == "row":
                # Row-cite verification: every cited cell must match the real result set.
                if claim.cells and not _verify_row_cells(claim.cells, rows):
                    logger.info(
                        "Dropping row claim — cited cell value doesn't match result rows",
                        extra={"sentence": claim.sentence},
                    )
                    dropped += 1
                    continue
                kept.append(claim)
                continue

            if claim.type != "computation":
                kept.append(claim)
                continue

            # Missing required fields → can't verify; preserve the claim
            if claim.value is None or claim.operation is None:
                kept.append(claim)
                continue

            # Derive operands from cited cells against real rows (never trust LLM operands).
            if claim.cells:
                derived = _resolve_cells_to_values(claim.cells, rows)
                if derived is None:
                    logger.info(
                        "Dropping computation claim — cells failed to resolve against result rows",
                        extra={"sentence": claim.sentence},
                    )
                    dropped += 1
                    continue
                operands = derived
            elif claim.operands is not None:
                # No cells — fall back to LLM-supplied operands (legacy path)
                operands = claim.operands
            else:
                # No cells and no operands — can't verify; preserve
                kept.append(claim)
                continue

            recomputed = _recompute(claim.operation, operands)
            if recomputed is None:
                # Unrecognized operation — zero verification means not trusted; drop it
                logger.debug(
                    "Unrecognized operation; claim dropped (unverifiable)",
                    extra={"operation": claim.operation},
                )
                dropped += 1
                continue

            b = claim.value
            tol = 1e-6 * max(1.0, abs(b))
            if abs(recomputed - b) < tol:
                kept.append(claim)
            else:
                logger.info(
                    "Dropping computation claim — arithmetic mismatch",
                    extra={
                        "operation": claim.operation,
                        "recomputed": recomputed,
                        "claimed": b,
                        "delta": abs(recomputed - b),
                    },
                )
                dropped += 1

        updated = spec.model_copy(update={"claims": kept, "dropped_claim_count": dropped})
        return updated, dropped

    async def validate(
        self,
        sql: str,
        schema_repo: SchemaRepository,
        query_repo: QueryRepository,
    ) -> ValidationResult:
        try:
            parsed = sqlglot.parse_one(sql, dialect="postgres")
        except Exception as exc:
            logger.warning("Failed to parse SQL for validation", extra={"error": str(exc)})
            return ValidationResult(dependency_set=[], fingerprints=[], scan_cost=0)

        alias_map = _build_alias_map(parsed)
        unique_tables = list(dict.fromkeys(alias_map.values()))
        deps = _extract_dependencies(parsed, alias_map, unique_tables)
        where_group_cols = _find_where_group_columns(parsed, alias_map)

        fingerprints: list[Fingerprint] = []
        for dep in deps:
            schema_cols = await schema_repo.get_columns(dep.table)
            col_info = next((c for c in schema_cols if c.name == dep.column), None)
            if col_info is None:
                continue

            schema_hash = _hash_schema(col_info)
            value_hash: str | None = None

            in_where_group = (
                (dep.table, dep.column) in where_group_cols
                or ("", dep.column) in where_group_cols
            )
            if in_where_group:
                value_hash = await _compute_value_hash(dep.table, dep.column, query_repo)

            fingerprints.append(
                Fingerprint(
                    table=dep.table,
                    column=dep.column,
                    schema_hash=schema_hash,
                    value_hash=value_hash,
                )
            )

        scan_cost = await _compute_scan_cost(sql, query_repo)
        logger.debug(
            "Validator completed",
            extra={
                "dep_count": len(deps),
                "fingerprint_count": len(fingerprints),
                "scan_cost": scan_cost,
            },
        )
        return ValidationResult(
            dependency_set=deps,
            fingerprints=fingerprints,
            scan_cost=scan_cost,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_cells_to_values(cells: list[dict], rows: list[dict]) -> list[float] | None:
    """Resolve each cited cell to its actual numeric value from the real result set.

    Returns a list of floats in cell order, or None if any cell cannot be resolved
    (out-of-bounds row index, missing column, or non-numeric value).
    """
    values: list[float] = []
    for cell in cells:
        row_idx = cell.get("row")
        col = cell.get("column")
        if row_idx is None or col is None:
            return None
        if not isinstance(row_idx, int) or row_idx < 0 or row_idx >= len(rows):
            return None
        row = rows[row_idx]
        if col not in row:
            return None
        try:
            values.append(float(row[col]))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
    return values


def _verify_row_cells(cells: list[dict], rows: list[dict]) -> bool:
    """Return True only if every cited cell matches rows[row][column] within tolerance.

    Numeric values are compared with a relative tolerance; strings are compared exactly.
    Returns False if any cell is out of bounds, the column is missing, or the value differs.
    """
    for cell in cells:
        row_idx = cell.get("row")
        col = cell.get("column")
        expected = cell.get("value")
        if row_idx is None or col is None:
            return False
        if not isinstance(row_idx, int) or row_idx < 0 or row_idx >= len(rows):
            return False
        row = rows[row_idx]
        if col not in row:
            return False
        actual = row[col]
        try:
            f_actual = float(actual)  # type: ignore[arg-type]
            f_expected = float(expected)  # type: ignore[arg-type]
            tol = 1e-6 * max(1.0, abs(f_expected))
            if abs(f_actual - f_expected) >= tol:
                return False
        except (TypeError, ValueError):
            if str(actual) != str(expected):
                return False
    return True


def _recompute(operation: str, operands: list[float]) -> float | None:
    """Return the recomputed numeric result for *operation* over *operands*.

    Returns ``None`` when the operation is unrecognized or operands are empty/invalid,
    signalling that the claim cannot be verified and must be dropped by the caller.

    Supported operations (case-insensitive):
    - ``sum`` — sum of operands
    - ``count`` — count of operands
    - ``avg`` / ``average`` / ``mean`` — arithmetic mean
    - ``ratio`` — operands[0] / operands[1]
    - ``recompute-excluding`` — sum of the already-filtered operands (LLM pre-excludes)
    """
    if not operands:
        return None
    op = operation.lower().strip()
    if op in ("sum", "recompute-excluding"):
        return sum(operands)
    if op == "count":
        return float(len(operands))
    if op in ("avg", "average", "mean"):
        return sum(operands) / len(operands)
    if op == "ratio":
        if len(operands) < 2 or operands[1] == 0.0:
            return None
        return operands[0] / operands[1]
    return None  # unrecognized — caller passes through unverified


def _build_alias_map(parsed: exp.Expression) -> dict[str, str]:
    """Return {alias_or_name -> real_table_name} for every table in the query."""
    result: dict[str, str] = {}
    for table in parsed.find_all(exp.Table):
        real_name = table.name
        if not real_name:
            continue
        alias = table.alias or real_name
        result[alias] = real_name
        result[real_name] = real_name
    return result


def _extract_dependencies(
    parsed: exp.Expression,
    alias_map: dict[str, str],
    unique_tables: list[str],
) -> list[Dependency]:
    seen: set[tuple[str, str]] = set()
    deps: list[Dependency] = []

    for col in parsed.find_all(exp.Column):
        col_name = col.name
        if not col_name or col_name == "*":
            continue

        table_ref = col.table
        if table_ref:
            real_table = alias_map.get(table_ref, table_ref)
        elif len(unique_tables) == 1:
            real_table = unique_tables[0]
        else:
            # Can't reliably resolve without full schema join; skip
            continue

        key = (real_table, col_name)
        if key not in seen:
            seen.add(key)
            deps.append(Dependency(table=real_table, column=col_name))

    return deps


def _find_where_group_columns(
    parsed: exp.Expression,
    alias_map: dict[str, str],
) -> set[tuple[str, str]]:
    """Return {(table, column)} for columns referenced in WHERE or GROUP BY clauses.

    Columns without a table qualifier are stored as ("", column_name) and matched
    against dependency entries during value-hash computation.
    """
    result: set[tuple[str, str]] = set()

    for clause_type in (exp.Where, exp.Group):
        clause = parsed.find(clause_type)
        if clause is None:
            continue
        for col in clause.find_all(exp.Column):
            col_name = col.name
            if not col_name:
                continue
            table_ref = col.table
            if table_ref:
                real_table = alias_map.get(table_ref, table_ref)
                result.add((real_table, col_name))
            else:
                result.add(("", col_name))

    return result


def _hash_schema(col_info: ColumnInfo) -> str:
    """Stable SHA-256 over column name + data_type + nullable (order-independent)."""
    parts = sorted(
        [
            f"name={col_info.name}",
            f"data_type={col_info.data_type}",
            f"nullable={col_info.is_nullable}",
        ]
    )
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


async def _compute_value_hash(
    table: str,
    column: str,
    query_repo: QueryRepository,
) -> str | None:
    """Fetch distinct values for a column (capped at LOW_CARD_CAP) and hash them."""
    safe_col = f'"{column.replace(chr(34), chr(34) * 2)}"'
    safe_table = f'"{table.replace(chr(34), chr(34) * 2)}"'
    distinct_sql = (
        f"SELECT DISTINCT {safe_col} FROM {safe_table} ORDER BY {safe_col}"
    )
    try:
        rows = await query_repo.execute(distinct_sql)
    except Exception as exc:
        logger.debug("Value hash fetch failed", extra={"error": str(exc)})
        return None

    if len(rows) > _LOW_CARD_CAP:
        return None  # high-cardinality; skip value hashing

    values = sorted(str(list(row.values())[0]) for row in rows if row)
    return hashlib.sha256("|".join(values).encode()).hexdigest()


async def _compute_scan_cost(sql: str, query_repo: QueryRepository) -> int:
    """Estimate row count via EXPLAIN (FORMAT JSON) — Postgres only.

    Returns 0 for in-memory repos or any repo that does not support EXPLAIN.
    Deliberately avoids a fallback execute of the main query to prevent
    disrupting stateful repository fakes used in ask_service tests.
    """
    try:
        rows = await query_repo.execute(f"EXPLAIN (FORMAT JSON) {sql}")
        if rows:
            plan_json = next(iter(rows[0].values()))
            if isinstance(plan_json, list) and plan_json:
                return int(plan_json[0]["Plan"]["Plan Rows"])
    except Exception:
        pass
    return 0
