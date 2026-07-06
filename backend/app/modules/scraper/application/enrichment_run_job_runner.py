"""Background execution for customer contact enrichment runs."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.modules.scraper.application.fair_scraper_import_automation import create_and_analyze_import_batch_from_handoff
from app.modules.scraper.core.scraper_run_logger import CappedWarningRunLogger, DbScraperRunLogger, ScraperRunLogger
from app.modules.scraper.domain.enrichment_run_summary import build_enrichment_run_summary
from app.modules.scraper.domain.requested_output_fields import (
    normalize_requested_fields,
    output_field_capabilities_from_supports,
)
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.handoff_storage import write_handoff_json
from app.modules.scraper.manifests.customer_contact_enrichment_manifest import CUSTOMER_CONTACT_ENRICHMENT_MANIFEST
from app.modules.scraper.services.enrichment_run_executor import execute_enrichment_run
from app.modules.scraper.services.adapter_instance_resolver import resolve_requested_fields
from app.modules.scraper.services.scraper_run_history_service import create_run_history_service
from app.modules.scraper.services.scraper_run_log_service import create_run_log_service

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EnrichmentRunJobCommand:
    run_id: UUID
    organization_id: UUID
    adapter_key: str
    user_id: UUID
    access_token: str = ""
    limit: int | None = 50
    requested_fields: list[str] | None = None
    dry_run: bool = False
    max_pages: int = 10


class EnrichmentRunJobRunner:
    def __init__(
        self,
        session_factory: Callable[[], Session] | None = None,
        executor: Callable[..., tuple[list, ScraperImportHandoff]] | None = None,
    ) -> None:
        self._session_factory = session_factory or SessionLocal
        self._executor = executor or execute_enrichment_run

    def run_enrichment(self, command: EnrichmentRunJobCommand) -> None:
        db = self._session_factory()
        run_logger: ScraperRunLogger | None = None
        try:
            history_service = create_run_history_service(db)
            log_service = create_run_log_service(db)
            run_logger = CappedWarningRunLogger(
                DbScraperRunLogger(command.run_id, log_service, db),
            )
            if command.requested_fields is not None:
                requested_fields = normalize_requested_fields(
                    list(command.requested_fields),
                    capabilities=output_field_capabilities_from_supports(
                        CUSTOMER_CONTACT_ENRICHMENT_MANIFEST.supports
                    ),
                )
            else:
                requested_fields = resolve_requested_fields(
                    db,
                    command.organization_id,
                    command.adapter_key,
                )
                requested_fields = normalize_requested_fields(
                    requested_fields,
                    capabilities=output_field_capabilities_from_supports(
                        CUSTOMER_CONTACT_ENRICHMENT_MANIFEST.supports
                    ),
                )

            run_logger.info(
                "started",
                "Müşteri iletişim zenginleştirme başladı",
                metadata={
                    "limit": command.limit,
                    "dry_run": command.dry_run,
                    "requested_fields": requested_fields,
                },
            )
            db.commit()

            results, handoff = self._executor(
                db,
                command.organization_id,
                run_id=command.run_id,
                run_logger=run_logger,
                limit=command.limit,
                requested_fields=requested_fields,
                max_pages=command.max_pages,
            )

            import_batch_id: UUID | None = None
            import_rows = len(handoff.canonical_rows or [])
            output_json_path: str | None = None

            if import_rows > 0:
                output_json_path = write_handoff_json(
                    handoff,
                    command.run_id,
                    adapter_key=command.adapter_key,
                    fair_id=None,
                    source_url=None,
                    run_logger=run_logger,
                )

            if not command.dry_run and import_rows > 0:
                try:
                    import_batch_id = create_and_analyze_import_batch_from_handoff(
                        db,
                        organization_id=command.organization_id,
                        fair_id=None,
                        run_id=command.run_id,
                        handoff=handoff,
                        adapter_key=command.adapter_key,
                        source_url="customer-contact-enrichment",
                        user_id=command.user_id,
                        access_token=command.access_token,
                    )
                    run_logger.info(
                        "import_batch_created",
                        "Import batch hazırlandı",
                        metadata={"import_batch_id": str(import_batch_id), "total_rows": import_rows},
                    )
                except Exception as exc:
                    logger.exception("Failed to create enrichment import batch run id=%s", command.run_id)
                    if isinstance(run_logger, CappedWarningRunLogger):
                        run_logger.flush_suppressed_warnings()
                    run_logger.error("import_batch_failed", str(exc))
                    self._fail_run(db, command.run_id, f"Import batch oluşturulamadı: {exc}")
                    return
            elif command.dry_run:
                run_logger.info(
                    "dry_run",
                    "Önizleme modu: import batch oluşturulmadı",
                    metadata={"import_rows": import_rows},
                )
            else:
                run_logger.warning(
                    "no_rows",
                    "Zenginleştirme tamamlandı ancak import satırı oluşmadı",
                    metadata={"customers_scanned": len(results)},
                )

            summary = build_enrichment_run_summary(
                results,
                dry_run=command.dry_run,
                import_batch_id=import_batch_id,
                import_rows=import_rows,
            )
            summary["run_id"] = str(command.run_id)
            if isinstance(run_logger, CappedWarningRunLogger):
                run_logger.flush_suppressed_warnings()
            run_logger.success(
                "run_finished",
                "Müşteri iletişim zenginleştirme tamamlandı",
                metadata=summary,
            )
            history_service.complete_run(
                command.run_id,
                handoff=handoff,
                output_json_path=output_json_path,
                import_batch_id=import_batch_id,
            )
            db.commit()
            logger.info(
                "Completed enrichment run id=%s scanned=%s import_rows=%s",
                command.run_id,
                summary["customers_scanned"],
                import_rows,
            )
        except Exception as exc:
            logger.exception("Enrichment run failed id=%s", command.run_id)
            if run_logger is not None:
                if isinstance(run_logger, CappedWarningRunLogger):
                    run_logger.flush_suppressed_warnings()
                run_logger.error("failed", str(exc))
            self._fail_run(db, command.run_id, str(exc))
        finally:
            db.close()

    def _fail_run(self, db: Session, run_id: UUID, error_message: str) -> None:
        try:
            history_service = create_run_history_service(db)
            history_service.fail_run(run_id, error_message=error_message)
            db.commit()
        except Exception:
            logger.exception("Failed to record enrichment run failure id=%s", run_id)
            db.rollback()
