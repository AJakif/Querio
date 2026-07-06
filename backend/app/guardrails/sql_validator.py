import re

from app.core.logging import get_logger


logger = get_logger("guardrails.sql_validator")

FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "EXEC", "EXECUTE", "GRANT", "REVOKE",
]


ERROR_EMPTY = "I couldn't understand that request. Please try rephrasing."
ERROR_NON_SELECT = "I can only look up data for you. Write operations aren't supported."
ERROR_FORBIDDEN_KEYWORD = "Your request would require making changes to the database, which I can't do."


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

    if "LIMIT" not in upper:
        stripped = stripped.rstrip(";") + f" LIMIT {max_rows}"
        logger.debug("Added SQL limit guardrail", extra={"max_rows": max_rows})

    logger.debug("SQL validation passed", extra={"sql_preview": stripped[:120]})
    return stripped, None
