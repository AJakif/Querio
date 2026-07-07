import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.services.ssrf_guard import SSRFError
from app.services.session_manager import SessionManager
from app.api.routes.upload import get_session_manager


CSV_CONTENT = b"city,population\nTokyo,14000000\nDelhi,32000000\n"


@pytest.fixture
def client():
    session_manager = SessionManager()
    app.dependency_overrides[get_session_manager] = lambda: session_manager

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.pop(get_session_manager, None)


class TestUrlPreviewEndpoint:
    def test_preview_from_url_returns_expected_shape(self, client: TestClient, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

        with patch("app.api.routes.upload.fetch_url") as mock_fetch:
            mock_fetch.return_value = (CSV_CONTENT, "text/csv")

            response = client.post(
                "/api/upload/preview-from-url",
                json={"url": "https://example.com/data.csv"},
            )

        assert response.status_code == 200
        body = response.json()
        assert "columns" in body
        assert "sample_rows" in body
        assert "total_rows" in body
        assert "preview_token" in body
        assert body["total_rows"] == 2
        assert len(body["columns"]) == 2

    def test_preview_from_url_parses_json_correctly(self, client: TestClient, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
        json_content = b'[{"id":1,"name":"Alice"},{"id":2,"name":"Bob"}]'

        with patch("app.api.routes.upload.fetch_url") as mock_fetch:
            mock_fetch.return_value = (json_content, "application/json")

            response = client.post(
                "/api/upload/preview-from-url",
                json={"url": "https://example.com/data.json"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["total_rows"] == 2
        col_names = [c["name"] for c in body["columns"]]
        assert "id" in col_names
        assert "name" in col_names

    def test_empty_url_returns_400(self, client: TestClient, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
        response = client.post(
            "/api/upload/preview-from-url",
            json={"url": ""},
        )
        assert response.status_code == 400

    def test_ssrf_error_propagates_as_400(self, client: TestClient, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

        with patch("app.api.routes.upload.fetch_url") as mock_fetch:
            mock_fetch.side_effect = SSRFError(
                "URL resolves to a private IP address (192.168.1.1). "
                "Only public internet URLs are allowed."
            )

            response = client.post(
                "/api/upload/preview-from-url",
                json={"url": "http://192.168.1.1/data.csv"},
            )

        assert response.status_code == 400
        assert "private" in response.json()["detail"].lower()

    def test_ssrf_blocked_ip_range(self, client: TestClient, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

        with patch("app.api.routes.upload.fetch_url") as mock_fetch:
            mock_fetch.side_effect = SSRFError(
                "URL resolves to a loopback address (127.0.0.1). "
                "Only public internet URLs are allowed."
            )

            response = client.post(
                "/api/upload/preview-from-url",
                json={"url": "http://127.0.0.1/data.csv"},
            )

        assert response.status_code == 400
        assert "loopback" in response.json()["detail"].lower()

    def test_oversized_file_rejected(self, client: TestClient, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

        with patch("app.api.routes.upload.fetch_url") as mock_fetch:
            mock_fetch.side_effect = SSRFError(
                "File too large. Maximum size is 50MB."
            )

            response = client.post(
                "/api/upload/preview-from-url",
                json={"url": "https://example.com/huge.csv"},
            )

        assert response.status_code == 400
        assert "too large" in response.json()["detail"].lower()

    def test_unsupported_content_type_rejected(self, client: TestClient, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

        with patch("app.api.routes.upload.fetch_url") as mock_fetch:
            mock_fetch.side_effect = SSRFError(
                "Unsupported content type 'application/pdf'. "
                "Only CSV and JSON files are supported."
            )

            response = client.post(
                "/api/upload/preview-from-url",
                json={"url": "https://example.com/data.pdf"},
            )

        assert response.status_code == 400
        assert "unsupported content type" in response.json()["detail"].lower()

    def test_parse_error_returns_400(self, client: TestClient, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

        with patch("app.api.routes.upload.fetch_url") as mock_fetch:
            mock_fetch.return_value = (b"a\n", "text/csv")

            response = client.post(
                "/api/upload/preview-from-url",
                json={"url": "https://example.com/empty.csv"},
            )

        assert response.status_code == 400

    def test_missing_url_field_returns_422(self, client: TestClient, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
        response = client.post(
            "/api/upload/preview-from-url",
            json={},
        )
        assert response.status_code == 422
