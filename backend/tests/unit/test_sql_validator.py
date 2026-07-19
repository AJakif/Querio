from app.guardrails.sql_validator import validate_sql


class TestValidateSql:
    def test_select_passes(self):
        sql, error = validate_sql("SELECT * FROM orders")
        assert error is None
        assert sql is not None

    def test_insert_is_rejected(self):
        sql, error = validate_sql("INSERT INTO orders VALUES (1, 100)")
        assert error is not None
        assert sql is None

    def test_drop_is_rejected(self):
        sql, error = validate_sql("DROP TABLE orders")
        assert error is not None
        assert sql is None

    def test_delete_is_rejected(self):
        sql, error = validate_sql("DELETE FROM orders WHERE id = 1")
        assert error is not None
        assert sql is None

    def test_update_is_rejected(self):
        sql, error = validate_sql("UPDATE orders SET status = 'shipped'")
        assert error is not None
        assert sql is None

    def test_empty_sql_is_rejected(self):
        sql, error = validate_sql("")
        assert error is not None
        assert sql is None

    def test_limit_is_applied_when_missing(self):
        sql, error = validate_sql("SELECT * FROM orders", max_rows=100)
        assert error is None
        assert "LIMIT 100" in sql

    def test_existing_limit_is_not_duplicated(self):
        sql, error = validate_sql("SELECT * FROM orders LIMIT 5")
        assert error is None
        assert "LIMIT 5" in sql

    def test_forbidden_keyword_in_string_literal_allowed(self):
        sql, error = validate_sql("SELECT * FROM orders WHERE name = 'DROP table'")
        assert error is None

    def test_exec_is_rejected(self):
        sql, error = validate_sql("EXEC sp_help")
        assert error is not None
        assert sql is None

    def test_non_select_error_is_friendly(self):
        _, error = validate_sql("DROP TABLE orders")
        assert error is not None
        assert "SELECT" not in error.upper()
        assert "SQL" not in error.upper()
        assert "keyword" not in error.lower()
        assert "query" not in error.lower()
        assert len(error) > 10

    def test_oversized_limit_is_capped(self):
        sql, error = validate_sql("SELECT * FROM orders LIMIT 500000", max_rows=1000)
        assert error is None
        assert "LIMIT 1000" in sql
        assert "500000" not in sql

    def test_limit_with_offset_offset_preserved(self):
        sql, error = validate_sql("SELECT * FROM orders LIMIT 500000 OFFSET 20", max_rows=1000)
        assert error is None
        assert "LIMIT 1000" in sql
        assert "OFFSET 20" in sql

    def test_subquery_limit_is_not_capped(self):
        # Outer query has no LIMIT; subquery has LIMIT 999999 — only outer is capped/added.
        sql, error = validate_sql(
            "SELECT * FROM (SELECT * FROM orders LIMIT 999999) sub",
            max_rows=1000,
        )
        assert error is None
        assert "LIMIT 1000" in sql
        assert "999999" in sql

    def test_forbidden_keyword_error_is_friendly(self):
        _, error = validate_sql("SELECT * FROM orders; DROP TABLE customers")
        assert error is not None
        assert "forbidden" not in error.lower()
        assert "keyword" not in error.lower()
        assert "SQL" not in error.upper()
        assert len(error) > 10
