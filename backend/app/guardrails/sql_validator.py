import re

FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "EXEC", "EXECUTE", "GRANT", "REVOKE",
]

TOP_LEVEL_ONLY = ["SELECT"]


def validate_sql(sql: str, max_rows: int = 1000) -> tuple[str | None, str | None]:
    stripped = sql.strip()
    if not stripped:
        return None, "Empty SQL statement."

    upper = stripped.upper().strip().rstrip(";")

    if not any(upper.startswith(kw) for kw in TOP_LEVEL_ONLY):
        return None, "Only SELECT queries are allowed."

    no_strings = re.sub(r"'[^']*'", "", upper)

    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in ("SELECT",):
            continue
        if re.search(rf'\b{keyword}\b', no_strings):
            return None, f"Query contains forbidden keyword: {keyword}."

    if "LIMIT" not in upper:
        stripped = stripped.rstrip(";") + f" LIMIT {max_rows}"

    return stripped, None
