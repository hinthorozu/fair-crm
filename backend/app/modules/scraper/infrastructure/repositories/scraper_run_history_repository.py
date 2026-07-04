"""Persistence for scraper run history."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.modules.scraper.domain.scraper_run_history import ScraperRunHistory, ScraperRunStatus
from app.modules.scraper.infrastructure.persistence.models import ScraperRunHistoryModel


def _to_entity(model: ScraperRunHistoryModel) -> ScraperRunHistory:
    return ScraperRunHistory(
        id=model.id,
        adapter_key=model.adapter_key,
        status=ScraperRunStatus(model.status),
        started_at=model.started_at,
        finished_at=model.finished_at,
        duration_ms=model.duration_ms,
        organization_id=model.organization_id,
        fair_id=model.fair_id,
        input_url=model.input_url,
        fair_name=model.fair_name,
        fair_year=model.fair_year,
        total_rows=model.total_rows,
        website_count=model.website_count,
        email_count=model.email_count,
        phone_count=model.phone_count,
        instagram_count=model.instagram_count,
        linkedin_count=model.linkedin_count,
        facebook_count=model.facebook_count,
        youtube_count=model.youtube_count,
        x_count=model.x_count,
        error_message=model.error_message,
        output_json_path=model.output_json_path,
        output_excel_path=model.output_excel_path,
    )


class ScraperRunHistoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, run: ScraperRunHistory) -> ScraperRunHistory:
        model = ScraperRunHistoryModel(
            id=run.id,
            adapter_key=run.adapter_key,
            status=run.status.value,
            started_at=run.started_at,
            finished_at=run.finished_at,
            duration_ms=run.duration_ms,
            organization_id=run.organization_id,
            fair_id=run.fair_id,
            input_url=run.input_url,
            fair_name=run.fair_name,
            fair_year=run.fair_year,
            total_rows=run.total_rows,
            website_count=run.website_count,
            email_count=run.email_count,
            phone_count=run.phone_count,
            instagram_count=run.instagram_count,
            linkedin_count=run.linkedin_count,
            facebook_count=run.facebook_count,
            youtube_count=run.youtube_count,
            x_count=run.x_count,
            error_message=run.error_message,
            output_json_path=run.output_json_path,
            output_excel_path=run.output_excel_path,
        )
        self._session.add(model)
        self._session.flush()
        return _to_entity(model)

    def update(self, run: ScraperRunHistory) -> ScraperRunHistory:
        model = self._session.get(ScraperRunHistoryModel, run.id)
        if model is None:
            raise KeyError(f"Scraper run not found: {run.id}")
        model.adapter_key = run.adapter_key
        model.status = run.status.value
        model.started_at = run.started_at
        model.finished_at = run.finished_at
        model.duration_ms = run.duration_ms
        model.organization_id = run.organization_id
        model.fair_id = run.fair_id
        model.input_url = run.input_url
        model.fair_name = run.fair_name
        model.fair_year = run.fair_year
        model.total_rows = run.total_rows
        model.website_count = run.website_count
        model.email_count = run.email_count
        model.phone_count = run.phone_count
        model.instagram_count = run.instagram_count
        model.linkedin_count = run.linkedin_count
        model.facebook_count = run.facebook_count
        model.youtube_count = run.youtube_count
        model.x_count = run.x_count
        model.error_message = run.error_message
        model.output_json_path = run.output_json_path
        model.output_excel_path = run.output_excel_path
        self._session.flush()
        return _to_entity(model)

    def get_by_id(self, run_id: UUID) -> ScraperRunHistory | None:
        model = self._session.get(ScraperRunHistoryModel, run_id)
        if model is None:
            return None
        return _to_entity(model)

    def list_runs(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        fair_id: UUID | None = None,
    ) -> list[ScraperRunHistory]:
        stmt = select(ScraperRunHistoryModel).order_by(desc(ScraperRunHistoryModel.started_at))
        if fair_id is not None:
            stmt = stmt.where(ScraperRunHistoryModel.fair_id == fair_id)
        stmt = stmt.limit(limit).offset(offset)
        return [_to_entity(model) for model in self._session.scalars(stmt).all()]

    def count_runs(self, *, fair_id: UUID | None = None) -> int:
        stmt = select(func.count()).select_from(ScraperRunHistoryModel)
        if fair_id is not None:
            stmt = stmt.where(ScraperRunHistoryModel.fair_id == fair_id)
        return int(self._session.scalar(stmt) or 0)

    def count_failed(self) -> int:
        stmt = (
            select(func.count())
            .select_from(ScraperRunHistoryModel)
            .where(ScraperRunHistoryModel.status == ScraperRunStatus.FAILED.value)
        )
        return int(self._session.scalar(stmt) or 0)

    def get_latest(self, *, fair_id: UUID | None = None) -> ScraperRunHistory | None:
        stmt = select(ScraperRunHistoryModel).order_by(desc(ScraperRunHistoryModel.started_at)).limit(1)
        if fair_id is not None:
            stmt = stmt.where(ScraperRunHistoryModel.fair_id == fair_id)
        model = self._session.scalars(stmt).first()
        if model is None:
            return None
        return _to_entity(model)

    def get_latest_completed_for_fair(self, fair_id: UUID) -> ScraperRunHistory | None:
        stmt = (
            select(ScraperRunHistoryModel)
            .where(
                ScraperRunHistoryModel.fair_id == fair_id,
                ScraperRunHistoryModel.status == ScraperRunStatus.COMPLETED.value,
            )
            .order_by(desc(ScraperRunHistoryModel.finished_at))
            .limit(1)
        )
        model = self._session.scalars(stmt).first()
        if model is None:
            return None
        return _to_entity(model)
