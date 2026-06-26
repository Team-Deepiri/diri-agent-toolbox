import json
import logging

from diri_agent_toolbox.logging import (
    ErrorLogger,
    JsonFormatter,
    StructuredLogger,
    get_error_logger,
    get_logger,
)


def test_json_formatter():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="hello",
        args=None,
        exc_info=None,
    )
    output = formatter.format(record)
    data = json.loads(output)
    assert data["level"] == "INFO"
    assert data["logger"] == "test"
    assert data["message"] == "hello"
    assert "timestamp" in data


def test_json_formatter_with_extras():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.WARNING,
        pathname="",
        lineno=0,
        msg="warn",
        args=None,
        exc_info=None,
    )
    record.custom_field = "custom_val"
    output = formatter.format(record)
    data = json.loads(output)
    assert data["custom_field"] == "custom_val"


def test_structured_logger_info(capsys):
    logger = get_logger("test_logger")
    logger.info("my_event", key="value")
    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    # StructuredLogger._log passes json.dumps(extra) as the message,
    # so event is inside the message field as a JSON string
    msg = json.loads(data["message"])
    assert msg["event"] == "my_event"
    assert msg["key"] == "value"


def test_structured_logger_levels(capsys):
    logger = StructuredLogger("test_levels", level=logging.DEBUG)
    logger.debug("debug_event")
    logger.info("info_event")
    logger.warning("warn_event")
    logger.error("err_event")
    logger.critical("crit_event")
    captured = capsys.readouterr()
    lines = [json.loads(line) for line in captured.out.strip().split("\n") if line]
    messages = [json.loads(ln["message"]) for ln in lines]
    events = [m["event"] for m in messages]
    assert "info_event" in events
    assert "warn_event" in events
    assert "err_event" in events
    assert "crit_event" in events


def test_error_logger_api_error(capsys):
    el = ErrorLogger()
    el.log_api_error(ValueError("bad request"), request_id="req-1", endpoint="/api/v1/test")
    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    msg = json.loads(data["message"])
    assert msg["event"] == "api_error"
    assert msg["request_id"] == "req-1"
    assert msg["endpoint"] == "/api/v1/test"


def test_error_logger_model_error(capsys):
    el = ErrorLogger()
    el.log_model_error(RuntimeError("oom"), model_name="bert", input_data={"text": "hello"})
    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    msg = json.loads(data["message"])
    assert msg["event"] == "model_error"
    assert msg["model_name"] == "bert"


def test_error_logger_training_error(capsys):
    el = ErrorLogger()
    el.log_training_error(TimeoutError("slow"), pipeline="train_pipe", config={"lr": 0.01})
    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    msg = json.loads(data["message"])
    assert msg["event"] == "training_error"
    assert msg["pipeline"] == "train_pipe"
    assert msg["config"] == {"lr": 0.01}


def test_get_error_logger_singleton():
    el1 = get_error_logger()
    el2 = get_error_logger()
    assert el1 is el2
