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
from app.modules.scraper.core.browser_service import BrowserConfig, BrowserService, create_browser_service
from app.modules.scraper.core.playwright_availability import PlaywrightBrowserNotInstalledError
from app.modules.scraper.core.scraper_registry import ScraperAdapterRegistry
from app.modules.scraper.core.scraper_run_logger import CappedWarningRunLogger, DbScraperRunLogger, ScraperRunLogger
from app.modules.scraper.domain.requested_output_fields import filter_handoff_by_requested_fields
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportExporter, ScraperImportHandoff
from app.modules.scraper.infrastructure.handoff_storage import write_handoff_excel_file, write_handoff_json
from app.modules.scraper.normalizers.company_normalizer import CompanyNormalizer
from app.modules.scraper.services.scraper_run_history_service import (
    ScraperRunHistoryService,
    create_run_history_service,
)
from app.modules.scraper.application.fair_scraper_import_automation import create_and_analyze_import_batch_from_handoff
from app.modules.scraper.services.adapter_instance_resolver import (
    resolve_engine_key,
    resolve_output_formats,
    resolve_requested_fields,
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
) -> ScraperContext:
    metadata: dict[str, Any] = {"fair_name": fair_name}
    if fair_year is not None:
        metadata["fair_year"] = fair_year

    options: dict[str, Any] = dict(scraper_config or {})
    options["run_logger"] = run_logger
    if requested_fields is not None:
        options["requested_fields"] = requested_fields

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
            context = _build_scraper_context(
                fair_id=fair.id,
                source_url=source_url,
                fair_name=fair.name,
                fair_year=fair_year,
                scraper_config=fair.scraper_config,
                run_logger=run_logger,
                requested_fields=requested_fields,
            )
            run_logger.info(
                "started",
                f"{adapter_key} adapter çalışıyor",
                metadata={"adapter_key": adapter_key, "url": source_url, "fair_id": str(fair.id)},
            )
            db.commit()

            clear_validation_cache()
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

            output_json_path: str | None = None
            output_excel_path: str | None = None
            if output_formats.json_handoff:
                output_json_path = write_handoff_json(
                    handoff,
                    command.run_id,
                    adapter_key=adapter_key,
                    fair_id=fair.id,
                    source_url=source_url,
                    run_logger=run_logger,
                )
            if output_formats.excel:
                output_excel_path = write_handoff_excel_file(
                    handoff,
                    command.run_id,
                    adapter_key=adapter_key,
                    fair_id=fair.id,
                    source_url=source_url,
                    requested_fields=requested_fields,
                    run_logger=run_logger,
                )
            if isinstance(run_logger, CappedWarningRunLogger):
                run_logger.flush_suppressed_warnings()
            total_rows = len(handoff.canonical_rows or [])
            import_batch_id = None
            if total_rows > 0:
                try:
                    import_batch_id = create_and_analyze_import_batch_from_handoff(
                        db,
                        organization_id=command.organization_id,
                        fair_id=fair.id,
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
                    if isinstance(run_logger, CappedWarningRunLogger):
                        run_logger.flush_suppressed_warnings()
                    run_logger.error("import_batch_failed", str(exc))
                    self._fail_run(db, command.run_id, f"Import batch oluşturulamadı: {exc}")
                    return
            else:
                run_logger.warning(
                    "no_rows",
                    "Scraper tamamlandı ancak kayıt bulunamadı; import batch oluşturulmadı.",
                    metadata={"total_rows": 0},
                )
            run_logger.success(
                "completed",
                f"{total_rows} kayıt tamamlandı",
                metadata={"total_rows": total_rows, "import_batch_id": str(import_batch_id) if import_batch_id else None},
            )
            history_service.complete_run(
                command.run_id,
                handoff=handoff,
                output_json_path=output_json_path,
                output_excel_path=output_excel_path,
                import_batch_id=import_batch_id,
            )
            db.commit()
            logger.info("Completed fair scraper run id=%s rows=%s", command.run_id, total_rows)
        except PlaywrightBrowserNotInstalledError as exc:
            logger.warning("%s", exc)
            if run_logger is not None:
                if isinstance(run_logger, CappedWarningRunLogger):
                    run_logger.flush_suppressed_warnings()
                run_logger.error("failed", str(exc))
            self._fail_run(db, command.run_id, str(exc))
        except Exception as exc:
            logger.exception("Fair scraper run failed id=%s", command.run_id)
            if run_logger is not None:
                if isinstance(run_logger, CappedWarningRunLogger):
                    run_logger.flush_suppressed_warnings()
                run_logger.error("failed", str(exc))
            self._fail_run(db, command.run_id, str(exc))
        finally:
            db.close()

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

    def _fail_run(self, db: Session, run_id: UUID, error_message: str) -> None:
        try:
            history_service = create_run_history_service(db)
            history_service.fail_run(run_id, error_message=error_message)
            db.commit()
        except Exception:
            logger.exception("Failed to record scraper run failure id=%s", run_id)
            db.rollback()
