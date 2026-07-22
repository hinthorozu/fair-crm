"""Secondary scraper artifact exporters (JSON, Excel, future formats).

Artifact production is intentionally decoupled from scrape success: each writer
runs independently and failures are collected as warnings instead of aborting
the run.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.modules.scraper.core.scraper_run_logger import ScraperRunLogger
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.handoff_storage import write_handoff_excel_file, write_handoff_json
from app.modules.scraper.services.adapter_instance_resolver import AdapterOutputFormats

logger = logging.getLogger(__name__)

ArtifactWriter = Callable[[], str]


@dataclass(frozen=True)
class ArtifactExportResult:
    key: str
    path: str | None = None
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.path is not None and self.error is None


@dataclass
class ArtifactExportBundle:
    results: list[ArtifactExportResult] = field(default_factory=list)

    def path_for(self, key: str) -> str | None:
        for result in self.results:
            if result.key == key and result.succeeded:
                return result.path
        return None

    @property
    def json_path(self) -> str | None:
        return self.path_for("json")

    @property
    def excel_path(self) -> str | None:
        return self.path_for("excel")

    @property
    def failures(self) -> list[ArtifactExportResult]:
        return [result for result in self.results if result.error]

    @property
    def has_failures(self) -> bool:
        return bool(self.failures)

    def warning_message(self) -> str | None:
        if not self.failures:
            return None
        parts = [f"{failure.key}: {failure.error}" for failure in self.failures]
        return "Artifact export uyarısı — " + "; ".join(parts)


def _safe_export(
    *,
    key: str,
    writer: ArtifactWriter,
    run_logger: ScraperRunLogger | None,
    success_event: str,
    failure_event: str,
    success_message: str,
) -> ArtifactExportResult:
    try:
        path = writer()
        if run_logger is not None:
            run_logger.info(success_event, success_message, metadata={"path": path})
        return ArtifactExportResult(key=key, path=path)
    except Exception as exc:
        message = str(exc) or exc.__class__.__name__
        logger.exception("Scraper artifact export failed key=%s", key)
        if run_logger is not None:
            run_logger.warning(
                failure_event,
                f"{key} üretilemedi: {message}",
                metadata={"artifact": key, "error": message},
            )
        return ArtifactExportResult(key=key, error=message)


def export_scraper_artifacts(
    handoff: ScraperImportHandoff,
    run_id: UUID,
    *,
    output_formats: AdapterOutputFormats | None = None,
    output_json: bool | None = None,
    output_excel: bool | None = None,
    adapter_key: str,
    fair_id: UUID | None = None,
    source_url: str | None = None,
    requested_fields: list[str] | None = None,
    base_dir: Any = None,
    run_logger: ScraperRunLogger | None = None,
) -> ArtifactExportBundle:
    """Run requested artifact writers independently and collect per-format outcomes."""
    want_json = output_formats.json_handoff if output_formats is not None else bool(output_json)
    want_excel = output_formats.excel if output_formats is not None else bool(output_excel)
    bundle = ArtifactExportBundle()

    if want_json:
        # Skip duplicate success log inside write_handoff_json by not passing run_logger there;
        # _safe_export owns success/failure logging for a consistent artifact pipeline.
        bundle.results.append(
            _safe_export(
                key="json",
                writer=lambda: write_handoff_json(
                    handoff,
                    run_id,
                    adapter_key=adapter_key,
                    fair_id=fair_id,
                    source_url=source_url,
                    base_dir=base_dir,
                    run_logger=None,
                ),
                run_logger=run_logger,
                success_event="export_json",
                failure_event="export_json_failed",
                success_message="JSON üretildi",
            )
        )

    if want_excel:
        bundle.results.append(
            _safe_export(
                key="excel",
                writer=lambda: write_handoff_excel_file(
                    handoff,
                    run_id,
                    adapter_key=adapter_key,
                    fair_id=fair_id,
                    source_url=source_url,
                    requested_fields=requested_fields,
                    base_dir=base_dir,
                    run_logger=None,
                ),
                run_logger=run_logger,
                success_event="export_excel",
                failure_event="export_excel_failed",
                success_message="Excel üretildi",
            )
        )

    return bundle
