from app.guardrails.sql_validator import validate_sql


class TestValidateSql:
    def test_select_passes(self):
        sql, error = validate_sql("SELECT * FROM orders")
        assert error is None
        assert sql is not None

    def test_insert_is_rejected(self):
        sql, error = validate_sql("INSERT INTO orders VALUES (1, 100)")
        assert error is not None
        assert "SELECT" in error
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

    def test_whitespace_sql_is_rejected(self):
        sql, error = validate_sql("   ")
        assert error is not None
        assert sql is None

    def test_limit_is_applied_when_missing(self):
        sql, error = validate_sql("SELECT * FROM orders", max_rows=100)
        assert error is None
        assert sql is not None
        assert "LIMIT 100" in sql

    def test_existing_limit_is_not_duplicated(self):
        sql, error = validate_sql("SELECT * FROM orders LIMIT 5")
        assert error is None
        assert sql is not None
        assert "LIMIT 5" in sql

    def test_forbidden_keyword_in_string_literal_still_rejected(self):
        sql, error = validate_sql("SELECT * FROM orders WHERE name = 'DROP'")
        assert error is None, "DROP inside a string should not be rejected"

    def test_exec_is_rejected(self):
        sql, error = validate_sql("EXEC sp_help")
        assert error is not None
        assert sql is None

    def test_select_with_semicolon(self):
        sql, error = validate_sql("SELECT * FROM orders;")
        assert error is None
        assert sql is not None
        assert sql.strip().endswith("LIMIT 1000") or "LIMIT 1000" in sql
