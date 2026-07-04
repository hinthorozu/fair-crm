"""End-to-end Foodist exhibitor scraper runner for Import Preview handoff."""



from __future__ import annotations



import argparse

import asyncio

import json

import logging

import sys

from dataclasses import dataclass
from uuid import UUID, uuid4

from pathlib import Path

from typing import Any

from app.modules.scraper.infrastructure.handoff_storage import serialize_handoff_to_canonical_json



BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:

    sys.path.insert(0, str(BACKEND_ROOT))



from datetime import UTC, datetime



from sqlalchemy import create_engine

from sqlalchemy.engine import Engine

from sqlalchemy.orm import Session, sessionmaker



from app.core.config import get_settings

from app.modules.scraper.adapters.tuyap_new_adapter import TuyapNewAdapter

from app.modules.scraper.core.browser_service import BrowserConfig, BrowserService, create_browser_service

from app.modules.scraper.core.scraper_run_logger import (
    CappedWarningRunLogger,
    DbScraperRunLogger,
    ScraperRunLogger,
)

from app.modules.scraper.exporters.scraper_excel_exporter import write_handoff_excel

from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportExporter, ScraperImportHandoff

from app.modules.scraper.normalizers.company_normalizer import CompanyNormalizer

from app.modules.scraper.services.scraper_run_history_service import (

    ScraperRunHistoryService,

    create_run_history_service,

)

from app.modules.scraper.services.scraper_run_log_service import create_run_log_service

from app.modules.scraper.types.scraper_context import ScraperContext

from app.modules.scraper.types.scraper_result import ScraperResult

from app.modules.scraper.types.scraper_site import ScraperSiteKey

from app.modules.scraper.validators.website_validator import clear_validation_cache



ADAPTER_KEY = ScraperSiteKey.TUYAP_NEW



logger = logging.getLogger(__name__)





@dataclass

class ScraperRunSession:

    engine: Engine

    session: Session

    run_id: Any

    run_logger: ScraperRunLogger

    history_service: ScraperRunHistoryService



    def complete(

        self,

        handoff: ScraperImportHandoff,

        *,

        output_json_path: str | None,

        output_excel_path: str | None,

    ) -> None:

        if isinstance(self.run_logger, CappedWarningRunLogger):

            self.run_logger.flush_suppressed_warnings()

        total_rows = len(handoff.canonical_rows or [])

        self.run_logger.success(

            "completed",

            f"{total_rows} kayıt tamamlandı",

            metadata={"total_rows": total_rows},

        )

        self.history_service.complete_run(

            self.run_id,

            handoff=handoff,

            output_json_path=output_json_path,

            output_excel_path=output_excel_path,

        )

        self.session.commit()

        logger.info("Recorded completed scraper run id=%s", self.run_id)



    def fail(

        self,

        error_message: str,

        *,

        output_json_path: str | None,

        output_excel_path: str | None,

    ) -> None:

        if isinstance(self.run_logger, CappedWarningRunLogger):

            self.run_logger.flush_suppressed_warnings()

        self.run_logger.error("failed", error_message)

        self.history_service.fail_run(

            self.run_id,

            error_message=error_message,

            output_json_path=output_json_path,

            output_excel_path=output_excel_path,

        )

        self.session.commit()

        logger.info("Recorded failed scraper run id=%s", self.run_id)



    def close(self) -> None:

        self.session.close()

        self.engine.dispose()





def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(

        description="Run Foodist exhibitor scraper and export Import Preview handoff JSON.",

    )

    parser.add_argument("--url", required=True, help="Foodist exhibitor list page URL")

    parser.add_argument("--fair-name", default=None, help="Target fair display name for handoff metadata")

    parser.add_argument("--fair-year", type=int, default=None, help="Target fair year for handoff metadata")

    parser.add_argument(

        "--max-pages",

        type=int,

        default=None,

        help="Maximum list pages to scrape (default: all discovered pagination pages)",

    )

    parser.add_argument(

        "--scrape-detail",

        action="store_true",

        help="Visit each brand detail page to enrich contact fields",

    )

    parser.add_argument("--output", default=None, help="Output JSON file path (prints to stdout if omitted)")

    parser.add_argument(

        "--excel-output",

        default=None,

        help="Optional .xlsx export path for review and comparison",

    )

    return parser





def parse_args(argv: list[str] | None = None) -> argparse.Namespace:

    return build_parser().parse_args(argv)





def _browser_config_for_scrape() -> BrowserConfig:

    settings = get_settings()

    config = BrowserConfig.from_settings(settings)

    channel = config.channel or "msedge"

    return BrowserConfig(

        headless=config.headless,

        timeout_ms=config.timeout_ms,

        user_agent=config.user_agent,

        channel=channel,

    )





def _build_context(args: argparse.Namespace, *, run_logger: ScraperRunLogger | None = None) -> ScraperContext:

    metadata: dict[str, Any] = {}

    if args.fair_name:

        metadata["fair_name"] = args.fair_name

    if args.fair_year is not None:

        metadata["fair_year"] = args.fair_year



    options: dict[str, Any] = {"scrape_detail": args.scrape_detail}

    if args.max_pages is not None:

        options["max_pages"] = args.max_pages

    if run_logger is not None:

        options["run_logger"] = run_logger



    return ScraperContext(

        list_url=args.url,

        options=options,

        metadata=metadata,

    )





