from fastapi.testclient import TestClient


class TestAskEndpoint:
    def test_post_ask_returns_answer_shape(self, client: TestClient):
        response = client.post("/api/ask", json={"question": "How many orders?"})
        assert response.status_code == 200
        body = response.json()
        assert body["type"] == "answer"
        assert "answer" in body
        assert isinstance(body["answer"], str)
        assert len(body["answer"]) > 0

    def test_post_ask_sql_is_optional(self, client: TestClient):
        response = client.post("/api/ask", json={"question": "anything"})
        assert response.status_code == 200
        body = response.json()
        assert "sql" in body

    def test_post_ask_chart_is_optional(self, client: TestClient):
        response = client.post("/api/ask", json={"question": "anything"})
        assert response.status_code == 200
        body = response.json()
        assert "chart" in body

    def test_health_returns_ok(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
