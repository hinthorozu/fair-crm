"""Request and SQL performance instrumentation."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool

logger = logging.getLogger("fair_crm.performance")

_active_background_jobs = 0
_active_background_jobs_lock = threading.Lock()


def register_background_job_started(operation: str, run_id: str | None = None) -> None:
    global _active_background_jobs
    with _active_background_jobs_lock:
        _active_background_jobs += 1
        active = _active_background_jobs
    logger.info(
        "background_job_started operation=%s run_id=%s thread=%s active_jobs=%s",
        operation,
        run_id or "-",
        threading.current_thread().name,
        active,
    )


def register_background_job_finished(
    operation: str,
    *,
    run_id: str | None = None,
    duration_ms: float,
    success: bool,
) -> None:
    global _active_background_jobs
    with _active_background_jobs_lock:
        _active_background_jobs = max(0, _active_background_jobs - 1)
        active = _active_background_jobs
    logger.info(
        "background_job_finished operation=%s run_id=%s duration_ms=%.2f success=%s thread=%s active_jobs=%s",
        operation,
        run_id or "-",
        duration_ms,
        success,
        threading.current_thread().name,
        active,
    )


def active_background_job_count() -> int:
    with _active_background_jobs_lock:
        return _active_background_jobs


def setup_sqlalchemy_performance_logging(
    engine: Engine,
    *,
    slow_query_ms: float,
) -> None:
    threshold = slow_query_ms / 1000.0

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        stack = conn.info.setdefault("query_start_time", [])
        stack.append(time.perf_counter())

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        stack = conn.info.get("query_start_time")
        if not stack:
            return
        elapsed = time.perf_counter() - stack.pop()
        if elapsed >= threshold:
            normalized = " ".join(statement.split())
            logger.warning(
                "slow_sql duration_ms=%.2f rows=%s sql=%s",
                elapsed * 1000,
                cursor.rowcount,
                normalized[:500],
            )

    @event.listens_for(Pool, "checkout")
    def on_checkout(dbapi_connection, connection_record, connection_proxy):
        connection_record.info["checkout_start"] = time.perf_counter()

    @event.listens_for(Pool, "checkin")
    def on_checkin(dbapi_connection, connection_record):
        checkout_start = connection_record.info.pop("checkout_start", None)
        if checkout_start is None:
            return
        held_ms = (time.perf_counter() - checkout_start) * 1000
        if held_ms >= max(slow_query_ms * 10, 2000):
            logger.warning("long_connection_hold duration_ms=%.2f", held_ms)


def log_pool_status(engine: Engine) -> None:
    pool: Any = engine.pool
    logger.info(
        "db_pool_status checked_out=%s overflow=%s size=%s",
        pool.checkedout(),
        pool.overflow(),
        pool.size(),
    )
