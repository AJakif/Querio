import pytest
from fastapi.testclient import TestClient


class TestAskRouteWiring:
    def test_post_ask_returns_answer_shape(self, client: TestClient):
        response = client.post("/api/ask", json={"question": "How many orders are there?"})
        assert response.status_code == 200
        body = response.json()
        assert body["type"] == "answer"
        assert "answer" in body
        assert isinstance(body["answer"], str)
        assert len(body["answer"]) > 0

    def test_post_ask_returns_chart(self, client: TestClient):
        response = client.post("/api/ask", json={"question": "anything"})
        assert response.status_code == 200
        body = response.json()
        assert body["chart"] is not None
        assert body["chart"]["chart_type"] == "bar"
        assert body["chart"]["title"] == "Orders Overview"
        assert len(body["chart"]["data"]) > 0
        assert "x_key" in body["chart"]
        assert "y_key" in body["chart"]

    def test_post_ask_returns_sql(self, client: TestClient):
        response = client.post("/api/ask", json={"question": "Show me orders"})
        assert response.status_code == 200
        body = response.json()
        assert body["sql"] is not None
        assert "sql" in body["sql"]
        assert "explanation" in body["sql"]

    def test_post_ask_empty_question(self, client: TestClient):
        response = client.post("/api/ask", json={"question": ""})
        assert response.status_code == 200

    def test_health_returns_ok(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
