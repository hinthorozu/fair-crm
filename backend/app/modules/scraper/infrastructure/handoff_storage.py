"""Persist scraper JSON handoff files for Import Preview pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from app.modules.scraper.core.scraper_run_logger import ScraperRunLogger
from app.modules.scraper.exporters.scraper_excel_exporter import write_handoff_excel
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.shared.canonical_import.scraper_mapper import scraper_handoff_to_canonical
from app.shared.canonical_import.validator import validate_canonical_import

_BACKEND_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_HANDOFF_DIR = _BACKEND_ROOT / "data" / "scraper-handoff"


def resolve_handoff_path(run_id: UUID, *, base_dir: Path | None = None) -> Path:
    directory = base_dir or DEFAULT_HANDOFF_DIR
    return directory / f"{run_id}.json"


def resolve_handoff_excel_path(run_id: UUID, *, base_dir: Path | None = None) -> Path:
    directory = base_dir or DEFAULT_HANDOFF_DIR
    return directory / f"{run_id}.xlsx"


def _is_safe_handoff_artifact_path(path: Path, *, run_id: UUID, handoff_dir: Path) -> bool:
    """Only allow deleting files that belong to this run under the handoff directory."""
    try:
        resolved = path.resolve()
        handoff_root = handoff_dir.resolve()
    except OSError:
        return False
    if not resolved.is_relative_to(handoff_root):
        return False
    run_token = str(run_id)
    return run_token in resolved.name


def delete_handoff_artifacts_for_run(
    run_id: UUID,
    *,
    output_json_path: str | None = None,
    output_excel_path: str | None = None,
    base_dir: Path | None = None,
) -> None:
    """Best-effort cleanup of run-scoped handoff files. Never deletes unrelated paths."""
    handoff_dir = base_dir or DEFAULT_HANDOFF_DIR
    candidates: list[Path] = [
        resolve_handoff_path(run_id, base_dir=handoff_dir),
        resolve_handoff_excel_path(run_id, base_dir=handoff_dir),
    ]
    for stored in (output_json_path, output_excel_path):
        if stored:
            candidates.append(Path(stored))

    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if not _is_safe_handoff_artifact_path(candidate, run_id=run_id, handoff_dir=handoff_dir):
            continue
        if not resolved.is_file():
            continue
        try:
            resolved.unlink()
        except OSError:
            # Orphaning a file is preferable to failing history deletion.
            continue


def serialize_handoff_to_canonical_json(
    handoff: ScraperImportHandoff,
    *,
    adapter_key: str,
    run_id: UUID | None = None,
    fair_id: UUID | None = None,
    source_url: str | None = None,
) -> dict[str, Any]:
    document = scraper_handoff_to_canonical(
        handoff,
        adapter_key=adapter_key,
        run_id=run_id,
        fair_id=fair_id,
        source_url=source_url,
    )
    validated = validate_canonical_import(document)
    return validated.model_dump(mode="json")


def write_handoff_json(
    handoff: ScraperImportHandoff,
    run_id: UUID,
    *,
    adapter_key: str,
    fair_id: UUID | None = None,
    source_url: str | None = None,
    base_dir: Path | None = None,
    run_logger: ScraperRunLogger | None = None,
) -> str:
    path = resolve_handoff_path(run_id, base_dir=base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = serialize_handoff_to_canonical_json(
        handoff,
        adapter_key=adapter_key,
        run_id=run_id,
        fair_id=fair_id,
        source_url=source_url,
    )
    path.write_text(f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n", encoding="utf-8")
    resolved = str(path.resolve())
    if run_logger is not None:
        run_logger.info("export_json", "JSON üretildi", metadata={"path": resolved})
    return resolved


def write_handoff_excel_file(
    handoff: ScraperImportHandoff,
    run_id: UUID,
    *,
    adapter_key: str | None = None,
    fair_id: UUID | None = None,
    source_url: str | None = None,
    requested_fields: list[str] | None = None,
    base_dir: Path | None = None,
    run_logger: ScraperRunLogger | None = None,
) -> str:
    path = resolve_handoff_excel_path(run_id, base_dir=base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path = write_handoff_excel(
        handoff,
        str(path),
        requested_fields=requested_fields,
        adapter_key=adapter_key,
        run_id=run_id,
        fair_id=fair_id,
        source_url=source_url,
    )
    resolved = str(resolved_path)
    if run_logger is not None:
        run_logger.info("export_excel", "Excel üretildi", metadata={"path": resolved})
    return resolved
