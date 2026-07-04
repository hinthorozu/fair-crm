"""Append and query adapter run console logs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.modules.scraper.domain.scraper_run_log import ScraperRunLog, ScraperRunLogLevel
from app.modules.scraper.infrastructure.repositories.scraper_run_log_repository import ScraperRunLogRepository


class ScraperRunLogService:
    def __init__(self, repository: ScraperRunLogRepository) -> None:
        self._repository = repository

    def append_log(
        self,
        *,
        run_id: UUID,
        level: ScraperRunLogLevel,
        step: str,
        message: str,
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> ScraperRunLog:
        return self._repository.add(
            ScraperRunLog(
                id=uuid4(),
                run_id=run_id,
                level=level,
                step=step,
                message=message,
                created_at=created_at or datetime.now(UTC),
                metadata=metadata,
            )
        )

    def list_logs(
        self,
        run_id: UUID,
        *,
        after_id: UUID | None = None,
        limit: int = 500,
    ) -> list[ScraperRunLog]:
        return self._repository.list_by_run_id(run_id, after_id=after_id, limit=limit)

    def count_logs(self, run_id: UUID) -> int:
        return self._repository.count_by_run_id(run_id)


def create_run_log_service(session: Session) -> ScraperRunLogService:
    return ScraperRunLogService(ScraperRunLogRepository(session))
