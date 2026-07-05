"""Record and query adapter scraper run history."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.modules.scraper.domain.scraper_run_history import ScraperRunHistory, ScraperRunStatus
from app.modules.scraper.domain.scraper_run_source import ScraperRunSource
from app.modules.scraper.domain.scraper_run_history_filters import ScraperRunHistoryListFilters
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import (
    ScraperRunHistoryListRow,
    ScraperRunHistoryRepository,
)


def compute_handoff_metrics(handoff: ScraperImportHandoff) -> dict[str, int]:
    rows = handoff.canonical_rows or []
    row_metadata = handoff.row_metadata or []
    padded_metadata = row_metadata + [{}] * max(0, len(rows) - len(row_metadata))

    def meta_filled(index: int, key: str) -> bool:
        if index >= len(padded_metadata):
            return False
        return bool(str(padded_metadata[index].get(key) or "").strip())

    return {
        "total_rows": len(rows),
        "website_count": sum(1 for row in rows if str(row.get("website") or "").strip()),
        "email_count": sum(1 for row in rows if str(row.get("email") or "").strip()),
        "phone_count": sum(1 for row in rows if str(row.get("phone") or "").strip()),
        "instagram_count": sum(1 for index in range(len(rows)) if meta_filled(index, "instagram_url")),
        "linkedin_count": sum(1 for index in range(len(rows)) if meta_filled(index, "linkedin_url")),
        "facebook_count": sum(1 for index in range(len(rows)) if meta_filled(index, "facebook_url")),
        "youtube_count": sum(1 for index in range(len(rows)) if meta_filled(index, "youtube_url")),
        "x_count": sum(1 for index in range(len(rows)) if meta_filled(index, "x_url")),
    }


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def duration_ms_between(started_at: datetime, finished_at: datetime) -> int:
    delta = _ensure_utc(finished_at) - _ensure_utc(started_at)
    return max(0, int(delta.total_seconds() * 1000))


class ScraperRunHistoryService:
    def __init__(self, repository: ScraperRunHistoryRepository) -> None:
        self._repository = repository

    def start_run(
        self,
        *,
        adapter_key: str,
        input_url: str | None,
        fair_name: str | None,
        fair_year: int | None,
        organization_id: UUID | None = None,
        fair_id: UUID | None = None,
        started_at: datetime | None = None,
        run_source: ScraperRunSource = ScraperRunSource.MANUAL_TEST,
    ) -> ScraperRunHistory:
        started = started_at or datetime.now(UTC)
        return self._repository.add(
            ScraperRunHistory(
                id=uuid4(),
                adapter_key=adapter_key,
                status=ScraperRunStatus.RUNNING,
                started_at=started,
                finished_at=None,
                duration_ms=None,
                organization_id=organization_id,
                fair_id=fair_id,
                input_url=input_url,
                fair_name=fair_name,
                fair_year=fair_year,
                total_rows=0,
                website_count=0,
                email_count=0,
                phone_count=0,
                instagram_count=0,
                linkedin_count=0,
                facebook_count=0,
                youtube_count=0,
                x_count=0,
                error_message=None,
                output_json_path=None,
                output_excel_path=None,
                run_source=run_source,
                import_batch_id=None,
            )
        )

    def complete_run(
        self,
        run_id: UUID,
        *,
        handoff: ScraperImportHandoff,
        finished_at: datetime | None = None,
        output_json_path: str | None = None,
        output_excel_path: str | None = None,
        import_batch_id: UUID | None = None,
    ) -> ScraperRunHistory:
        existing = self._repository.get_by_id(run_id)
        if existing is None:
            raise KeyError(f"Scraper run not found: {run_id}")
        if existing.status == ScraperRunStatus.CANCELLED:
            return existing
        finished = finished_at or datetime.now(UTC)
        metrics = compute_handoff_metrics(handoff)
        return self._repository.update(
            replace(
                existing,
                status=ScraperRunStatus.COMPLETED,
                finished_at=finished,
                duration_ms=duration_ms_between(existing.started_at, finished),
                error_message=None,
                output_json_path=output_json_path,
                output_excel_path=output_excel_path,
                import_batch_id=import_batch_id if import_batch_id is not None else existing.import_batch_id,
                **metrics,
            )
        )

    def fail_run(
        self,
        run_id: UUID,
        *,
        error_message: str,
        finished_at: datetime | None = None,
        output_json_path: str | None = None,
        output_excel_path: str | None = None,
    ) -> ScraperRunHistory:
        existing = self._repository.get_by_id(run_id)
        if existing is None:
            raise KeyError(f"Scraper run not found: {run_id}")
        if existing.status == ScraperRunStatus.CANCELLED:
            return existing
        finished = finished_at or datetime.now(UTC)
        return self._repository.update(
            replace(
                existing,
                status=ScraperRunStatus.FAILED,
                finished_at=finished,
                duration_ms=duration_ms_between(existing.started_at, finished),
                total_rows=0,
                website_count=0,
                email_count=0,
                phone_count=0,
                instagram_count=0,
                linkedin_count=0,
                facebook_count=0,
                youtube_count=0,
                x_count=0,
                error_message=error_message,
                output_json_path=output_json_path,
                output_excel_path=output_excel_path,
            )
        )

    def record_completed_run(
        self,
        *,
        adapter_key: str,
        started_at: datetime,
        finished_at: datetime | None = None,
        input_url: str | None,
        fair_name: str | None,
        fair_year: int | None,
        handoff: ScraperImportHandoff,
        organization_id: UUID | None = None,
        fair_id: UUID | None = None,
        output_json_path: str | None = None,
        output_excel_path: str | None = None,
        run_source: ScraperRunSource = ScraperRunSource.MANUAL_TEST,
        import_batch_id: UUID | None = None,
    ) -> ScraperRunHistory:
        finished = finished_at or datetime.now(UTC)
        metrics = compute_handoff_metrics(handoff)
        return self._repository.add(
            ScraperRunHistory(
                id=uuid4(),
                adapter_key=adapter_key,
                status=ScraperRunStatus.COMPLETED,
                started_at=started_at,
                finished_at=finished,
                duration_ms=duration_ms_between(started_at, finished),
                organization_id=organization_id,
                fair_id=fair_id,
                input_url=input_url,
                fair_name=fair_name,
                fair_year=fair_year,
                error_message=None,
                output_json_path=output_json_path,
                output_excel_path=output_excel_path,
                run_source=run_source,
                import_batch_id=import_batch_id,
                **metrics,
            )
        )

    def record_failed_run(
        self,
        *,
        adapter_key: str,
        started_at: datetime,
        input_url: str | None,
        fair_name: str | None,
        fair_year: int | None,
        error_message: str,
        organization_id: UUID | None = None,
        fair_id: UUID | None = None,
        finished_at: datetime | None = None,
        output_json_path: str | None = None,
        output_excel_path: str | None = None,
        run_source: ScraperRunSource = ScraperRunSource.MANUAL_TEST,
    ) -> ScraperRunHistory:
        finished = finished_at or datetime.now(UTC)
        return self._repository.add(
            ScraperRunHistory(
                id=uuid4(),
                adapter_key=adapter_key,
                status=ScraperRunStatus.FAILED,
                started_at=started_at,
                finished_at=finished,
                duration_ms=duration_ms_between(started_at, finished),
                organization_id=organization_id,
                fair_id=fair_id,
                input_url=input_url,
                fair_name=fair_name,
                fair_year=fair_year,
                total_rows=0,
                website_count=0,
                email_count=0,
                phone_count=0,
                instagram_count=0,
                linkedin_count=0,
                facebook_count=0,
                youtube_count=0,
                x_count=0,
                error_message=error_message,
                output_json_path=output_json_path,
                output_excel_path=output_excel_path,
                run_source=run_source,
                import_batch_id=None,
            )
        )

    def list_runs(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        fair_id: UUID | None = None,
        filters: ScraperRunHistoryListFilters | None = None,
    ) -> list[ScraperRunHistory]:
        return self._repository.list_runs(limit=limit, offset=offset, fair_id=fair_id, filters=filters)

    def list_run_rows(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        fair_id: UUID | None = None,
        filters: ScraperRunHistoryListFilters | None = None,
    ) -> list[ScraperRunHistoryListRow]:
        return self._repository.list_run_rows(limit=limit, offset=offset, fair_id=fair_id, filters=filters)

    def get_run(self, run_id: UUID) -> ScraperRunHistory | None:
        return self._repository.get_by_id(run_id)

    def get_run_row(
        self,
        run_id: UUID,
        *,
        organization_id: UUID | None = None,
    ) -> ScraperRunHistoryListRow | None:
        return self._repository.get_run_row_by_id(run_id, organization_id=organization_id)

    def count_runs(
        self,
        *,
        fair_id: UUID | None = None,
        filters: ScraperRunHistoryListFilters | None = None,
    ) -> int:
        return self._repository.count_runs(fair_id=fair_id, filters=filters)

    def get_latest_completed_for_fair(self, fair_id: UUID) -> ScraperRunHistory | None:
        return self._repository.get_latest_completed_for_fair(fair_id)

    def list_running_for_adapter(
        self,
        *,
        adapter_key: str,
        organization_id: UUID | None = None,
    ) -> list[ScraperRunHistory]:
        return self._repository.list_running_for_adapter(
            adapter_key=adapter_key,
            organization_id=organization_id,
        )

    def count_running_for_adapter(
        self,
        *,
        adapter_key: str,
        organization_id: UUID | None = None,
    ) -> int:
        return self._repository.count_running_for_adapter(
            adapter_key=adapter_key,
            organization_id=organization_id,
        )

    def cancel_run(
        self,
        run_id: UUID,
        *,
        reason: str,
        finished_at: datetime | None = None,
    ) -> ScraperRunHistory:
        existing = self._repository.get_by_id(run_id)
        if existing is None:
            raise KeyError(f"Scraper run not found: {run_id}")
        if existing.status != ScraperRunStatus.RUNNING:
            return existing
        finished = finished_at or datetime.now(UTC)
        return self._repository.update(
            replace(
                existing,
                status=ScraperRunStatus.CANCELLED,
                finished_at=finished,
                duration_ms=duration_ms_between(existing.started_at, finished),
                error_message=reason,
            )
        )

    def cancel_running_for_adapter(
        self,
        *,
        adapter_key: str,
        organization_id: UUID | None,
        reason: str,
    ) -> list[ScraperRunHistory]:
        cancelled: list[ScraperRunHistory] = []
        for run in self.list_running_for_adapter(adapter_key=adapter_key, organization_id=organization_id):
            cancelled.append(self.cancel_run(run.id, reason=reason))
        return cancelled

    def hard_delete_runs_for_adapter(
        self,
        *,
        adapter_key: str,
        organization_id: UUID,
    ) -> int:
        return self._repository.hard_delete_for_adapter(
            adapter_key=adapter_key,
            organization_id=organization_id,
        )

    def get_dashboard_run_stats(self) -> dict[str, int | str | None]:
        latest = self._repository.get_latest()
        return {
            "last_run_adapter": latest.adapter_key if latest is not None else None,
            "failed_scraper_count": self._repository.count_failed(),
        }


def create_run_history_service(session: Session) -> ScraperRunHistoryService:
    return ScraperRunHistoryService(ScraperRunHistoryRepository(session))

