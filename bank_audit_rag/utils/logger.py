"""
日志工具模块
提供结构化日志、请求日志、计时器等功能
"""

import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional


# ============================================================================
# 根日志配置
# ============================================================================

class StructuredFormatter(logging.Formatter):
    """结构化日志格式器"""

    def format(self, record: logging.LogRecord) -> str:
        # 基础信息
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }

        # 合并额外字段
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "asctime", "taskName",
            }:
                log_data[key] = value

        # 异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 构建日志行
        extra_str = " ".join(f"{k}={v}" for k, v in log_data.items()
                             if k not in ("timestamp", "level", "module", "message"))
        base = f"[{log_data['timestamp']}] {log_data['level']} {log_data['module']}: {log_data['message']}"
        if extra_str:
            base += f" | {extra_str}"
        if "exception" in log_data:
            base += f"\n{log_data['exception']}"
        return base


def configure_logging(
    level: str = "INFO",
    format_type: str = "structured",
    log_file: Optional[str] = None,
) -> None:
    """
    配置全局日志

    Args:
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        format_type: 格式类型 (structured/plain)
        log_file: 日志文件路径（可选）
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 清除现有 handler
    root.handlers.clear()

    # 控制台 handler
    console_handler = logging.StreamHandler()
    if format_type == "structured":
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
    root.addHandler(console_handler)

    # 文件 handler
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(StructuredFormatter())
        root.addHandler(file_handler)


# 根日志器
root_logger = logging.getLogger("bank_audit_rag")


def get_logger(name: str = "bank_audit_rag") -> logging.Logger:
    """获取日志器实例"""
    return logging.getLogger(name)


# ============================================================================
# 辅助工具
# ============================================================================

class Timer:
    """计时器工具"""

    def __init__(self, name: str = "", logger: Optional[logging.Logger] = None):
        self.name = name
        self.logger = logger or get_logger()
        self.start_time: Optional[float] = None
        self.elapsed: Optional[float] = None

    def __enter__(self) -> "Timer":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.elapsed = time.perf_counter() - self.start_time
        if self.name:
            self.logger.info(f"{self.name} completed in {self.elapsed:.3f}s")


class LoggingContext:
    """日志上下文管理器，为日志添加额外字段"""

    def __init__(self, **kwargs: Any):
        self.context = kwargs
        self._old_factory: Optional[Any] = None

    def __enter__(self) -> "LoggingContext":
        old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)
        self._old_factory = old_factory
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._old_factory is not None:
            logging.setLogRecordFactory(self._old_factory)


class RequestLogger:
    """请求日志器，记录请求的完整生命周期"""

    def __init__(self, request_id: str, logger: Optional[logging.Logger] = None):
        self.request_id = request_id
        self.logger = logger or get_logger()
        self.start_time = time.perf_counter()

    def log_request(self, method: str, path: str, **kwargs: Any) -> None:
        """记录请求开始"""
        self.logger.info(
            "request_started",
            extra={"request_id": self.request_id, "method": method, "path": path, **kwargs},
        )

    def log_response(self, status_code: int, **kwargs: Any) -> None:
        """记录请求完成"""
        elapsed = time.perf_counter() - self.start_time
        self.logger.info(
            "request_completed",
            extra={
                "request_id": self.request_id,
                "status_code": status_code,
                "elapsed_ms": round(elapsed * 1000, 2),
                **kwargs,
            },
        )

    def log_error(self, error: str, **kwargs: Any) -> None:
        """记录请求错误"""
        elapsed = time.perf_counter() - self.start_time
        self.logger.error(
            "request_error",
            extra={
                "request_id": self.request_id,
                "error": error,
                "elapsed_ms": round(elapsed * 1000, 2),
                **kwargs,
            },
        )


# ============================================================================
# 初始化默认配置
# ============================================================================

if not root_logger.handlers:
    configure_logging()
