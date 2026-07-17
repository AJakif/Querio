from app.schemas.ask import AskRequest, AnswerResponse, ClarifyingQuestionResponse, ChartSpecResponse, SqlQueryResponse


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
        assert d == {
            "type": "answer",
            "answer": "hello",
            "chart": None,
            "sql": None,
            "conversation_id": None,
            "plan": None,
            "validation": None,
            "answer_spec": None,
            "dropped_claim_count": 0,
        }

    def test_answer_response_can_include_conversation_id(self):
        resp = AnswerResponse(answer="result", conversation_id="conv-1")
        assert resp.conversation_id == "conv-1"


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
