"""Background scraper execution for adapter detail test runs (no CRM / import writes)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.scraper.adapters import register_builtin_adapters
from app.modules.scraper.application.fair_scraper_job_runner import _scrape_and_export
from app.modules.scraper.core.browser_service import BrowserConfig, BrowserService, create_browser_service
from app.modules.scraper.core.playwright_availability import PlaywrightBrowserNotInstalledError
from app.modules.scraper.core.scraper_registry import ScraperAdapterRegistry
from app.modules.scraper.core.scraper_run_logger import CappedWarningRunLogger, DbScraperRunLogger, ScraperRunLogger
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.handoff_storage import write_handoff_excel_file, write_handoff_json
from app.modules.scraper.services.adapter_instance_resolver import resolve_engine_key, resolve_requested_fields
from app.modules.scraper.services.scraper_run_history_service import create_run_history_service
from app.modules.scraper.services.scraper_run_log_service import create_run_log_service
from app.modules.scraper.types.scraper_context import ScraperContext
from app.modules.scraper.validators.website_validator import clear_validation_cache

logger = logging.getLogger(__name__)

TEST_FAIR_NAME = "Adapter Test"


@dataclass(frozen=True)
class AdapterTestRunJobCommand:
    run_id: UUID
    organization_id: UUID
    adapter_key: str
    input_url: str
    output_json: bool = True
    output_excel: bool = False
    max_pages: int | None = None


class AdapterTestRunJobRunner:
    def __init__(
        self,
        session_factory: Callable[[], Session] | None = None,
        scrape_executor: Callable[..., ScraperImportHandoff] | None = None,
    ) -> None:
        self._session_factory = session_factory or SessionLocal
        self._scrape_executor = scrape_executor

    def run_adapter_test(self, command: AdapterTestRunJobCommand) -> None:
        db = self._session_factory()
        run_logger: ScraperRunLogger | None = None
        try:
            history_service = create_run_history_service(db)
            log_service = create_run_log_service(db)
            run_logger = CappedWarningRunLogger(
                DbScraperRunLogger(command.run_id, log_service, db),
            )
            context_options: dict[str, object] = {"run_logger": run_logger}
            if command.max_pages is not None:
                context_options["max_pages"] = command.max_pages
            context = ScraperContext(
                fair_id=None,
                list_url=command.input_url,
                options=context_options,
                metadata={"fair_name": TEST_FAIR_NAME},
            )
            started_metadata: dict[str, object] = {
                "adapter_key": command.adapter_key,
                "url": command.input_url,
            }
            if command.max_pages is not None:
                started_metadata["max_pages"] = command.max_pages
            run_logger.info(
                "started",
                (
                    f"{command.adapter_key} test çalışması başladı"
                    + (
                        f" (en fazla {command.max_pages} liste sayfası)"
                        if command.max_pages is not None
                        else ""
                    )
                ),
                metadata=started_metadata,
            )
            db.commit()

            engine_key = resolve_engine_key(db, command.organization_id, command.adapter_key)
            requested_fields = resolve_requested_fields(db, command.organization_id, command.adapter_key)
            context = replace(
                context,
                options={**context.options, "requested_fields": requested_fields},
            )
            clear_validation_cache()
            if self._scrape_executor is not None:
                handoff = self._scrape_executor(
                    instance_key=command.adapter_key,
                    engine_key=engine_key,
                    context=context,
                    fair_name=TEST_FAIR_NAME,
                    fair_year=None,
                    source_url=command.input_url,
                    run_logger=run_logger,
                )
            else:
                handoff = asyncio.run(
                    self._execute_with_browser(
                        instance_key=command.adapter_key,
                        engine_key=engine_key,
                        context=context,
                        input_url=command.input_url,
                        run_logger=run_logger,
                    )
                )

            output_json_path: str | None = None
            output_excel_path: str | None = None
            if command.output_json:
                output_json_path = write_handoff_json(
                    handoff,
                    command.run_id,
                    adapter_key=command.adapter_key,
                    fair_id=None,
                    source_url=command.input_url,
                    run_logger=run_logger,
                )
            if command.output_excel:
                output_excel_path = write_handoff_excel_file(
                    handoff,
                    command.run_id,
                    adapter_key=command.adapter_key,
                    source_url=command.input_url,
                    requested_fields=requested_fields,
                    run_logger=run_logger,
                )
            if isinstance(run_logger, CappedWarningRunLogger):
                run_logger.flush_suppressed_warnings()
            total_rows = len(handoff.canonical_rows or [])
            run_logger.success(
                "completed",
                f"{total_rows} kayıt tamamlandı",
                metadata={"total_rows": total_rows},
            )
            history_service.complete_run(
                command.run_id,
                handoff=handoff,
                output_json_path=output_json_path,
                output_excel_path=output_excel_path,
            )
            db.commit()
            logger.info("Completed adapter test run id=%s rows=%s", command.run_id, total_rows)
        except PlaywrightBrowserNotInstalledError as exc:
            logger.warning("%s", exc)
            if run_logger is not None:
                if isinstance(run_logger, CappedWarningRunLogger):
                    run_logger.flush_suppressed_warnings()
                run_logger.error("failed", str(exc))
            self._fail_run(db, command.run_id, str(exc))
        except Exception as exc:
            logger.exception("Adapter test run failed id=%s", command.run_id)
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
        input_url: str,
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
                fair_name=TEST_FAIR_NAME,
                fair_year=None,
                source_url=input_url,
                run_logger=run_logger,
                browser=browser,
            )

    def _fail_run(self, db: Session, run_id: UUID, error_message: str) -> None:
        try:
            history_service = create_run_history_service(db)
            history_service.fail_run(run_id, error_message=error_message)
            db.commit()
        except Exception:
            logger.exception("Failed to record adapter test run failure id=%s", run_id)
            db.rollback()
