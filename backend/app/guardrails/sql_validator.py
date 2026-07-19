import re

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError, SqlglotError

from app.core.logging import get_logger


logger = get_logger("guardrails.sql_validator")

FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "EXEC", "EXECUTE", "GRANT", "REVOKE",
]


ERROR_EMPTY = "I couldn't understand that request. Please try rephrasing."
ERROR_NON_SELECT = "I can only look up data for you. Write operations aren't supported."
ERROR_FORBIDDEN_KEYWORD = "Your request would require making changes to the database, which I can't do."


def _apply_limit_cap(sql: str, max_rows: int) -> str:
    """Enforce max_rows on the outermost query LIMIT via AST rewrite.

    Falls back to string-append when sqlglot cannot parse the SQL, so
    unparseable queries never bypass the row cap.
    """
    try:
        statements = sqlglot.parse(sql, dialect="postgres", error_level=sqlglot.ErrorLevel.RAISE)
        if not statements or statements[0] is None:
            raise ParseError("empty parse result")

        stmt = statements[0]
        limit_node: exp.Expression | None = stmt.args.get("limit")

        if limit_node is None:
            stmt.set("limit", exp.Limit(expression=exp.Literal.number(max_rows)))
            logger.debug("Added SQL limit guardrail via AST", extra={"max_rows": max_rows})
        else:
            limit_expr: exp.Expression | None = limit_node.args.get("expression")
            if isinstance(limit_expr, exp.Literal) and limit_expr.is_number:
                current_limit = int(limit_expr.this)
                if current_limit > max_rows:
                    limit_node.set("expression", exp.Literal.number(max_rows))
                    logger.debug(
                        "Capped SQL limit guardrail via AST",
                        extra={"original_limit": current_limit, "max_rows": max_rows},
                    )

        return stmt.sql(dialect="postgres")

    except SqlglotError:
        # Fallback for unparseable SQL: string-based cap so row limit is never bypassed.
        if "LIMIT" not in sql.upper():
            logger.debug("Added SQL limit guardrail via string fallback", extra={"max_rows": max_rows})
            return sql.rstrip(";") + f" LIMIT {max_rows}"
        return sql


def validate_sql(sql: str, max_rows: int = 1000) -> tuple[str | None, str | None]:
    stripped = sql.strip()
    if not stripped:
        logger.warning("SQL validation failed: empty query")
        return None, ERROR_EMPTY

    upper = stripped.upper().strip().rstrip(";")

    if not upper.startswith("SELECT"):
        logger.warning("SQL validation failed: non-select query", extra={"sql_preview": stripped[:120]})
        return None, ERROR_NON_SELECT

    no_strings = re.sub(r"'[^']*'", "", upper)

    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf'\b{keyword}\b', no_strings):
            logger.warning(
                "SQL validation failed: forbidden keyword",
                extra={"keyword": keyword, "sql_preview": stripped[:120]},
            )
            return None, ERROR_FORBIDDEN_KEYWORD

    rewritten = _apply_limit_cap(stripped, max_rows)

    logger.debug("SQL validation passed", extra={"sql_preview": rewritten[:120]})
    return rewritten, None
