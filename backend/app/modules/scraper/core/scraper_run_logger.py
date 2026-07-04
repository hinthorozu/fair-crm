"""Structured run console logger for adapter scrape progress."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol
from uuid import UUID

from app.modules.scraper.domain.scraper_run_log import ScraperRunLogLevel
from app.modules.scraper.types.scraper_context import ScraperContext

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.modules.scraper.services.scraper_run_log_service import ScraperRunLogService


class ScraperRunLogger(Protocol):
    def info(self, step: str, message: str, *, metadata: dict[str, Any] | None = None) -> None: ...

    def warning(self, step: str, message: str, *, metadata: dict[str, Any] | None = None) -> None: ...

    def error(self, step: str, message: str, *, metadata: dict[str, Any] | None = None) -> None: ...

    def success(self, step: str, message: str, *, metadata: dict[str, Any] | None = None) -> None: ...


WARNING_LOG_CAP = 200
DETAIL_PROGRESS_INTERVAL = 50


class CappedWarningRunLogger:
    """Wraps a run logger and limits warning log volume per run."""

    def __init__(self, inner: ScraperRunLogger, *, cap: int = WARNING_LOG_CAP) -> None:
        self._inner = inner
        self._cap = cap
        self._warning_count = 0
        self._suppressed = 0

    def info(self, step: str, message: str, *, metadata: dict[str, Any] | None = None) -> None:
        self._inner.info(step, message, metadata=metadata)

    def warning(self, step: str, message: str, *, metadata: dict[str, Any] | None = None) -> None:
        if self._warning_count >= self._cap:
            self._suppressed += 1
            return
        self._inner.warning(step, message, metadata=metadata)
        self._warning_count += 1

    def error(self, step: str, message: str, *, metadata: dict[str, Any] | None = None) -> None:
        self._inner.error(step, message, metadata=metadata)

    def success(self, step: str, message: str, *, metadata: dict[str, Any] | None = None) -> None:
        self._inner.success(step, message, metadata=metadata)

    def flush_suppressed_warnings(self, step: str = "detail_scrape_progress") -> None:
        if self._suppressed <= 0:
            return
        self._inner.warning(
            step,
            f"{self._suppressed} uyarı limit nedeniyle gösterilmedi (limit: {self._cap})",
            metadata={"suppressed_warnings": self._suppressed, "cap": self._cap},
        )


class NullScraperRunLogger:
    def info(self, step: str, message: str, *, metadata: dict[str, Any] | None = None) -> None:
        _ = (step, message, metadata)

    def warning(self, step: str, message: str, *, metadata: dict[str, Any] | None = None) -> None:
        _ = (step, message, metadata)

    def error(self, step: str, message: str, *, metadata: dict[str, Any] | None = None) -> None:
        _ = (step, message, metadata)

    def success(self, step: str, message: str, *, metadata: dict[str, Any] | None = None) -> None:
        _ = (step, message, metadata)


def resolve_run_logger(context: ScraperContext) -> ScraperRunLogger:
    logger = context.options.get("run_logger")
    if logger is None:
        return NullScraperRunLogger()
    return logger  # type: ignore[return-value]


class DbScraperRunLogger:
    """Persists each log line immediately for polling-based live console."""

    def __init__(
        self,
        run_id: UUID,
        log_service: "ScraperRunLogService",
        session: Session,
    ) -> None:
        self._run_id = run_id
        self._log_service = log_service
        self._session = session

    def info(self, step: str, message: str, *, metadata: dict[str, Any] | None = None) -> None:
        self._append(ScraperRunLogLevel.INFO, step, message, metadata)

    def warning(self, step: str, message: str, *, metadata: dict[str, Any] | None = None) -> None:
        self._append(ScraperRunLogLevel.WARNING, step, message, metadata)

    def error(self, step: str, message: str, *, metadata: dict[str, Any] | None = None) -> None:
        self._append(ScraperRunLogLevel.ERROR, step, message, metadata)

    def success(self, step: str, message: str, *, metadata: dict[str, Any] | None = None) -> None:
        self._append(ScraperRunLogLevel.SUCCESS, step, message, metadata)

    def _append(
        self,
        level: ScraperRunLogLevel,
        step: str,
        message: str,
        metadata: dict[str, Any] | None,
    ) -> None:
        self._log_service.append_log(
            run_id=self._run_id,
            level=level,
            step=step,
            message=message,
            metadata=metadata,
        )
        self._session.commit()
