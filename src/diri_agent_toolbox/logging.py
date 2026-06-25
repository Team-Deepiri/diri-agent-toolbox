from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
            ):
                log_data[key] = value
        return json.dumps(log_data)


class StructuredLogger:
    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.handlers = []
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        handler.setFormatter(JsonFormatter())
        self.logger.addHandler(handler)
        self.logger.propagate = False

    def _log(self, level: int, event: str, **kwargs: Any) -> None:
        extra = {"event": event, "timestamp": datetime.now(timezone.utc).isoformat()}
        extra.update(kwargs)
        self.logger.log(level, json.dumps(extra))

    def debug(self, event: str, **kwargs: Any) -> None:
        self._log(logging.DEBUG, event, **kwargs)

    def info(self, event: str, **kwargs: Any) -> None:
        self._log(logging.INFO, event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._log(logging.WARNING, event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        self._log(logging.ERROR, event, **kwargs)

    def critical(self, event: str, **kwargs: Any) -> None:
        self._log(logging.CRITICAL, event, **kwargs)


class ErrorLogger:
    def __init__(self) -> None:
        self.logger = get_logger("error_logger")

    def log_api_error(self, error: Exception, request_id: str, endpoint: str) -> None:
        self.logger.error(
            "api_error",
            error=str(error),
            error_type=type(error).__name__,
            request_id=request_id,
            endpoint=endpoint,
        )

    def log_model_error(
        self, error: Exception, model_name: str, input_data: dict | None = None
    ) -> None:
        self.logger.error(
            "model_error",
            error=str(error),
            error_type=type(error).__name__,
            model_name=model_name,
            input_sample=str(input_data)[:200] if input_data else None,
        )

    def log_training_error(
        self, error: Exception, pipeline: str, config: dict | None = None
    ) -> None:
        self.logger.error(
            "training_error",
            error=str(error),
            error_type=type(error).__name__,
            pipeline=pipeline,
            config=config,
        )


_loggers: dict[str, StructuredLogger] = {}
_error_logger: ErrorLogger | None = None


def get_logger(name: str, level: int = logging.INFO) -> StructuredLogger:
    return StructuredLogger(name, level)


def get_cached_logger(name: str) -> StructuredLogger:
    if name not in _loggers:
        _loggers[name] = get_logger(name)
    return _loggers[name]


def get_error_logger() -> ErrorLogger:
    global _error_logger
    if _error_logger is None:
        _error_logger = ErrorLogger()
    return _error_logger
