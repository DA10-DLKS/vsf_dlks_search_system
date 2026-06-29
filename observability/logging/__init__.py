"""DA10 — Structured JSON logger (§7 monitoring_plan).

Output: stdout + logs/da10.jsonl (one JSON object per line).
Usage:
    from observability.logging_setup import get_logger
    logger = get_logger()
    logger.info("", extra={"event": "search_completed", "request_id": rid, ...})
"""
from __future__ import annotations

import contextvars
import logging
import os
from datetime import datetime, timezone, timedelta
from logging.handlers import RotatingFileHandler

_VN = timezone(timedelta(hours=7))

# request_id của request hiện tại (set bởi middleware ở api/main.py). Mọi dòng log trong cùng
# request tự mang request_id này -> truy vết 1 request xuyên các stage bằng cách filter log.
_request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "da10_request_id", default=None
)


def set_request_id(rid: str | None) -> None:
    _request_id_ctx.set(rid)


def get_request_id() -> str | None:
    return _request_id_ctx.get()


def _now_iso() -> str:
    return datetime.now(_VN).strftime("%Y-%m-%dT%H:%M:%S+07:00")


class _VnJsonFormatter(logging.Formatter):
    """Minimal JSON formatter — avoids dependency on pythonjsonlogger field ordering."""

    def format(self, record: logging.LogRecord) -> str:
        import json

        base = {
            "timestamp": _now_iso(),
            "level": record.levelname,
        }
        rid = _request_id_ctx.get()
        if rid:
            base["request_id"] = rid
        # Merge extra fields (from logger.info("", extra={...}))
        skip = {
            "name", "msg", "args", "created", "filename", "funcName",
            "levelname", "levelno", "lineno", "module", "msecs",
            "pathname", "process", "processName", "relativeCreated",
            "stack_info", "thread", "threadName", "exc_info", "exc_text",
            "message", "taskName",  # taskName: thuộc tính LogRecord thêm từ Python 3.12 -> lọc bỏ
        }
        for k, v in record.__dict__.items():
            if k not in skip:
                base[k] = v

        if record.getMessage():
            base.setdefault("message", record.getMessage())

        return json.dumps(base, ensure_ascii=False, default=str)


_logger: logging.Logger | None = None


def get_logger(name: str = "da10") -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        _logger = logger
        return logger

    fmt = _VnJsonFormatter()

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    os.makedirs("logs", exist_ok=True)
    # RotatingFileHandler: chặn logs/da10.jsonl phình vô hạn (10MB x 5 file = ~50MB trần).
    fh = RotatingFileHandler(
        "logs/da10.jsonl", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    _logger = logger
    return logger