def open_run_session(

    *,

    input_url: str,

    fair_name: str | None,

    fair_year: int | None,

    started_at: datetime | None = None,

) -> ScraperRunSession:

    settings = get_settings()

    engine = create_engine(settings.database_url)

    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    session = session_factory()

    history_service = create_run_history_service(session)

    log_service = create_run_log_service(session)

    run = history_service.start_run(

        adapter_key=ADAPTER_KEY,

        input_url=input_url,

        fair_name=fair_name,

        fair_year=fair_year,

        started_at=started_at,

    )

    run_logger = CappedWarningRunLogger(DbScraperRunLogger(run.id, log_service, session))

    run_logger.info(

        "started",

        "TÜYAP New adapter çalışıyor",

        metadata={"adapter_key": ADAPTER_KEY, "url": input_url},

    )

    session.commit()

    return ScraperRunSession(

        engine=engine,

        session=session,

        run_id=run.id,

        run_logger=run_logger,

        history_service=history_service,

    )





async def scrape_and_export(

    args: argparse.Namespace,

    *,

    adapter: TuyapNewAdapter,

    run_logger: ScraperRunLogger | None = None,

) -> ScraperImportHandoff:

    context = _build_context(args, run_logger=run_logger)



    logger.info(

        "Starting Foodist scrape url=%r max_pages=%s scrape_detail=%s",

        args.url,

        args.max_pages if args.max_pages is not None else "unlimited",

        args.scrape_detail,

    )

    raw_rows = await adapter.scrape_async(context)

    normalized, warnings = CompanyNormalizer().normalize_many(raw_rows)

    for warning in warnings:

        if run_logger is not None:

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

    logger.info(

        "Scrape finished raw_count=%s normalized_count=%s warnings=%s",

        result.raw_count,

        result.normalized_count,

        len(result.warnings),

    )



    return ScraperImportExporter().export(

        result,

        fair_name=args.fair_name,

        fair_year=args.fair_year,

        source_url=args.url,

    )





async def run_pipeline(

    args: argparse.Namespace,

    *,

    adapter: TuyapNewAdapter | None = None,

    browser: BrowserService | None = None,

    run_logger: ScraperRunLogger | None = None,

) -> ScraperImportHandoff:

    if adapter is not None:

        return await scrape_and_export(args, adapter=adapter, run_logger=run_logger)



    active_browser = browser or create_browser_service(_browser_config_for_scrape())

    active_adapter = TuyapNewAdapter(browser=active_browser)

    async with active_browser:

        return await scrape_and_export(args, adapter=active_adapter, run_logger=run_logger)





def handoff_to_dict(
    handoff: ScraperImportHandoff,
    *,
    run_id: Any | None = None,
    adapter_key: str = ADAPTER_KEY,
) -> dict[str, Any]:
    resolved_run_id = run_id or uuid4()
    fair_id_raw = handoff.metadata.get("fair_id") if handoff.metadata else None
    fair_id = UUID(str(fair_id_raw)) if fair_id_raw else None
    return serialize_handoff_to_canonical_json(
        handoff,
        adapter_key=adapter_key,
        run_id=resolved_run_id,
        fair_id=fair_id,
        source_url=(handoff.metadata or {}).get("source_url"),
    )





def write_handoff_json(

    handoff: ScraperImportHandoff,

    output_path: str | None,

    *,

    run_logger: ScraperRunLogger | None = None,

) -> str:

    payload = handoff_to_dict(handoff)

    text = json.dumps(payload, ensure_ascii=False, indent=2)

    if output_path:

        path = Path(output_path)

        path.write_text(f"{text}\n", encoding="utf-8")

        logger.info("Wrote Import handoff JSON to %s", path.resolve())

        if run_logger is not None:

            run_logger.info(

                "export_json",

                "JSON üretildi",

                metadata={"path": str(path.resolve())},

            )

    elif run_logger is not None:

        run_logger.info("export_json", "JSON üretildi", metadata={"path": None})

    return text





def main(argv: list[str] | None = None) -> int:

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

    args = parse_args(argv)



    if not args.url.strip():

        logger.error("URL must not be empty.")

        return 1

    if args.max_pages is not None and args.max_pages < 1:

        logger.error("--max-pages must be at least 1 when provided.")

        return 1



    started_at = datetime.now(UTC)

    run_session: ScraperRunSession | None = None

    try:

        run_session = open_run_session(

            input_url=args.url,

            fair_name=args.fair_name,

            fair_year=args.fair_year,

            started_at=started_at,

        )

        clear_validation_cache()

        handoff = asyncio.run(run_pipeline(args, run_logger=run_session.run_logger))

        text = write_handoff_json(handoff, args.output, run_logger=run_session.run_logger)

        if not args.output:

            print(text)

        excel_path: str | None = None

        if args.excel_output:

            excel_path = write_handoff_excel(handoff, args.excel_output)

            logger.info("Wrote review Excel to %s", excel_path)

            run_session.run_logger.info(

                "export_excel",

                "Excel üretildi",

                metadata={"path": excel_path},

            )

        run_session.complete(

            handoff,

            output_json_path=args.output,

            output_excel_path=excel_path,

        )

        return 0

    except KeyboardInterrupt:

        logger.error("Scrape interrupted by user.")

        if run_session is not None:

            run_session.fail(

                "Scrape interrupted by user",

                output_json_path=args.output,

                output_excel_path=args.excel_output,

            )

        return 130

    except Exception as exc:

        logger.exception("Foodist scraper failed: %s", exc)

        if run_session is not None:

            run_session.fail(

                str(exc),

                output_json_path=args.output,

                output_excel_path=args.excel_output,

            )

        return 1

    finally:

        if run_session is not None:

            run_session.close()





if __name__ == "__main__":

    raise SystemExit(main())

