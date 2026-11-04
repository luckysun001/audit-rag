"""结构化日志工具单元测试（纯标准库，无第三方依赖）。"""

import logging

from bank_audit_rag.utils.logger import (
    LoggingContext,
    RequestLogger,
    StructuredFormatter,
    Timer,
    configure_logging,
)


def test_structured_formatter_basic():
    fmt = StructuredFormatter()
    record = logging.LogRecord("mod", logging.INFO, "path", 1, "hello", None, None)
    out = fmt.format(record)
    assert "hello" in out
    assert "INFO" in out
    # record.module 取自 pathname 而非 logger 名称
    assert "path" in out


def test_structured_formatter_extra_field():
    fmt = StructuredFormatter()
    record = logging.LogRecord("mod", logging.INFO, "path", 1, "msg", None, None)
    record.custom_field = "v1"
    out = fmt.format(record)
    assert "custom_field=v1" in out


def test_structured_formatter_exception():
    fmt = StructuredFormatter()
    import sys

    try:
        raise ValueError("boom")
    except ValueError:
        exc_info = sys.exc_info()
    record = logging.LogRecord("mod", logging.ERROR, "path", 1, "err", None, exc_info)
    out = fmt.format(record)
    assert "boom" in out
    assert "ValueError" in out


def test_timer_context():
    with Timer("op") as t:
        pass
    assert t.elapsed is not None
    assert t.elapsed >= 0


def test_logging_context_injects_field():
    captured = {}

    class H(logging.Handler):
        def emit(self, record):
            captured["request_id"] = getattr(record, "request_id", None)

    root = logging.getLogger()
    root.addHandler(H())
    root.setLevel(logging.INFO)
    try:
        with LoggingContext(request_id="r-99"):
            logging.getLogger("x").info("hi")
    finally:
        root.removeHandler(root.handlers[-1])
    assert captured.get("request_id") == "r-99"


def test_request_logger_no_crash():
    rl = RequestLogger("req-1")
    rl.log_request("GET", "/x")
    rl.log_response(200)
    rl.log_error("boom")
    assert True


def test_configure_logging_no_crash():
    configure_logging(level="DEBUG", format_type="structured", log_file=None)
    configure_logging(level="INFO", format_type="plain")
    assert True
