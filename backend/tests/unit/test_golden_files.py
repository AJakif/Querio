from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.csv_ingestion import parse_csv, parse_json
from app.services.session_manager import SessionManager
from app.api.routes.upload import get_session_manager


FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _read_fixture(name: str) -> bytes:
    path = FIXTURES_DIR / name
    with open(path, "rb") as f:
        return f.read()


class TestCsvGoldenFiles:
    def test_bom_utf8_csv(self):
        content = _read_fixture("bom_utf8.csv")
        result = parse_csv(content)
        assert result.total_rows == 2
        col_names = [c.name for c in result.columns]
        assert col_names == ["name", "age"]

    def test_windows_crlf_csv(self):
        content = _read_fixture("windows_crlf.csv")
        result = parse_csv(content)
        assert result.total_rows == 2
        col_names = [c.name for c in result.columns]
        assert col_names == ["name", "age"]

    def test_quoted_commas_csv(self):
        content = _read_fixture("quoted_commas.csv")
        result = parse_csv(content)
        assert result.total_rows == 2
        col_names = [c.name for c in result.columns]
        assert "name" in col_names
        assert "description" in col_names
        row0 = result.all_rows[0]
        assert row0["description"] == "loves cats, dogs, and birds"

    def test_mostly_null_csv(self):
        content = _read_fixture("mostly_null.csv")
        result = parse_csv(content)
        assert result.total_rows == 10
        col_map = {c.name: c for c in result.columns}
        value_col = col_map["value"]
        assert value_col.stats["null_percentage"] >= 70.0

    def test_empty_csv(self):
        content = _read_fixture("empty.csv")
        with pytest.raises(ValueError) as exc:
            parse_csv(content)
        assert "no column" in str(exc.value).lower() or "no data" in str(exc.value).lower()

    def test_empty_json(self):
        content = _read_fixture("empty.json")
        with pytest.raises(ValueError):
            parse_json(content)


class TestJsonGoldenFiles:
    def test_flat_json_array(self):
        content = _read_fixture("flat_array.json")
        result = parse_json(content)
        assert result.total_rows == 2
        col_names = [c.name for c in result.columns]
        assert col_names == ["id", "name"]

    def test_nested_one_level_json(self):
        content = _read_fixture("nested_one_level.json")
        result = parse_json(content)
        assert result.total_rows == 1
        col_names = [c.name for c in result.columns]
        assert "id" in col_names
        assert "customer_name" in col_names
        assert "customer_age" in col_names
        assert "customer" not in col_names

    def test_nested_two_levels_json_rejected(self):
        content = _read_fixture("nested_two_levels.json")
        with pytest.raises(ValueError) as exc:
            parse_json(content)
        assert "more than one level deep" in str(exc.value).lower()


class TestOversizedFile:
    @pytest.fixture
    def client(self):
        session_manager = SessionManager()
        app.dependency_overrides[get_session_manager] = lambda: session_manager
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.pop(get_session_manager, None)

    def test_oversized_csv_rejected_via_api(self, client, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

        import app.api.routes.upload as upload_route
        monkeypatch.setattr(upload_route, "MAX_UPLOAD_SIZE", 50)

        oversized = b"a,b\n" * 20
        assert len(oversized) > 50

        response = client.post(
            "/api/upload/preview",
            files={"file": ("large.csv", oversized, "text/csv")},
        )

        assert response.status_code == 400
        assert "too large" in response.json()["detail"].lower()
