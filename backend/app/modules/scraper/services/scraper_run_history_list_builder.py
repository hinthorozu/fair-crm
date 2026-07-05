"""Build enriched scraper run history list API responses."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from app.modules.scraper.domain.adapter_engine import AdapterEngineType
from app.modules.scraper.domain.scraper_run_history import ScraperRunHistory, ScraperRunStatus
from app.modules.scraper.infrastructure.handoff_storage import resolve_handoff_excel_path, resolve_handoff_path
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import ScraperRunHistoryListRow
from app.modules.scraper.services.adapter_engine_service import AdapterEngineService


def _artifact_available(default_path: Path, stored_path: str | None) -> bool:
    if default_path.is_file():
        return True
    if stored_path:
        return Path(stored_path).is_file()
    return False


def _resolve_engine_type(engine_service: AdapterEngineService, engine_key: str | None) -> AdapterEngineType | None:
    if not engine_key:
        return None
    try:
        return engine_service.engine_type_for_key(engine_key)
    except KeyError:
        return None


def build_run_history_list_item(
    row: ScraperRunHistoryListRow,
    *,
    engine_service: AdapterEngineService,
) -> dict:
    run = row.run
    engine_key = row.adapter_engine_key or run.adapter_key
    engine_type = _resolve_engine_type(engine_service, engine_key)
    adapter_name = row.adapter_name or run.adapter_key

    json_path = resolve_handoff_path(run.id)
    excel_path = resolve_handoff_excel_path(run.id)
    outputs_ready = run.status == ScraperRunStatus.COMPLETED
    output_json_available = outputs_ready and _artifact_available(json_path, run.output_json_path)
    output_excel_available = outputs_ready and _artifact_available(excel_path, run.output_excel_path)

    output_base = f"/api/v1/scraper/runs/{run.id}/output"
    return {
        "run": run,
        "adapter_name": adapter_name,
        "engine_key": engine_key,
        "engine_type": engine_type,
        "output_json_available": output_json_available,
        "output_excel_available": output_excel_available,
        "json_download_url": f"{output_base}/json" if output_json_available else None,
        "json_view_url": f"{output_base}/json" if output_json_available else None,
        "excel_download_url": f"{output_base}/excel" if output_excel_available else None,
        "excel_view_url": f"{output_base}/excel" if output_excel_available else None,
    }


def build_run_history_detail_item(
    run: ScraperRunHistory,
    *,
    adapter_name: str | None,
    adapter_engine_key: str | None,
    engine_service: AdapterEngineService,
) -> dict:
    return build_run_history_list_item(
        ScraperRunHistoryListRow(
            run=run,
            adapter_name=adapter_name,
            adapter_engine_key=adapter_engine_key,
        ),
        engine_service=engine_service,
    )
