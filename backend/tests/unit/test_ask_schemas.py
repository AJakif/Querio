from app.schemas.ask import AskRequest, AnswerResponse, ClarifyingQuestionResponse, ChartSpecResponse, SqlQueryResponse


class TestAskRequest:
    def test_ask_request_has_question(self):
        req = AskRequest(question="How many orders?")
        assert req.question == "How many orders?"


class TestAnswerResponse:
    def test_answer_response_default_type(self):
        resp = AnswerResponse(answer="42 orders")
        assert resp.type == "answer"
        assert resp.answer == "42 orders"
        assert resp.chart is None
        assert resp.sql is None

    def test_answer_response_with_chart_and_sql(self):
        chart = ChartSpecResponse(chart_type="bar", title="O", data=[{"x": 1}], x_key="x", y_key="y")
        sql = SqlQueryResponse(sql="SELECT 1", explanation="test")
        resp = AnswerResponse(answer="result", chart=chart, sql=sql)
        assert resp.chart.chart_type == "bar"
        assert resp.sql.sql == "SELECT 1"

    def test_answer_response_serializes_to_json(self):
        resp = AnswerResponse(answer="hello")
        d = resp.model_dump()
        assert d == {"type": "answer", "answer": "hello", "chart": None, "sql": None}


class TestClarifyingQuestionResponse:
    def test_clarifying_question_default_type(self):
        resp = ClarifyingQuestionResponse(question="Which?", options=["a", "b"])
        assert resp.type == "clarifying_question"
        assert resp.question == "Which?"
        assert resp.options == ["a", "b"]

    def test_clarifying_question_empty_options(self):
        resp = ClarifyingQuestionResponse(question="Which?")
        assert resp.options == []
