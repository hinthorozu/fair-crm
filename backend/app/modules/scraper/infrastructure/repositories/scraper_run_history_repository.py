"""Persistence for scraper run history."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import and_, delete, desc, func, select
from sqlalchemy.orm import Session

from app.modules.scraper.domain.scraper_run_history import (
    ACTIVE_SCRAPER_RUN_STATUSES,
    ScraperRunHistory,
    ScraperRunStatus,
)
from app.modules.scraper.domain.scraper_run_source import ScraperRunSource
from app.modules.scraper.domain.scraper_run_history_filters import ScraperRunHistoryListFilters
from app.modules.scraper.infrastructure.persistence.models import ScraperAdapterModel, ScraperRunHistoryModel


@dataclass(frozen=True)
class ScraperRunHistoryListRow:
    run: ScraperRunHistory
    adapter_name: str | None
    adapter_engine_key: str | None


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
        run_source=ScraperRunSource(model.run_source),
        import_batch_id=model.import_batch_id,
        cancel_requested_by=model.cancel_requested_by,
        cancel_requested_at=model.cancel_requested_at,
        last_heartbeat_at=model.last_heartbeat_at,
        progress_current=model.progress_current,
        progress_total=model.progress_total,
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
            run_source=run.run_source.value,
            import_batch_id=run.import_batch_id,
            cancel_requested_by=run.cancel_requested_by,
            cancel_requested_at=run.cancel_requested_at,
            last_heartbeat_at=run.last_heartbeat_at,
            progress_current=run.progress_current,
            progress_total=run.progress_total,
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
        model.run_source = run.run_source.value
        model.import_batch_id = run.import_batch_id
        model.cancel_requested_by = run.cancel_requested_by
        model.cancel_requested_at = run.cancel_requested_at
        model.last_heartbeat_at = run.last_heartbeat_at
        model.progress_current = run.progress_current
        model.progress_total = run.progress_total
        self._session.flush()
        return _to_entity(model)

    def get_by_id(self, run_id: UUID) -> ScraperRunHistory | None:
        row = self.get_run_row_by_id(run_id)
        if row is None:
            return None
        return row.run

    def get_run_row_by_id(
        self,
        run_id: UUID,
        *,
        organization_id: UUID | None = None,
    ) -> ScraperRunHistoryListRow | None:
        stmt = (
            select(
                ScraperRunHistoryModel,
                ScraperAdapterModel.name,
                ScraperAdapterModel.engine_key,
            )
            .outerjoin(
                ScraperAdapterModel,
                and_(
                    ScraperAdapterModel.adapter_key == ScraperRunHistoryModel.adapter_key,
                    ScraperAdapterModel.deleted_at.is_(None),
                    *(
                        [ScraperAdapterModel.organization_id == organization_id]
                        if organization_id is not None
                        else []
                    ),
                ),
            )
            .where(ScraperRunHistoryModel.id == run_id)
        )
        if organization_id is not None:
            stmt = stmt.where(ScraperRunHistoryModel.organization_id == organization_id)
        row = self._session.execute(stmt).first()
        if row is None:
            return None
        model, adapter_name, adapter_engine_key = row
        return ScraperRunHistoryListRow(
            run=_to_entity(model),
            adapter_name=adapter_name,
            adapter_engine_key=adapter_engine_key,
        )

    def list_runs(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        fair_id: UUID | None = None,
        filters: ScraperRunHistoryListFilters | None = None,
    ) -> list[ScraperRunHistory]:
        rows = self.list_run_rows(limit=limit, offset=offset, fair_id=fair_id, filters=filters)
        return [row.run for row in rows]

    def list_run_rows(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        fair_id: UUID | None = None,
        filters: ScraperRunHistoryListFilters | None = None,
    ) -> list[ScraperRunHistoryListRow]:
        resolved_filters = filters or ScraperRunHistoryListFilters()
        if fair_id is not None and resolved_filters.fair_id is None:
            resolved_filters = ScraperRunHistoryListFilters(
                organization_id=resolved_filters.organization_id,
                adapter_key=resolved_filters.adapter_key,
                adapter_id=resolved_filters.adapter_id,
                status=resolved_filters.status,
                engine_keys=resolved_filters.engine_keys,
                date_from=resolved_filters.date_from,
                date_to=resolved_filters.date_to,
                url_query=resolved_filters.url_query,
                fair_id=fair_id,
            )

        stmt = (
            select(
                ScraperRunHistoryModel,
                ScraperAdapterModel.name,
                ScraperAdapterModel.engine_key,
            )
            .outerjoin(
                ScraperAdapterModel,
                and_(
                    ScraperAdapterModel.adapter_key == ScraperRunHistoryModel.adapter_key,
                    ScraperAdapterModel.deleted_at.is_(None),
                    *(
                        [ScraperAdapterModel.organization_id == resolved_filters.organization_id]
                        if resolved_filters.organization_id is not None
                        else []
                    ),
                ),
            )
            .order_by(desc(ScraperRunHistoryModel.started_at))
        )
        stmt = self._apply_run_filters(stmt, resolved_filters)
        stmt = stmt.limit(limit).offset(offset)
        return [
            ScraperRunHistoryListRow(
                run=_to_entity(model),
                adapter_name=adapter_name,
                adapter_engine_key=adapter_engine_key,
            )
            for model, adapter_name, adapter_engine_key in self._session.execute(stmt).all()
        ]

    def count_runs(
        self,
        *,
        fair_id: UUID | None = None,
        filters: ScraperRunHistoryListFilters | None = None,
    ) -> int:
        resolved_filters = filters or ScraperRunHistoryListFilters()
        if fair_id is not None and resolved_filters.fair_id is None:
            resolved_filters = ScraperRunHistoryListFilters(
                organization_id=resolved_filters.organization_id,
                adapter_key=resolved_filters.adapter_key,
                adapter_id=resolved_filters.adapter_id,
                status=resolved_filters.status,
                engine_keys=resolved_filters.engine_keys,
                date_from=resolved_filters.date_from,
                date_to=resolved_filters.date_to,
                url_query=resolved_filters.url_query,
                fair_id=fair_id,
            )

        stmt = (
            select(func.count())
            .select_from(ScraperRunHistoryModel)
            .outerjoin(
                ScraperAdapterModel,
                and_(
                    ScraperAdapterModel.adapter_key == ScraperRunHistoryModel.adapter_key,
                    ScraperAdapterModel.deleted_at.is_(None),
                    *(
                        [ScraperAdapterModel.organization_id == resolved_filters.organization_id]
                        if resolved_filters.organization_id is not None
                        else []
                    ),
                ),
            )
        )
        stmt = self._apply_run_filters(stmt, resolved_filters)
        return int(self._session.scalar(stmt) or 0)

    def _apply_run_filters(self, stmt, filters: ScraperRunHistoryListFilters):
        if filters.organization_id is not None:
            stmt = stmt.where(ScraperRunHistoryModel.organization_id == filters.organization_id)
        if filters.adapter_key:
            normalized_key = filters.adapter_key.strip().lower()
            stmt = stmt.where(ScraperRunHistoryModel.adapter_key == normalized_key)
        if filters.adapter_id is not None:
            stmt = stmt.where(ScraperAdapterModel.id == filters.adapter_id)
        if filters.status is not None:
            stmt = stmt.where(ScraperRunHistoryModel.status == filters.status.value)
        if filters.engine_keys:
            engine_keys = tuple(key.strip().lower() for key in filters.engine_keys if key.strip())
            if engine_keys:
                stmt = stmt.where(
                    func.coalesce(ScraperAdapterModel.engine_key, ScraperRunHistoryModel.adapter_key).in_(
                        engine_keys
                    )
                )
        if filters.date_from is not None:
            stmt = stmt.where(ScraperRunHistoryModel.started_at >= filters.date_from)
        if filters.date_to is not None:
            stmt = stmt.where(ScraperRunHistoryModel.started_at <= filters.date_to)
        if filters.url_query:
            stmt = stmt.where(ScraperRunHistoryModel.input_url.ilike(f"%{filters.url_query.strip()}%"))
        if filters.fair_id is not None:
            stmt = stmt.where(ScraperRunHistoryModel.fair_id == filters.fair_id)
        return stmt

    def count_failed(self) -> int:
        stmt = (
            select(func.count())
            .select_from(ScraperRunHistoryModel)
            .where(ScraperRunHistoryModel.status == ScraperRunStatus.FAILED.value)
        )
        return int(self._session.scalar(stmt) or 0)

    def count_failed_for_organization(self, organization_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(ScraperRunHistoryModel)
            .where(
                ScraperRunHistoryModel.organization_id == organization_id,
                ScraperRunHistoryModel.status == ScraperRunStatus.FAILED.value,
            )
        )
        return int(self._session.scalar(stmt) or 0)

    def get_latest_for_organization(self, organization_id: UUID) -> ScraperRunHistory | None:
        stmt = (
            select(ScraperRunHistoryModel)
            .where(ScraperRunHistoryModel.organization_id == organization_id)
            .order_by(desc(ScraperRunHistoryModel.started_at))
            .limit(1)
        )
        model = self._session.scalars(stmt).first()
        if model is None:
            return None
        return _to_entity(model)

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

    def list_running_for_adapter(
        self,
        *,
        adapter_key: str,
        organization_id: UUID | None = None,
    ) -> list[ScraperRunHistory]:
        active_statuses = tuple(status.value for status in ACTIVE_SCRAPER_RUN_STATUSES)
        stmt = select(ScraperRunHistoryModel).where(
            ScraperRunHistoryModel.adapter_key == adapter_key,
            ScraperRunHistoryModel.status.in_(active_statuses),
        )
        if organization_id is not None:
            stmt = stmt.where(ScraperRunHistoryModel.organization_id == organization_id)
        stmt = stmt.order_by(desc(ScraperRunHistoryModel.started_at))
        return [_to_entity(model) for model in self._session.scalars(stmt).all()]

    def count_running_for_adapter(
        self,
        *,
        adapter_key: str,
        organization_id: UUID | None = None,
    ) -> int:
        active_statuses = tuple(status.value for status in ACTIVE_SCRAPER_RUN_STATUSES)
        stmt = (
            select(func.count())
            .select_from(ScraperRunHistoryModel)
            .where(
                ScraperRunHistoryModel.adapter_key == adapter_key,
                ScraperRunHistoryModel.status.in_(active_statuses),
            )
        )
        if organization_id is not None:
            stmt = stmt.where(ScraperRunHistoryModel.organization_id == organization_id)
        return int(self._session.scalar(stmt) or 0)

    def hard_delete_for_adapter(
        self,
        *,
        adapter_key: str,
        organization_id: UUID,
    ) -> int:
        normalized_key = adapter_key.strip().lower()
        result = self._session.execute(
            delete(ScraperRunHistoryModel).where(
                ScraperRunHistoryModel.adapter_key == normalized_key,
                ScraperRunHistoryModel.organization_id == organization_id,
            )
        )
        self._session.flush()
        return int(result.rowcount or 0)

    def hard_delete_by_id(
        self,
        run_id: UUID,
        *,
        organization_id: UUID,
    ) -> bool:
        result = self._session.execute(
            delete(ScraperRunHistoryModel).where(
                ScraperRunHistoryModel.id == run_id,
                ScraperRunHistoryModel.organization_id == organization_id,
            )
        )
        self._session.flush()
        return int(result.rowcount or 0) > 0

