"""Persistence for scraper run console logs."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy import asc, func, select
from sqlalchemy.orm import Session

from app.modules.scraper.domain.scraper_run_log import ScraperRunLog, ScraperRunLogLevel
from app.modules.scraper.infrastructure.persistence.models import ScraperRunLogModel


def _parse_metadata(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _to_entity(model: ScraperRunLogModel) -> ScraperRunLog:
    return ScraperRunLog(
        id=model.id,
        run_id=model.run_id,
        level=ScraperRunLogLevel(model.level),
        step=model.step,
        message=model.message,
        created_at=model.created_at,
        metadata=_parse_metadata(model.metadata_json),
    )


class ScraperRunLogRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, log: ScraperRunLog) -> ScraperRunLog:
        metadata_json = json.dumps(log.metadata, ensure_ascii=False) if log.metadata else None
        model = ScraperRunLogModel(
            id=log.id,
            run_id=log.run_id,
            level=log.level.value,
            step=log.step,
            message=log.message,
            created_at=log.created_at,
            metadata_json=metadata_json,
        )
        self._session.add(model)
        self._session.flush()
        return _to_entity(model)

    def list_by_run_id(
        self,
        run_id: UUID,
        *,
        after_id: UUID | None = None,
        limit: int = 500,
    ) -> list[ScraperRunLog]:
        stmt = select(ScraperRunLogModel).where(ScraperRunLogModel.run_id == run_id)
        if after_id is not None:
            anchor = self._session.get(ScraperRunLogModel, after_id)
            if anchor is not None:
                stmt = stmt.where(
                    (ScraperRunLogModel.created_at > anchor.created_at)
                    | (
                        (ScraperRunLogModel.created_at == anchor.created_at)
                        & (ScraperRunLogModel.id > anchor.id)
                    )
                )
        stmt = stmt.order_by(asc(ScraperRunLogModel.created_at), asc(ScraperRunLogModel.id)).limit(limit)
        return [_to_entity(model) for model in self._session.scalars(stmt).all()]

    def count_by_run_id(self, run_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(ScraperRunLogModel)
            .where(ScraperRunLogModel.run_id == run_id)
        )
        return int(self._session.scalar(stmt) or 0)
