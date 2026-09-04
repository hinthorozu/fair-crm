"""Run blocking work from Starlette BackgroundTasks without freezing the API event loop."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import TypeVar
from uuid import UUID

from starlette.concurrency import run_in_threadpool

from app.core.performance_monitoring import (
    register_background_job_finished,
    register_background_job_started,
)
from app.shared.queued_work_lifecycle import should_execute_queued_product_work

logger = logging.getLogger("fair_crm.performance")

T = TypeVar("T")

# When True (pytest), run detached jobs inline so request-scoped test sessions stay valid.
_detached_jobs_inline = False


def configure_detached_jobs_inline(enabled: bool) -> None:
    global _detached_jobs_inline
    _detached_jobs_inline = enabled


def _operation_label(func: Callable[..., T], args: tuple) -> tuple[str, str | None]:
    name = getattr(func, "__name__", func.__class__.__name__)
    run_id: str | None = None
    if args:
        command = args[0]
        run_id_raw = getattr(command, "run_id", None)
        if isinstance(run_id_raw, UUID):
            run_id = str(run_id_raw)
    return name, run_id


def _run_guarded(func: Callable[..., T], args: tuple, kwargs: dict) -> T | None:
    if not should_execute_queued_product_work(func, args, kwargs):
        return None
    return func(*args, **kwargs)


async def run_blocking_background_task(func: Callable[..., T], /, *args, **kwargs) -> T | None:
    operation, run_id = _operation_label(func, args)
    register_background_job_started(operation, run_id)
    start = time.perf_counter()
    success = False
    try:
        result = await run_in_threadpool(_run_guarded, func, args, kwargs)
        success = True
        return result
    finally:
        register_background_job_finished(
            operation,
            run_id=run_id,
            duration_ms=(time.perf_counter() - start) * 1000,
            success=success,
        )


def schedule_detached_blocking_job(func: Callable[..., T], /, *args, **kwargs) -> None:
    """Fire-and-forget blocking work that must not delay the HTTP response.

    Starlette ``BackgroundTasks`` can execute before the client receives the
    response body when ``BaseHTTPMiddleware`` is in the stack (e.g. request
    timing). Long SMTP / batch work is therefore detached onto a daemon thread.

    Tests may force inline execution via ``configure_detached_jobs_inline(True)``
    so the shared request-scoped DB session remains usable.
    """

    def _runner() -> None:
        operation, run_id = _operation_label(func, args)
        register_background_job_started(operation, run_id)
        start = time.perf_counter()
        success = False
        try:
            _run_guarded(func, args, kwargs)
            success = True
        except Exception:
            logger.exception("detached_background_job_failed operation=%s", operation)
        finally:
            register_background_job_finished(
                operation,
                run_id=run_id,
                duration_ms=(time.perf_counter() - start) * 1000,
                success=success,
            )

    if _detached_jobs_inline:
        _runner()
        return

    thread_name = f"detached-{getattr(func, '__name__', 'job')}"
    threading.Thread(target=_runner, name=thread_name, daemon=True).start()
