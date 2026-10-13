"""TOBB domain worker on the existing detached executor and run-history store."""
from dataclasses import asdict
from datetime import UTC, date, datetime
from hashlib import sha256
import json
from uuid import UUID

import httpx

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.fairs.application.sync_tobb_system_fairs import SyncTobbSystemFairsUseCase
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
from app.modules.fairs.infrastructure.tobb_calendar import TobbCalendarClient, TobbFairRow
from app.modules.fairs.infrastructure.tobb_review_repository import SqlAlchemyTobbReviewRepository
from app.modules.fairs.infrastructure.tobb_run_repository import SqlAlchemyTobbRunRepository, run_response
from app.modules.scraper.services.scraper_run_cancellation import RunCancelChecker, ScraperRunCancelledError


def encoded_rows(rows: list[TobbFairRow]) -> list[dict]:
    return [{key: value.isoformat() if isinstance(value, date) else value
             for key, value in asdict(row).items()} for row in rows]


def digest(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


class TobbSyncJobRunner:
    def __init__(self, session_factory=SessionLocal, reader=None):
        self.session_factory = session_factory
        self.reader = reader or TobbCalendarClient()

    def run(self, run_id: UUID) -> None:
        session = self.session_factory()
        repository = SqlAlchemyTobbRunRepository(session)
        run = repository.get(run_id, lock=True)
        if run is not None and run.status == "cancel_requested":
            self._finish(repository, run, "cancelled")
            self._notify(repository, run)
            session.close()
            return
        if run is None or run.status != "queued":
            session.close()
            return
        summary = dict(run.summary_json or {})
        phase = summary["phase"]
        run.status = "running"
        repository.log(run.id, "started", "TOBB takvimi işleniyor")
        session.commit()
        checker = RunCancelChecker(self.session_factory, run_id, organization_id=None)

        def checkpoint():
            if checker.is_cancel_requested():
                raise ScraperRunCancelledError()
            if checker.current_status() not in {"queued", "running", "cancel_requested", "cancelling"}:
                raise ScraperRunCancelledError()
            checker.touch_heartbeat_if_active()

        try:
            fairs = SqlAlchemyFairRepository(session)
            reviews = SqlAlchemyTobbReviewRepository(session)
            sync = SyncTobbSystemFairsUseCase(fairs, self.reader, reviews)
            results = dict(summary.get("year_results", {}))
            for year in summary["years"]:
                checkpoint()
                previous = results.get(str(year), {})
                if previous.get("status") == "completed":
                    continue
                attempts = previous.get("attempts", 0)
                # Same bounded policy as Core platform jobs: at most three attempts.
                while attempts < 3:
                    checkpoint()
                    attempts += 1
                    try:
                        rows = self.reader.read(year)
                        checkpoint()
                        if phase == "fetch_preview":
                            plan = sync.execute(year, rows=rows, preview=True)
                            results[str(year)] = {"status": "preview_ready", "attempts": attempts,
                                "rows": encoded_rows(rows), "source_digest": digest(encoded_rows(rows)),
                                "catalog_digest": self._catalog_digest(fairs), "changes": list(plan.changes),
                                "inserted": plan.inserted, "updated": plan.updated, "reviews": plan.conflicts + len(plan.date_change_warnings)}
                        else:
                            if run.run_source == "tobb_manual":
                                shown = summary.get("preview", {}).get(str(year))
                                if shown is None or shown["source_digest"] != digest(encoded_rows(rows)) or shown["catalog_digest"] != self._catalog_digest(fairs):
                                    results[str(year)] = {"status": "preview_stale", "attempts": attempts,
                                                         "error": "Kaynak veya fuar değişti; önizlemeyi yenileyin"}
                                    break
                            partial = dict(results.get(str(year), {}))
                            partial_details = list(partial.get("details", []))
                            def commit_item(detail):
                                partial_details.append(detail)
                                results[str(year)] = {"status": "running", "attempts": attempts, "details": list(partial_details)}
                                summary["year_results"] = dict(results)
                                current_run = repository.get(run_id)
                                current_run.summary_json = dict(summary)
                                current_run.progress_current = sum(item.get("status") == "completed" for item in results.values())
                                session.commit()
                            result = sync.execute(year, rows=rows, checkpoint=checkpoint, committed_item=commit_item)
                            session.commit()
                            results[str(year)] = {"status": "completed", "attempts": attempts,
                                "inserted": result.inserted, "updated": result.updated,
                                "reviews": sum(item["action"] == "review" for item in result.changes),
                                "skipped": max(0, len(rows) - result.inserted - result.updated - result.conflicts),
                                "details": list(result.changes)}
                        break
                    except ScraperRunCancelledError:
                        raise
                    except Exception as exc:
                        session.rollback()
                        results[str(year)] = {"status": "failed", "attempts": attempts, "error": str(exc)}
                        repository.log(run_id, "year_failed", f"{year}: deneme {attempts} başarısız", level="error")
                        session.commit()
                run = repository.get(run_id, lock=True)
                summary["year_results"] = results
                run.summary_json = dict(summary)
                run.progress_current = len(results)
                repository.log(run_id, "year_finished", f"{year}: {results[str(year)]['status']}")
                session.commit()
                checkpoint()
            run = repository.get(run_id, lock=True)
            ready = phase == "fetch_preview" and all(item["status"] == "preview_ready" for item in results.values())
            successful = ready or all(item["status"] == "completed" for item in results.values())
            summary["phase"] = "preview_ready" if ready else "finished"
            run.summary_json = dict(summary)
            self._finish(repository, run, "completed" if successful else "failed")
            if not ready:
                self._notify(repository, run)
        except ScraperRunCancelledError:
            session.rollback()
            run = repository.get(run_id, lock=True)
            if run.status == "failed":
                return
            run.status = "cancelling"
            repository.log(run_id, "cancelling", "İş güvenli noktada durduruluyor")
            session.commit()
            self._finish(repository, run, "cancelled")
            self._notify(repository, run)
        except Exception as exc:
            session.rollback()
            run = repository.get(run_id, lock=True)
            run.error_message = str(exc)
            self._finish(repository, run, "failed")
            self._notify(repository, run)
        finally:
            session.close()

    @staticmethod
    def _catalog_digest(repository) -> str:
        return digest([asdict(fair) for fair in sorted(repository.list_system_fairs_for_source(source="tobb"), key=lambda item: str(item.id))])

    @staticmethod
    def _finish(repository, run, status):
        now = datetime.now(UTC)
        run.status, run.finished_at = status, now
        start = run.started_at.replace(tzinfo=UTC) if run.started_at.tzinfo is None else run.started_at
        run.duration_ms = int((now - start).total_seconds() * 1000)
        if status == "cancelled":
            run.error_message = None
        if (run.summary_json or {}).get("phase") != "preview_ready":
            run.summary_json = {**(run.summary_json or {}), "notification": "pending"}
        repository.log(run.id, status, f"TOBB çalışması: {status}")
        repository.session.commit()

    @staticmethod
    def _notify(repository, run):
        settings = get_settings()
        token = settings.kyrox_core_product_notification_token
        try:
            if not token:
                raise RuntimeError("Core uygulama içi bildirim anahtarı yapılandırılmamış")
            for attempt in range(1, 4):
                try:
                    with httpx.Client(timeout=10) as client:
                        response = client.post(f"{settings.kyrox_core_base_url.rstrip('/')}/api/v1/internal/notifications/in-app",
                            headers={"X-Kyrox-Notification-Token": token}, json={"subject": "TOBB çalışması tamamlandı",
                            "body": "Çalışma sonuçlarını ve bekleyen incelemeleri görüntüleyin.",
                            "idempotency_key": f"tobb-{run.id}-{run.status}",
                            "variables": {"path": f"/fairs?tobb_run={run.id}", "run_id": str(run.id), "status": run.status}})
                        response.raise_for_status()
                    break
                except httpx.HTTPError:
                    repository.log(run.id, "notification_retry", f"Core bildirim denemesi {attempt} başarısız", level="warning")
                    repository.session.commit()
                    if attempt == 3:
                        raise
            summary = dict(run.summary_json or {})
            summary["notification"] = "sent"
            summary["notification_attempts"] = attempt
        except Exception as exc:
            summary = dict(run.summary_json or {})
            summary["notification"] = "failed"
            summary["notification_error"] = str(exc)
            repository.log(run.id, "notification_failed", "Core bildirimi teslim edilemedi", level="error")
        run.summary_json = summary
        repository.session.commit()

    def retry_notification(self, run_id: UUID) -> None:
        with self.session_factory() as session:
            repository = SqlAlchemyTobbRunRepository(session)
            run = repository.get(run_id, lock=True)
            if run is not None and run.status in {"completed", "failed", "cancelled"}:
                self._notify(repository, run)
