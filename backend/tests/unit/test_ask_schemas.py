from app.schemas.ask import (
    AskRequest,
    AnswerResponse,
    AnswerSpecResponse,
    ChartSpecResponse,
    ClarifyingQuestionResponse,
    HeadlineResponse,
    SqlQueryResponse,
)


class TestAskRequest:
    def test_ask_request_has_question(self):
        req = AskRequest(question="How many orders?")
        assert req.question == "How many orders?"

    def test_ask_request_can_include_clarification_answer(self):
        req = AskRequest(question="customers", conversation_id="abc-123", clarification_answer="count")
        assert req.conversation_id == "abc-123"
        assert req.clarification_answer == "count"

    def test_ask_request_clarification_fields_default_to_none(self):
        req = AskRequest(question="How many orders?")
        assert req.conversation_id is None
        assert req.clarification_answer is None


class TestAnswerResponse:
    def test_answer_response_default_type(self):
        resp = AnswerResponse(answer="42 orders")
        assert resp.type == "answer"
        assert resp.answer == "42 orders"
        assert resp.chart is None
        assert resp.sql is None
        assert resp.conversation_id is None

    def test_answer_response_with_chart_and_sql(self):
        chart = ChartSpecResponse(chart_type="bar", title="O", data=[{"x": 1}], x_key="x", y_key="y")
        sql = SqlQueryResponse(sql="SELECT 1", explanation="test")
        resp = AnswerResponse(answer="result", chart=chart, sql=sql)
        assert resp.chart.chart_type == "bar"
        assert resp.sql.sql == "SELECT 1"

    def test_answer_response_serializes_to_json(self):
        resp = AnswerResponse(answer="hello")
        d = resp.model_dump()
        assert d["type"] == "answer"
        assert d["answer"] == "hello"
        assert d["chart"] is None
        assert d["sql"] is None
        assert d["conversation_id"] is None
        assert d["plan"] is None
        assert d["validation"] is None
        assert d["answer_spec"] is None
        assert d["dropped_claim_count"] == 0
        assert d["result_rows"] is None

    def test_answer_response_can_include_conversation_id(self):
        resp = AnswerResponse(answer="result", conversation_id="conv-1")
        assert resp.conversation_id == "conv-1"


# ---------------------------------------------------------------------------
# BUG-2 regression — emphasis_target / y_keys dropped by serialization layer
# ---------------------------------------------------------------------------


def test_chart_spec_response_emphasis_target_and_y_keys_survive_serialization():
    """Regression: ChartSpecModel had emphasis_target/y_keys but ChartSpecResponse and
    the route builder didn't.  These fields must survive the full
    contracts -> schema -> model_dump() path so the frontend can use them.
    """
    chart = ChartSpecResponse(
        chart_type="bar",
        title="Revenue by region",
        data=[{"region": "North", "revenue": 100}],
        x_key="region",
        y_key="revenue",
        emphasis_target="North",
        y_keys=None,
    )
    d = chart.model_dump()
    assert d["emphasis_target"] == "North"
    assert d["y_keys"] is None

    # Also verify y_keys round-trips for stacked_bar
    stacked = ChartSpecResponse(
        chart_type="stacked_bar",
        title="Sales by region and category",
        data=[],
        x_key="region",
        y_key="electronics",
        y_keys=["electronics", "apparel"],
    )
    assert stacked.model_dump()["y_keys"] == ["electronics", "apparel"]


# ---------------------------------------------------------------------------
# GAP-1 regression — response_type absent from AnswerSpec contract
# ---------------------------------------------------------------------------


def test_answer_spec_response_type_defaults_stat_and_accepts_chart():
    """Regression: AnswerSpecResponse had no response_type field — frontend had to
    infer routing from chart_spec presence, which is fragile.  The field must now
    default to 'stat' and survive round-trip serialization.
    """
    headline = HeadlineResponse(value="42", label="total orders")
    stat_spec = AnswerSpecResponse(headline=headline, restatement="There are 42 orders.")
    assert stat_spec.response_type == "stat"
    assert stat_spec.model_dump()["response_type"] == "stat"

    chart_spec_data = ChartSpecResponse(
        chart_type="bar", title="T", data=[], x_key="x", y_key="y"
    )
    chart_spec = AnswerSpecResponse(
        response_type="chart",
        headline=headline,
        restatement="Chart of orders by region.",
        chart_spec=chart_spec_data,
    )
    assert chart_spec.model_dump()["response_type"] == "chart"


class TestClarifyingQuestionResponse:
    def test_clarifying_question_default_type(self):
        resp = ClarifyingQuestionResponse(question="Which?", options=["a", "b"])
        assert resp.type == "clarifying_question"
        assert resp.question == "Which?"
        assert resp.options == ["a", "b"]
        assert resp.conversation_id is not None
        assert len(resp.conversation_id) > 0

    def test_clarifying_question_empty_options(self):
        resp = ClarifyingQuestionResponse(question="Which?")
        assert resp.options == []
        assert resp.conversation_id is not None
