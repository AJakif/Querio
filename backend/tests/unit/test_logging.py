import io
import json
import logging
from pathlib import Path

from app.core.config import Settings
from app.core.logging import DevFormatter, JsonFormatter, configure_logging


def test_dev_logging_uses_debug_and_human_readable_format():
    logger = configure_logging(Settings(app_env="dev"))
    root_handler = logging.getLogger().handlers[0]

    assert logging.getLogger().level == logging.DEBUG
    assert isinstance(root_handler.formatter, DevFormatter)
    assert logger.name == "querio"


def test_prod_logging_uses_info_and_json_format():
    logger = configure_logging(Settings(app_env="production"))
    root_handler = logging.getLogger().handlers[0]

    assert logging.getLogger().level == logging.INFO
    assert isinstance(root_handler.formatter, JsonFormatter)
    assert logger.name == "querio"


def test_json_formatter_serializes_extra_fields():
    formatter = JsonFormatter()
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(formatter)

    logger = logging.getLogger("test.json")
    logger.handlers = []
    logger.propagate = False
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    logger.info("hello", extra={"conversation_id": "abc123"})

    payload = json.loads(stream.getvalue().strip())
    assert payload["message"] == "hello"
    assert payload["conversation_id"] == "abc123"


def test_configure_logging_creates_log_file(tmp_path: Path):
    log_dir = tmp_path / "logs"
    logger = configure_logging(Settings(app_env="dev"), log_dir=log_dir)

    logger.info("written to file", extra={"request_id": "req-1"})

    log_file = log_dir / "querio.log"
    assert log_file.exists()
    contents = log_file.read_text(encoding="utf-8")
    assert "written to file" in contents
