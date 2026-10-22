"""Observability, timing, and structured telemetry for Author-MCP."""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
import structlog

logger = structlog.get_logger("author_mcp.observability")


@contextmanager
def timed_operation(operation: str, **kwargs: Any) -> Generator[dict[str, Any], None, None]:
    """Context manager to measure and log operation latency."""
    start_time = time.perf_counter()
    info: dict[str, Any] = {"operation": operation, **kwargs}
    try:
        yield info
    finally:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        info["elapsed_ms"] = round(elapsed_ms, 2)
        logger.debug("operation_completed", **info)
