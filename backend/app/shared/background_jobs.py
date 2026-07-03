"""Run blocking work from Starlette BackgroundTasks without freezing the API event loop."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar
from uuid import UUID

from starlette.concurrency import run_in_threadpool

from app.core.performance_monitoring import (
    register_background_job_finished,
    register_background_job_started,
)

logger = logging.getLogger("fair_crm.performance")

T = TypeVar("T")


def _operation_label(func: Callable[..., T], args: tuple) -> tuple[str, str | None]:
    name = getattr(func, "__name__", func.__class__.__name__)
    run_id: str | None = None
    if args:
        command = args[0]
        run_id_raw = getattr(command, "run_id", None)
        if isinstance(run_id_raw, UUID):
            run_id = str(run_id_raw)
    return name, run_id


async def run_blocking_background_task(func: Callable[..., T], /, *args, **kwargs) -> T:
    operation, run_id = _operation_label(func, args)
    register_background_job_started(operation, run_id)
    start = time.perf_counter()
    success = False
    try:
        if kwargs:
            result = await run_in_threadpool(lambda: func(*args, **kwargs))
        else:
            result = await run_in_threadpool(func, *args)
        success = True
        return result
    finally:
        register_background_job_finished(
            operation,
            run_id=run_id,
            duration_ms=(time.perf_counter() - start) * 1000,
            success=success,
        )
