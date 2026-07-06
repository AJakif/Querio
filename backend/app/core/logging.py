import json
import logging
import logging.config
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import Settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "file_name": record.filename,
            "line_number": record.lineno,
            "function_name": record.funcName,
        }
        payload.update(_extra_fields(record))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


class DevFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extra = _extra_fields(record)
        if not extra:
            return base
        details = " ".join(f"{key}={value!r}" for key, value in sorted(extra.items()))
        return f"{base} | {details}"


def configure_logging(settings: Settings, log_dir: Path | None = None) -> logging.Logger:
    formatter_name = "json" if settings.normalized_app_env == "prod" else "dev"
    target_log_dir = log_dir or _default_log_dir()
    target_log_dir.mkdir(parents=True, exist_ok=True)
    log_file = target_log_dir / "querio.log"

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {"()": "app.core.logging.JsonFormatter"},
                "dev": {"()": "app.core.logging.DevFormatter"},
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": formatter_name,
                    "stream": "ext://sys.stdout",
                },
                "file": {
                    "class": "logging.FileHandler",
                    "formatter": formatter_name,
                    "filename": str(log_file),
                    "encoding": "utf-8",
                }
            },
            "root": {
                "level": settings.effective_log_level,
                "handlers": ["console", "file"],
            },
        }
    )

    logger = logging.getLogger("querio")
    logger.debug(
        "Logging configured",
        extra={
            "app_env": settings.normalized_app_env,
            "log_level": settings.effective_log_level,
            "log_file": str(log_file),
        },
    )
    return logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"querio.{name}")


def _default_log_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "logs"


def _extra_fields(record: logging.LogRecord) -> dict[str, object]:
    standard_fields = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
    }
    return {
        key: value
        for key, value in record.__dict__.items()
        if key not in standard_fields and not key.startswith("_")
    }
