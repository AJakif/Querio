import pytest

from app.domain.models import Answer, ClarifyingQuestion, ChartSpec, ChartType, SqlQuery, Question


class TestDomainModels:
    def test_answer_can_be_created_with_just_text(self):
        a = Answer(text="42 orders found")
        assert a.text == "42 orders found"
        assert a.chart is None
        assert a.sql is None

    def test_answer_can_include_chart_and_sql(self):
        chart = ChartSpec(
            chart_type=ChartType.bar,
            title="Orders",
            data=[{"month": "Jan", "count": 10}],
            x_key="month",
            y_key="count",
        )
        sql = SqlQuery(sql="SELECT count(*) FROM orders", explanation="count all")
        a = Answer(text="42 orders", chart=chart, sql=sql)
        assert a.chart is not None
        assert a.chart.chart_type == ChartType.bar
        assert a.sql.sql == "SELECT count(*) FROM orders"

    def test_clarifying_question_has_question_and_options(self):
        q = ClarifyingQuestion(question="Which customers?", options=["by region", "by status"])
        assert q.question == "Which customers?"
        assert "by region" in q.options

    def test_chart_spec_holds_data(self):
        cs = ChartSpec(chart_type=ChartType.line, title="Trend", data=[{"x": 1, "y": 2}], x_key="x", y_key="y")
        assert cs.chart_type == ChartType.line
        assert cs.data == [{"x": 1, "y": 2}]

    def test_sql_query_holds_sql_and_explanation(self):
        sq = SqlQuery(sql="SELECT 1", explanation="test")
        assert sq.sql == "SELECT 1"
        assert sq.explanation == "test"

    def test_question_is_value_object(self):
        q = Question(text="How many?")
        assert q.text == "How many?"


class TestExceptions:
    def test_guardrail_violation_is_exception(self):
        from app.domain.exceptions import GuardrailViolation
        ex = GuardrailViolation("bad query")
        assert str(ex) == "bad query"

    def test_ambiguous_question_is_exception(self):
        from app.domain.exceptions import AmbiguousQuestion
        ex = AmbiguousQuestion("unclear")
        assert str(ex) == "unclear"
