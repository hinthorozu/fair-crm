"""HTTP request duration middleware."""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.performance_monitoring import active_background_job_count, log_pool_status
from app.db.session import engine

logger = logging.getLogger("fair_crm.performance")


class RequestTimingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, slow_request_ms: float) -> None:
        super().__init__(app)
        self._slow_request_ms = slow_request_ms

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        path = request.url.path
        if duration_ms >= self._slow_request_ms:
            log_pool_status(engine)
            logger.warning(
                "slow_request method=%s path=%s status=%s duration_ms=%.2f active_background_jobs=%s",
                request.method,
                path,
                response.status_code,
                duration_ms,
                active_background_job_count(),
            )
        elif path != "/health":
            logger.info(
                "request method=%s path=%s status=%s duration_ms=%.2f",
                request.method,
                path,
                response.status_code,
                duration_ms,
            )
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
        return response
