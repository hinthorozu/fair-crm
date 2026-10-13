from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.scraper.infrastructure.persistence.models import ScraperRunHistoryModel, ScraperRunLogModel
from app.modules.fairs.domain.exceptions import TobbReviewConflict, TobbRunNotFound

TOBB_ADAPTER = "tobb_calendar"
ACTIVE = ("queued", "running", "cancel_requested", "cancelling")


def run_response(run: ScraperRunHistoryModel) -> dict:
    return {
        "id": str(run.id), "job_scope": "system", "organization_id": None,
        "job_type": "tobb_catalog_sync", "source_module": "fairs", "status": run.status,
        "requested_by": str(run.requested_by) if run.requested_by else None,
        "run_source": run.run_source, "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "duration_ms": run.duration_ms, "progress_current": run.progress_current,
        "progress_total": run.progress_total, "error_message": run.error_message,
        "progress_percent": min(100, round(100 * (run.progress_current or 0) / run.progress_total)) if run.progress_total else 0,
        "last_heartbeat_at": run.last_heartbeat_at.isoformat() if run.last_heartbeat_at else None,
        "cancel_requested_by": str(run.cancel_requested_by) if run.cancel_requested_by else None,
        "cancel_requested_at": run.cancel_requested_at.isoformat() if run.cancel_requested_at else None,
        "summary": run.summary_json or {},
    }


class SqlAlchemyTobbRunRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, run_id: UUID, *, lock: bool = False) -> ScraperRunHistoryModel | None:
        query = select(ScraperRunHistoryModel).where(ScraperRunHistoryModel.id == run_id,
            ScraperRunHistoryModel.adapter_key == TOBB_ADAPTER, ScraperRunHistoryModel.organization_id.is_(None))
        query = query.execution_options(populate_existing=True)
        return self.session.scalar(query.with_for_update() if lock else query)

    def active(self) -> ScraperRunHistoryModel | None:
        run = self.session.scalar(select(ScraperRunHistoryModel).where(
            ScraperRunHistoryModel.adapter_key == TOBB_ADAPTER, ScraperRunHistoryModel.status.in_(ACTIVE),
            ScraperRunHistoryModel.organization_id.is_(None)))
        if run is not None:
            from app.modules.scraper.services.scraper_run_history_service import create_run_history_service
            service = create_run_history_service(self.session)
            snapshot = service.get_run(run.id, organization_id=None)
            if snapshot is not None and service.is_stale_active_run(snapshot):
                run.status, run.finished_at = "failed", datetime.now(UTC)
                run.error_message = "Çalışmanın heartbeat süresi aşıldı; güvenli yeniden deneme gerekli"
                self.log(run.id, "stale_running", run.error_message, level="error")
                self.session.commit()
                return None
        return run

    def start(self, years: list[int], *, requested_by: UUID | None, automatic: bool = False,
              requested_by_label: str | None = None) -> tuple[ScraperRunHistoryModel, bool]:
        existing = self.active()
        if existing:
            return existing, False
        now = datetime.now(UTC)
        run = ScraperRunHistoryModel(id=uuid4(), adapter_key=TOBB_ADAPTER, status="queued", started_at=now,
            organization_id=None, requested_by=requested_by, run_source="tobb_weekly" if automatic else "tobb_manual",
            progress_current=0, progress_total=len(years), last_heartbeat_at=now,
            summary_json={"phase": "apply" if automatic else "fetch_preview", "years": years, "year_results": {},
                          "details": [], "requested_by_label": requested_by_label or "Sistem"})
        try:
            self.session.add(run)
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            existing = self.active()
            if existing is None:
                raise
            return existing, False
        self.log(run.id, "queued", "TOBB çalışması sıraya alındı")
        self.session.commit()
        return run, True

    def log(self, run_id: UUID, step: str, message: str, *, level: str = "info") -> None:
        self.session.add(ScraperRunLogModel(id=uuid4(), run_id=run_id, step=step, message=message,
                                         level=level, created_at=datetime.now(UTC)))

    def list_runs(self, *, limit: int = 50, offset: int = 0) -> list[dict]:
        return [run_response(run) for run in self.session.scalars(select(ScraperRunHistoryModel).where(
            ScraperRunHistoryModel.adapter_key == TOBB_ADAPTER, ScraperRunHistoryModel.organization_id.is_(None),
        ).order_by(ScraperRunHistoryModel.started_at.desc(), ScraperRunHistoryModel.id.desc()).offset(offset).limit(limit)).all()]

    def view(self, run) -> dict:
        return run_response(run)

    def get_view(self, run_id: UUID) -> dict:
        run = self.get(run_id)
        if run is None:
            raise TobbRunNotFound("TOBB çalışması bulunamadı")
        return run_response(run)

    def queue_apply(self, run_id: UUID):
        run = self.get(run_id, lock=True)
        active = self.active()
        if active:
            return active, False
        if run is None or run.status != "completed" or (run.summary_json or {}).get("phase") != "preview_ready":
            raise TobbReviewConflict("Güncel önizleme gereklidir")
        summary = dict(run.summary_json)
        summary.update(preview=dict(summary["year_results"]), year_results={}, phase="apply")
        run.summary_json, run.status, run.finished_at = summary, "queued", None
        return self._commit_queued(run)

    def queue_retry(self, run_id: UUID, *, user_id: UUID, user_label: str):
        run = self.get(run_id, lock=True)
        active = self.active()
        if active:
            return active, False
        if run is None or run.status != "failed":
            raise TobbReviewConflict("Yalnız başarısız çalışmalar yeniden denenebilir")
        summary = dict(run.summary_json or {})
        results = dict(summary.get("year_results", {}))
        if any(item.get("status") == "preview_stale" for item in results.values()):
            raise TobbReviewConflict("Değişen kaynak için yeni önizleme oluşturun")
        history = list(summary.get("retry_history", []))
        history.append({"at": datetime.now(UTC).isoformat(), "year_results": results,
                        "user_id": str(user_id), "user_label": user_label})
        summary["retry_history"] = history
        summary["year_results"] = {year: item for year, item in results.items() if item.get("status") == "completed"}
        summary["phase"] = "fetch_preview" if run.run_source == "tobb_manual" and not summary.get("preview") else "apply"
        run.summary_json, run.status, run.finished_at, run.error_message = summary, "queued", None, None
        return self._commit_queued(run)

    def _commit_queued(self, run):
        run.progress_current = sum(item.get("status") == "completed" for item in (run.summary_json or {}).get("year_results", {}).values())
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            active = self.active()
            if active:
                return active, False
            raise
        return run, True

    def queue_notification_retry(self, run_id: UUID) -> dict:
        run = self.get(run_id, lock=True)
        if run is None:
            raise TobbRunNotFound("TOBB çalışması bulunamadı")
        if run.status not in {"completed", "failed", "cancelled"} or (run.summary_json or {}).get("notification") != "failed":
            raise TobbReviewConflict("Yalnız teslim edilemeyen tamamlanmış çalışma bildirimi yeniden denenebilir")
        run.summary_json = {**(run.summary_json or {}), "notification": "pending"}
        self.log(run.id, "notification_retry_requested", "Super Admin bildirim teslimatını yeniden istedi")
        self.session.commit()
        return run_response(run)

    def request_cancel(self, run_id: UUID, *, user_id: UUID) -> dict:
        run = self.get(run_id, lock=True)
        if run is None:
            raise TobbRunNotFound("TOBB çalışması bulunamadı")
        if run.status in {"queued", "running"}:
            run.status = "cancel_requested"
            run.cancel_requested_at, run.cancel_requested_by = datetime.now(UTC), user_id
            self.log(run_id, "cancel_requested", "Super Admin işi durdurmak istedi")
            self.session.commit()
        return run_response(run)
