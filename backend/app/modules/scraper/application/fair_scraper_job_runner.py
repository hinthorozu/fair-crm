"""Background scraper execution for fair-linked runs."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
from app.modules.scraper.adapters import register_builtin_adapters
from app.modules.scraper.application.fair_scraper_import_automation import create_and_analyze_import_batch_from_handoff
from app.modules.scraper.core.browser_service import BrowserConfig, BrowserService, create_browser_service
from app.modules.scraper.core.playwright_availability import PlaywrightBrowserNotInstalledError
from app.modules.scraper.core.scraper_registry import ScraperAdapterRegistry
from app.modules.scraper.core.scraper_run_logger import CappedWarningRunLogger, DbScraperRunLogger, ScraperRunLogger
from app.modules.scraper.domain.requested_output_fields import filter_handoff_by_requested_fields
from app.modules.scraper.exporters.scraper_artifact_export import ArtifactExportBundle, export_scraper_artifacts
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportExporter, ScraperImportHandoff
from app.modules.scraper.normalizers.company_normalizer import CompanyNormalizer
from app.modules.scraper.services.adapter_instance_resolver import (
    resolve_engine_key,
    resolve_output_formats,
    resolve_requested_fields,
)
from app.modules.scraper.services.scraper_run_cancellation import (
    RunCancelChecker,
    ScraperRunCancelledError,
)
from app.modules.scraper.services.scraper_run_history_service import (
    ScraperRunHistoryService,
    create_run_history_service,
)
from app.modules.scraper.services.scraper_run_log_service import create_run_log_service
from app.modules.scraper.types.scraper_context import ScraperContext
from app.modules.scraper.types.scraper_result import ScraperResult
from app.modules.scraper.validators.website_validator import clear_validation_cache

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FairScraperJobCommand:
    run_id: UUID
    organization_id: UUID
    fair_id: UUID
    user_id: UUID
    access_token: str = ""


def _fair_year_from_start_date(start_date) -> int | None:
    return start_date.year if start_date is not None else None


def _build_scraper_context(
    *,
    fair_id: UUID,
    source_url: str,
    fair_name: str,
    fair_year: int | None,
    scraper_config: dict[str, Any] | None,
    run_logger: ScraperRunLogger,
    requested_fields: list[str] | None = None,
    cancel_checker: RunCancelChecker | None = None,
) -> ScraperContext:
    metadata: dict[str, Any] = {"fair_name": fair_name}
    if fair_year is not None:
        metadata["fair_year"] = fair_year

    options: dict[str, Any] = dict(scraper_config or {})
    options["run_logger"] = run_logger
    if requested_fields is not None:
        options["requested_fields"] = requested_fields
    if cancel_checker is not None:
        options["cancel_checker"] = cancel_checker

    return ScraperContext(
        fair_id=fair_id,
        list_url=source_url,
        options=options,
        metadata=metadata,
    )


async def _scrape_and_export(
    *,
    instance_key: str,
    engine_key: str | None = None,
    context: ScraperContext,
    fair_name: str,
    fair_year: int | None,
    source_url: str,
    run_logger: ScraperRunLogger,
    browser: BrowserService,
) -> ScraperImportHandoff:
    resolved_engine_key = (engine_key or instance_key).strip().lower()
    registry = ScraperAdapterRegistry()
    register_builtin_adapters(registry, browser=browser)
    adapter = registry.get(resolved_engine_key)
    normalizer = CompanyNormalizer()

    raw_rows = await adapter.scrape_async(context)
    normalized, warnings = normalizer.normalize_many(raw_rows)
    for warning in warnings:
        run_logger.warning("detail_scrape_progress", warning)

    result = ScraperResult(
        site_key=adapter.site_key,
        fair_id=context.fair_id,
        companies=normalized,
        raw_count=len(raw_rows),
        normalized_count=len(normalized),
        errors=[],
        warnings=warnings,
        metadata={"adapter": adapter.display_name, **context.metadata},
        scraped_at=datetime.now(UTC),
    )
    handoff = ScraperImportExporter().export(
        result,
        fair_name=fair_name,
        fair_year=fair_year,
        source_url=source_url,
    )
    requested_fields = context.options.get("requested_fields")
    return filter_handoff_by_requested_fields(handoff, requested_fields)


def _combine_warning_messages(*messages: str | None) -> str | None:
    parts = [message.strip() for message in messages if message and message.strip()]
    if not parts:
        return None
    return " | ".join(parts)


class FairScraperJobRunner:
    def __init__(
        self,
        session_factory: Callable[[], Session] | None = None,
        scrape_executor: Callable[..., ScraperImportHandoff] | None = None,
    ) -> None:
        self._session_factory = session_factory or SessionLocal
        self._scrape_executor = scrape_executor

    def run_fair_scraper(self, command: FairScraperJobCommand) -> None:
        db = self._session_factory()
        run_logger: ScraperRunLogger | None = None
        try:
            fair_repo = SqlAlchemyFairRepository(db)
            fair = fair_repo.get_by_id(command.organization_id, command.fair_id)
            if fair is None:
                logger.warning("Fair not found for scraper run id=%s fair_id=%s", command.run_id, command.fair_id)
                return

            adapter_key = (fair.adapter_key or "").strip()
            source_url = (fair.source_url or "").strip()
            if not adapter_key or not source_url:
                self._fail_run(db, command.run_id, "Adapter or source URL is not configured")
                return

            history_service = create_run_history_service(db)
            log_service = create_run_log_service(db)
            run_logger = CappedWarningRunLogger(
                DbScraperRunLogger(command.run_id, log_service, db),
            )
            engine_key = resolve_engine_key(db, command.organization_id, adapter_key)
            requested_fields = resolve_requested_fields(db, command.organization_id, adapter_key)
            output_formats = resolve_output_formats(db, command.organization_id, adapter_key)
            fair_year = _fair_year_from_start_date(fair.start_date)
            cancel_checker = RunCancelChecker(self._session_factory, command.run_id)
            context = _build_scraper_context(
                fair_id=fair.id,
                source_url=source_url,
                fair_name=fair.name,
                fair_year=fair_year,
                scraper_config=fair.scraper_config,
                run_logger=run_logger,
                requested_fields=requested_fields,
                cancel_checker=cancel_checker,
            )
            run_logger.info(
                "started",
                f"{adapter_key} adapter çalışıyor",
                metadata={"adapter_key": adapter_key, "url": source_url, "fair_id": str(fair.id)},
            )
            db.commit()

            clear_validation_cache()
            if cancel_checker.is_cancel_requested():
                self._cancel_run(db, command.run_id, run_logger=run_logger)
                return
            try:
                if self._scrape_executor is not None:
                    handoff = self._scrape_executor(
                        instance_key=adapter_key,
                        engine_key=engine_key,
                        context=context,
                        fair_name=fair.name,
                        fair_year=fair_year,
                        source_url=source_url,
                        run_logger=run_logger,
                    )
                else:
                    handoff = asyncio.run(
                        self._execute_with_browser(
                            instance_key=adapter_key,
                            engine_key=engine_key,
                            context=context,
                            fair_name=fair.name,
                            fair_year=fair_year,
                            source_url=source_url,
                            run_logger=run_logger,
                        )
                    )
            except ScraperRunCancelledError:
                self._cancel_run(db, command.run_id, run_logger=run_logger)
                return
            except PlaywrightBrowserNotInstalledError as scrape_exc:
                logger.warning("%s", scrape_exc)
                if isinstance(run_logger, CappedWarningRunLogger):
                    run_logger.flush_suppressed_warnings()
                run_logger.error("failed", str(scrape_exc))
                self._fail_run(db, command.run_id, str(scrape_exc))
                return
            except Exception as scrape_exc:
                logger.exception("Fair scraper scrape failed id=%s", command.run_id)
                if isinstance(run_logger, CappedWarningRunLogger):
                    run_logger.flush_suppressed_warnings()
                run_logger.error("failed", str(scrape_exc))
                self._fail_run(db, command.run_id, str(scrape_exc))
                return

            if cancel_checker.is_cancel_requested():
                self._cancel_run(db, command.run_id, run_logger=run_logger)
                return

            # Scraping succeeded: secondary artifact/import failures must not fail the run.
            self._finalize_successful_scrape(
                db=db,
                command=command,
                history_service=history_service,
                run_logger=run_logger,
                handoff=handoff,
                adapter_key=adapter_key,
                fair_id=fair.id,
                source_url=source_url,
                requested_fields=requested_fields,
                output_formats=output_formats,
            )
        except Exception as exc:
            logger.exception("Fair scraper run failed id=%s", command.run_id)
            if run_logger is not None:
                if isinstance(run_logger, CappedWarningRunLogger):
                    run_logger.flush_suppressed_warnings()
                run_logger.error("failed", str(exc))
            self._fail_run(db, command.run_id, str(exc))
        finally:
            db.close()

    def _finalize_successful_scrape(
        self,
        *,
        db: Session,
        command: FairScraperJobCommand,
        history_service: ScraperRunHistoryService,
        run_logger: ScraperRunLogger,
        handoff: ScraperImportHandoff,
        adapter_key: str,
        fair_id: UUID,
        source_url: str,
        requested_fields: list[str] | None,
        output_formats,
    ) -> None:
        artifacts: ArtifactExportBundle = export_scraper_artifacts(
            handoff,
            command.run_id,
            output_formats=output_formats,
            adapter_key=adapter_key,
            fair_id=fair_id,
            source_url=source_url,
            requested_fields=requested_fields,
            run_logger=run_logger,
        )
        if isinstance(run_logger, CappedWarningRunLogger):
            run_logger.flush_suppressed_warnings()

        total_rows = len(handoff.canonical_rows or [])
        import_batch_id = None
        import_warning: str | None = None
        if total_rows > 0:
            try:
                import_batch_id = create_and_analyze_import_batch_from_handoff(
                    db,
                    organization_id=command.organization_id,
                    fair_id=fair_id,
                    run_id=command.run_id,
                    handoff=handoff,
                    adapter_key=adapter_key,
                    source_url=source_url,
                    user_id=command.user_id,
                    access_token=command.access_token,
                )
                run_logger.info(
                    "import_batch_created",
                    "Import batch hazırlandı",
                    metadata={"import_batch_id": str(import_batch_id), "total_rows": total_rows},
                )
            except Exception as exc:
                logger.exception("Failed to create import batch for fair scraper run id=%s", command.run_id)
                import_warning = f"Import batch oluşturulamadı: {exc}"
                run_logger.warning(
                    "import_batch_failed",
                    import_warning,
                    metadata={"total_rows": total_rows, "error": str(exc)},
                )
        else:
            run_logger.warning(
                "no_rows",
                "Scraper tamamlandı ancak kayıt bulunamadı; import batch oluşturulmadı.",
                metadata={"total_rows": 0},
            )

        warning_message = _combine_warning_messages(artifacts.warning_message(), import_warning)
        completed_metadata: dict[str, object] = {"total_rows": total_rows}
        if import_batch_id is not None:
            completed_metadata["import_batch_id"] = str(import_batch_id)
        if warning_message:
            completed_metadata["artifact_warnings"] = warning_message
        run_logger.success(
            "completed",
            f"{total_rows} kayıt tamamlandı",
            metadata=completed_metadata,
        )
        history_service.complete_run(
            command.run_id,
            handoff=handoff,
            output_json_path=artifacts.json_path,
            output_excel_path=artifacts.excel_path,
            import_batch_id=import_batch_id,
            warning_message=warning_message,
        )
        db.commit()
        logger.info(
            "Completed fair scraper run id=%s rows=%s json=%s excel=%s warnings=%s",
            command.run_id,
            total_rows,
            bool(artifacts.json_path),
            bool(artifacts.excel_path),
            bool(warning_message),
        )

    async def _execute_with_browser(
        self,
        *,
        instance_key: str,
        engine_key: str,
        context: ScraperContext,
        fair_name: str,
        fair_year: int | None,
        source_url: str,
        run_logger: ScraperRunLogger,
    ) -> ScraperImportHandoff:
        settings = get_settings()
        browser_config = BrowserConfig.from_settings(settings)
        browser = create_browser_service(browser_config)
        async with browser:
            return await _scrape_and_export(
                instance_key=instance_key,
                engine_key=engine_key,
                context=context,
                fair_name=fair_name,
                fair_year=fair_year,
                source_url=source_url,
                run_logger=run_logger,
                browser=browser,
            )

    def _cancel_run(
        self,
        db: Session,
        run_id: UUID,
        *,
        run_logger: ScraperRunLogger | None,
    ) -> None:
        try:
            history_service = create_run_history_service(db)
            history_service.mark_cancelling(run_id)
            if run_logger is not None:
                if isinstance(run_logger, CappedWarningRunLogger):
                    run_logger.flush_suppressed_warnings()
                run_logger.info("cancelled", "Fuar scraper çalışması iptal edildi / silindi")
            history_service.complete_cancelled_run(
                run_id,
                error_message="Kullanıcı tarafından durduruldu.",
            )
            db.commit()
        except Exception:
            logger.exception("Failed to record fair scraper run cancellation id=%s", run_id)
            db.rollback()

    def _fail_run(self, db: Session, run_id: UUID, error_message: str) -> None:
        try:
            history_service = create_run_history_service(db)
            history_service.fail_run(run_id, error_message=error_message)
            db.commit()
        except Exception:
            logger.exception("Failed to record scraper run failure id=%s", run_id)
            db.rollback()
