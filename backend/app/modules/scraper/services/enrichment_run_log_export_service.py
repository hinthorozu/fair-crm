"""Build TXT/JSON exports for enrichment run console logs."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.modules.scraper.domain.scraper_run_history import ScraperRunHistory
from app.modules.scraper.domain.scraper_run_log import ScraperRunLog
from app.modules.scraper.services.enrichment_run_log_txt_formatter import build_console_txt_export
from app.modules.scraper.services.enrichment_run_summary_loader import load_enrichment_summary_for_run
from app.modules.scraper.services.scraper_run_log_service import ScraperRunLogService

_EXPORT_FORMATS = frozenset({"txt", "json"})


def is_supported_export_format(value: str | None) -> bool:
    return (value or "").strip().lower() in _EXPORT_FORMATS


def build_export_filename(*, export_format: str, exported_at: datetime | None = None) -> str:
    moment = exported_at or datetime.now(UTC)
    stamp = moment.strftime("%Y-%m-%d-%H-%M-%S")
    normalized = export_format.strip().lower()
    return f"fair-crm-enrichment-run-{stamp}.{normalized}"


def _resolve_scope(run: ScraperRunHistory) -> str:
    return "fair" if run.fair_id is not None else "org"


def _resolve_counts(summary: dict[str, Any] | None) -> tuple[int | None, int | None, int | None]:
    if summary is None:
        return None, None, None
    processed = summary.get("customers_scanned")
    failed = summary.get("failed")
    found = summary.get("found")
    not_found = summary.get("not_found")
    if isinstance(processed, int) and isinstance(failed, int):
        if isinstance(found, int) and isinstance(not_found, int):
            success = found + not_found
        else:
            success = processed - failed
        return processed, success, failed
    return None, None, None


def _resolve_duration_seconds(run: ScraperRunHistory) -> int | None:
    if run.duration_ms is not None:
        return max(0, run.duration_ms // 1000)
    if run.finished_at is None:
        return None
    delta = run.finished_at - run.started_at
    return max(0, int(delta.total_seconds()))


def _format_iso_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _resolve_import_batch_id(run: ScraperRunHistory, summary: dict[str, Any] | None) -> str | None:
    if summary is not None:
        batch_id = summary.get("import_batch_id")
        if batch_id:
            return str(batch_id)
    if run.import_batch_id is not None:
        return str(run.import_batch_id)
    return None


def _resolve_dry_run(summary: dict[str, Any] | None) -> bool | None:
    if summary is None or "dry_run" not in summary:
        return None
    return bool(summary["dry_run"])


def build_run_export_payload(
    run: ScraperRunHistory,
    summary: dict[str, Any] | None,
) -> dict[str, Any]:
    processed, success, failed = _resolve_counts(summary)
    return {
        "id": str(run.id),
        "scope": _resolve_scope(run),
        "fair_id": str(run.fair_id) if run.fair_id is not None else None,
        "fair_name": run.fair_name,
        "status": run.status.value,
        "started_at": _format_iso_timestamp(run.started_at),
        "finished_at": _format_iso_timestamp(run.finished_at) if run.finished_at is not None else None,
        "duration_seconds": _resolve_duration_seconds(run),
        "processed": processed,
        "success": success,
        "failed": failed,
        "import_batch_id": _resolve_import_batch_id(run, summary),
        "dry_run": _resolve_dry_run(summary),
    }


def _serialize_log_for_json(log: ScraperRunLog) -> dict[str, Any]:
    return {
        "created_at": _format_iso_timestamp(log.created_at),
        "level": log.level.value,
        "step": log.step,
        "message": log.message,
    }


def build_json_export(
    run: ScraperRunHistory,
    logs: list[ScraperRunLog],
    summary: dict[str, Any] | None,
) -> str:
    payload = {
        "run": build_run_export_payload(run, summary),
        "logs": [_serialize_log_for_json(log) for log in logs],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_txt_export(logs: list[ScraperRunLog]) -> str:
    return build_console_txt_export(logs)


def export_enrichment_run_logs(
    *,
    run: ScraperRunHistory,
    run_log_service: ScraperRunLogService,
    export_format: str,
    exported_at: datetime | None = None,
) -> tuple[bytes, str, str]:
    normalized = export_format.strip().lower()
    if normalized not in _EXPORT_FORMATS:
        raise ValueError(f"Unsupported export format: {export_format}")

    summary = load_enrichment_summary_for_run(run_log_service, run.id)
    logs = run_log_service.list_all_logs(run.id)
    filename = build_export_filename(export_format=normalized, exported_at=exported_at)

    if normalized == "json":
        content = build_json_export(run, logs, summary)
        media_type = "application/json; charset=utf-8"
    else:
        content = build_txt_export(logs)
        media_type = "text/plain; charset=utf-8"

    return content.encode("utf-8"), filename, media_type
