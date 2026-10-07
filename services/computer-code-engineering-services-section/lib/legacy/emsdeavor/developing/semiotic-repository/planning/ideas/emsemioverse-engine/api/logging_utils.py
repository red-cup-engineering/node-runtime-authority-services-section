"""Logging helpers for request and audit events."""

from __future__ import annotations

import logging
import uuid
import time
from typing import Callable, Awaitable

from fastapi import Request

logger = logging.getLogger(__name__)


async def request_logger(request: Request, call_next: Callable[..., Awaitable]):
    """Middleware-style logger that emits correlation IDs."""
    req_id = str(uuid.uuid4())
    start = time.monotonic()
    request.state.request_id = req_id
    logger.info("req %s %s %s", req_id, request.method, request.url.path)
    response = await call_next(request)
    duration_ms = (time.monotonic() - start) * 1000
    response.headers["X-Request-ID"] = req_id
    logger.info("res %s %s %s %.2fms %s", req_id, request.method, request.url.path, duration_ms, response.status_code)
    return response
