"""Record and query adapter scraper run history."""

from __future__ import annotations

import time
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

# Cooperative stop wait before treating an active run as stale / force-stopping.
DEFAULT_DELETE_STOP_WAIT_SECONDS = 30.0
DEFAULT_DELETE_STOP_POLL_SECONDS = 0.25
# Active runs with no recent heartbeat are treated as orphaned (no living worker).
DEFAULT_STALE_HEARTBEAT_SECONDS = 120.0

from app.modules.scraper.domain.scraper_run_history import (
    ACTIVE_SCRAPER_RUN_STATUSES,
    ScraperRunHistory,
    ScraperRunStatus,
)
from app.modules.scraper.domain.scraper_run_source import ScraperRunSource
from app.modules.scraper.domain.scraper_run_history_filters import ScraperRunHistoryListFilters
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.handoff_storage import delete_handoff_artifacts_for_run
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import (
    ScraperRunHistoryListRow,
    ScraperRunHistoryRepository,
)


class ScraperRunHistoryDeleteError(Exception):
    """Raised when a run history row cannot be deleted."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


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
                cancel_requested_by=None,
                cancel_requested_at=None,
                last_heartbeat_at=started,
                progress_current=0,
                progress_total=None,
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
        warning_message: str | None = None,
    ) -> ScraperRunHistory | None:
        existing = self._repository.get_by_id(run_id)
        if existing is None:
            # Race-safe: history may have been deleted while the worker finished.
            return None
        if existing.status == ScraperRunStatus.CANCELLED:
            return existing
        if existing.status in {ScraperRunStatus.CANCEL_REQUESTED, ScraperRunStatus.CANCELLING}:
            return existing
        finished = finished_at or datetime.now(UTC)
        metrics = compute_handoff_metrics(handoff)
        return self._repository.update(
            replace(
                existing,
                status=ScraperRunStatus.COMPLETED,
                finished_at=finished,
                duration_ms=duration_ms_between(existing.started_at, finished),
                # Keep scrape success as completed; surface secondary artifact/import warnings.
                error_message=warning_message,
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
    ) -> ScraperRunHistory | None:
        existing = self._repository.get_by_id(run_id)
        if existing is None:
            return None
        if existing.status == ScraperRunStatus.CANCELLED:
            return existing
        if existing.status in {ScraperRunStatus.CANCEL_REQUESTED, ScraperRunStatus.CANCELLING}:
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

    def get_run_for_organization(
        self,
        run_id: UUID,
        organization_id: UUID,
    ) -> ScraperRunHistory | None:
        row = self.get_run_row(run_id, organization_id=organization_id)
        if row is None:
            return None
        return row.run

    def get_run(self, run_id: UUID) -> ScraperRunHistory | None:
        """Internal/background use only — not for tenant-scoped API access."""
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

    def request_cancel(
        self,
        run_id: UUID,
        *,
        organization_id: UUID,
        requested_by: UUID,
        requested_at: datetime | None = None,
    ) -> ScraperRunHistory:
        existing = self._repository.get_by_id(run_id)
        if existing is None or existing.organization_id != organization_id:
            raise KeyError(f"Scraper run not found: {run_id}")
        if existing.status in {
            ScraperRunStatus.CANCELLED,
            ScraperRunStatus.COMPLETED,
            ScraperRunStatus.FAILED,
        }:
            return existing
        if existing.status in {ScraperRunStatus.CANCEL_REQUESTED, ScraperRunStatus.CANCELLING}:
            return existing
        if existing.status != ScraperRunStatus.RUNNING:
            return existing
        requested = requested_at or datetime.now(UTC)
        return self._repository.update(
            replace(
                existing,
                status=ScraperRunStatus.CANCEL_REQUESTED,
                cancel_requested_by=requested_by,
                cancel_requested_at=requested,
            )
        )

    def mark_cancelling(self, run_id: UUID) -> ScraperRunHistory | None:
        existing = self._repository.get_by_id(run_id)
        if existing is None:
            return None
        if existing.status == ScraperRunStatus.CANCELLED:
            return existing
        if existing.status not in {ScraperRunStatus.CANCEL_REQUESTED, ScraperRunStatus.CANCELLING}:
            return existing
        return self._repository.update(
            replace(
                existing,
                status=ScraperRunStatus.CANCELLING,
            )
        )

    def touch_heartbeat(
        self,
        run_id: UUID,
        *,
        progress_current: int | None = None,
        progress_total: int | None = None,
        heartbeat_at: datetime | None = None,
    ) -> ScraperRunHistory | None:
        existing = self._repository.get_by_id(run_id)
        if existing is None:
            return None
        if existing.status not in ACTIVE_SCRAPER_RUN_STATUSES:
            return existing
        now = heartbeat_at or datetime.now(UTC)
        updates: dict[str, object] = {"last_heartbeat_at": now}
        if progress_current is not None:
            updates["progress_current"] = progress_current
        if progress_total is not None:
            updates["progress_total"] = progress_total
        return self._repository.update(replace(existing, **updates))

    def complete_cancelled_run(
        self,
        run_id: UUID,
        *,
        handoff: ScraperImportHandoff | None = None,
        finished_at: datetime | None = None,
        output_json_path: str | None = None,
        import_batch_id: UUID | None = None,
        error_message: str | None = None,
    ) -> ScraperRunHistory | None:
        existing = self._repository.get_by_id(run_id)
        if existing is None:
            return None
        if existing.status == ScraperRunStatus.CANCELLED:
            return existing
        finished = finished_at or datetime.now(UTC)
        metrics = compute_handoff_metrics(handoff) if handoff is not None else {
            "total_rows": 0,
            "website_count": 0,
            "email_count": 0,
            "phone_count": 0,
            "instagram_count": 0,
            "linkedin_count": 0,
            "facebook_count": 0,
            "youtube_count": 0,
            "x_count": 0,
        }
        return self._repository.update(
            replace(
                existing,
                status=ScraperRunStatus.CANCELLED,
                finished_at=finished,
                duration_ms=duration_ms_between(existing.started_at, finished),
                error_message=error_message,
                output_json_path=output_json_path if output_json_path is not None else existing.output_json_path,
                import_batch_id=import_batch_id if import_batch_id is not None else existing.import_batch_id,
                **metrics,
            )
        )

    def cancel_run(
        self,
        run_id: UUID,
        *,
        reason: str | None = None,
        finished_at: datetime | None = None,
    ) -> ScraperRunHistory | None:
        existing = self._repository.get_by_id(run_id)
        if existing is None:
            return None
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

    def force_stop_run(
        self,
        run_id: UUID,
        *,
        reason: str,
    ) -> ScraperRunHistory | None:
        """Force an active run into a terminal cancelled state (stale / delete path)."""
        existing = self._repository.get_by_id(run_id)
        if existing is None:
            return None
        if existing.status not in ACTIVE_SCRAPER_RUN_STATUSES:
            return existing
        if existing.status == ScraperRunStatus.RUNNING:
            return self.cancel_run(run_id, reason=reason)
        return self.complete_cancelled_run(run_id, error_message=reason)

    def is_stale_active_run(
        self,
        run: ScraperRunHistory,
        *,
        now: datetime | None = None,
        stale_heartbeat_seconds: float = DEFAULT_STALE_HEARTBEAT_SECONDS,
    ) -> bool:
        if run.status not in ACTIVE_SCRAPER_RUN_STATUSES:
            return False
        current = now or datetime.now(UTC)
        heartbeat = run.last_heartbeat_at or run.started_at
        if heartbeat.tzinfo is None:
            heartbeat = heartbeat.replace(tzinfo=UTC)
        else:
            heartbeat = heartbeat.astimezone(UTC)
        age = (current - heartbeat).total_seconds()
        if age >= stale_heartbeat_seconds:
            return True
        if run.cancel_requested_at is not None:
            requested = run.cancel_requested_at
            if requested.tzinfo is None:
                requested = requested.replace(tzinfo=UTC)
            else:
                requested = requested.astimezone(UTC)
            if (current - requested).total_seconds() >= stale_heartbeat_seconds:
                return True
        return False

    def _commit_visible(self) -> None:
        """Flush+commit so cooperative workers in other sessions can observe cancel state."""
        self._repository._session.flush()
        self._repository._session.commit()

    def _refresh_run(self, run_id: UUID) -> ScraperRunHistory | None:
        self._repository._session.expire_all()
        return self._repository.get_by_id(run_id)

    def stop_active_run_for_delete(
        self,
        run_id: UUID,
        *,
        organization_id: UUID,
        requested_by: UUID,
        wait_seconds: float | None = None,
        poll_seconds: float | None = None,
        stale_heartbeat_seconds: float | None = None,
    ) -> ScraperRunHistory | None:
        """Stop an active run via existing cancel semantics, then ensure terminal state.

        1. Request cooperative cancel when still running.
        2. Wait briefly for the worker to observe cancel and finish.
        3. If still active and stale (or wait elapsed), force-cancel the DB row.
        4. If still active after force, raise — do not delete blindly.
        """
        resolved_wait = DEFAULT_DELETE_STOP_WAIT_SECONDS if wait_seconds is None else wait_seconds
        resolved_poll = DEFAULT_DELETE_STOP_POLL_SECONDS if poll_seconds is None else poll_seconds
        resolved_stale = (
            DEFAULT_STALE_HEARTBEAT_SECONDS if stale_heartbeat_seconds is None else stale_heartbeat_seconds
        )

        existing = self._repository.get_by_id(run_id)
        if existing is None or existing.organization_id != organization_id:
            raise KeyError(f"Scraper run not found: {run_id}")
        if existing.status not in ACTIVE_SCRAPER_RUN_STATUSES:
            return existing

        if self.is_stale_active_run(existing, stale_heartbeat_seconds=resolved_stale):
            forced = self.force_stop_run(
                run_id,
                reason="Takılı kalmış çalıştırma silme için durduruldu.",
            )
            self._commit_visible()
            return forced

        if existing.status == ScraperRunStatus.RUNNING:
            self.request_cancel(
                run_id,
                organization_id=organization_id,
                requested_by=requested_by,
            )
            self._commit_visible()

        deadline = time.monotonic() + max(0.0, resolved_wait)
        while time.monotonic() < deadline:
            current = self._refresh_run(run_id)
            if current is None:
                return None
            if current.status not in ACTIVE_SCRAPER_RUN_STATUSES:
                return current
            time.sleep(max(0.05, resolved_poll))

        current = self._refresh_run(run_id)
        if current is None:
            return None
        if current.status not in ACTIVE_SCRAPER_RUN_STATUSES:
            return current

        # Wait elapsed: treat as orphaned / non-cooperative and force-stop.
        forced = self.force_stop_run(
            run_id,
            reason="Silme için çalıştırma durduruldu.",
        )
        self._commit_visible()
        current = self._refresh_run(run_id)
        if current is None:
            return None
        if current.status in ACTIVE_SCRAPER_RUN_STATUSES:
            raise ScraperRunHistoryDeleteError(
                "Çalıştırma durdurulamadı. History kaydı silinmedi."
            )
        return current

    def cancel_running_for_adapter(
        self,
        *,
        adapter_key: str,
        organization_id: UUID | None,
        reason: str,
    ) -> list[ScraperRunHistory]:
        cancelled: list[ScraperRunHistory] = []
        for run in self.list_running_for_adapter(adapter_key=adapter_key, organization_id=organization_id):
            stopped = self.cancel_run(run.id, reason=reason)
            if stopped is not None:
                cancelled.append(stopped)
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

    def delete_run(
        self,
        run_id: UUID,
        *,
        organization_id: UUID,
        requested_by: UUID | None = None,
        wait_seconds: float | None = None,
        poll_seconds: float | None = None,
        stale_heartbeat_seconds: float | None = None,
    ) -> None:
        """Stop (if needed) then delete a run history row and its handoff artifacts.

        Does not delete fairs, customers, import batches, or other primary CRM data.
        Linked FKs that point at this run (e.g. enrichment state) are SET NULL by the DB.
        """
        existing = self._repository.get_by_id(run_id)
        if existing is None or existing.organization_id != organization_id:
            raise KeyError(f"Scraper run not found: {run_id}")

        if existing.status in ACTIVE_SCRAPER_RUN_STATUSES:
            if requested_by is None:
                raise ScraperRunHistoryDeleteError(
                    "Aktif çalıştırma silinemedi: durdurma için kullanıcı kimliği gerekli."
                )
            stopped = self.stop_active_run_for_delete(
                run_id,
                organization_id=organization_id,
                requested_by=requested_by,
                wait_seconds=wait_seconds,
                poll_seconds=poll_seconds,
                stale_heartbeat_seconds=stale_heartbeat_seconds,
            )
            if stopped is None:
                return
            existing = stopped
            if existing.status in ACTIVE_SCRAPER_RUN_STATUSES:
                raise ScraperRunHistoryDeleteError(
                    "Çalıştırma durdurulamadı. History kaydı silinmedi."
                )

        delete_handoff_artifacts_for_run(
            run_id,
            output_json_path=existing.output_json_path,
            output_excel_path=existing.output_excel_path,
        )
        deleted = self._repository.hard_delete_by_id(run_id, organization_id=organization_id)
        if not deleted:
            raise KeyError(f"Scraper run not found: {run_id}")

    def get_dashboard_run_stats(self, organization_id: UUID) -> dict[str, int | str | None]:
        latest = self._repository.get_latest_for_organization(organization_id)
        return {
            "last_run_adapter": latest.adapter_key if latest is not None else None,
            "failed_scraper_count": self._repository.count_failed_for_organization(organization_id),
        }


def create_run_history_service(session: Session) -> ScraperRunHistoryService:
    return ScraperRunHistoryService(ScraperRunHistoryRepository(session))

