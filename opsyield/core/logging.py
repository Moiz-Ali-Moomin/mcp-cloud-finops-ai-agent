"""
OpsYield Centralized Logging — Structured, Correlated, Production-Grade.

Usage:
    from opsyield.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("message", extra={"correlation_id": "abc-123"})

Features:
    - JSON structured output (machine-parseable)
    - Correlation ID propagation via contextvars
    - Configurable log levels per module
    - Thread-safe, async-safe
"""

import logging
import logging.config
import json
import os
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional


# ─────────────────────────────────────────────────────────────
# Correlation ID Context
# ─────────────────────────────────────────────────────────────

_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def set_correlation_id(cid: Optional[str] = None) -> str:
    """Set a correlation ID for the current context. Returns the ID."""
    cid = cid or uuid.uuid4().hex[:12]
    _correlation_id.set(cid)
    return cid


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID."""
    return _correlation_id.get()


# ─────────────────────────────────────────────────────────────
# JSON Formatter
# ─────────────────────────────────────────────────────────────

class StructuredJSONFormatter(logging.Formatter):
    """
    Emits each log record as a single-line JSON object.
    Fields: timestamp, level, logger, message, correlation_id, module, funcName, lineno
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Inject correlation ID
        cid = getattr(record, "correlation_id", None) or get_correlation_id()
        if cid:
            log_entry["correlation_id"] = cid

        # Merge any extra fields passed via `extra={}`
        for key in ("request_id", "provider", "duration_ms", "resource_count", "error_type"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val

        # Exception info
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────

_LOG_LEVEL = os.environ.get("OPSYIELD_LOG_LEVEL", "INFO").upper()
_LOG_FORMAT = os.environ.get("OPSYIELD_LOG_FORMAT", "json")  # "json" or "text"
_configured = False


def configure_logging(
    level: str = _LOG_LEVEL,
    fmt: str = _LOG_FORMAT,
    stream=None,
) -> None:
    """
    Configure logging for the entire OpsYield application.
    Call once at startup. Idempotent — subsequent calls are no-ops.
    """
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger("opsyield")
    root.setLevel(getattr(logging, level, logging.INFO))

    handler = logging.StreamHandler(stream or sys.stderr)

    if fmt == "json":
        handler.setFormatter(StructuredJSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        ))

    root.addHandler(handler)

    # Suppress noisy third-party loggers
    for noisy in ("urllib3", "httpx", "google", "botocore", "boto3", "azure"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    """
    Get a namespaced logger under the 'opsyield' hierarchy.

    Usage:
        logger = get_logger(__name__)  # e.g., 'opsyield.core.orchestrator'
    """
    configure_logging()

    # Ensure all modules log under opsyield.* namespace
    if not name.startswith("opsyield"):
        name = f"opsyield.{name}"

    return logging.getLogger(name)


class TimedOperation:
    """
    Context manager for timing operations with automatic logging.

    Usage:
        with TimedOperation(logger, "gcp_cost_fetch"):
            result = await fetch_costs()
    """

    def __init__(self, logger: logging.Logger, operation: str, **extra):
        self.logger = logger
        self.operation = operation
        self.extra = extra
        self.start = None

    def __enter__(self):
        self.start = time.perf_counter()
        self.logger.info(f"Starting: {self.operation}", extra=self.extra)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = round((time.perf_counter() - self.start) * 1000, 2)
        extras = {**self.extra, "duration_ms": duration_ms}

        if exc_type:
            extras["error_type"] = exc_type.__name__
            self.logger.error(
                f"Failed: {self.operation} ({duration_ms}ms)",
                extra=extras,
                exc_info=True,
            )
        else:
            self.logger.info(
                f"Completed: {self.operation} ({duration_ms}ms)",
                extra=extras,
            )
        return False  # Don't suppress exceptions
