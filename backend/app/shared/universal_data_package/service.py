"""Vendor-independent business data export (Universal Data Package)."""

from __future__ import annotations

import json
import tempfile
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.activities.infrastructure.persistence.models import ActivityModel
from app.modules.contacts.infrastructure.persistence.models import ContactModel
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
from app.shared.database_backup.engine import BackupRunResult, sha256_file

StageCallback = Callable[[str], None]

ENTITY_EXPORTS: tuple[tuple[str, type], ...] = (
    ("customers", CustomerModel),
    ("fairs", FairModel),
    ("participations", CustomerFairParticipationModel),
    ("contacts", ContactModel),
    ("activities", ActivityModel),
)


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def _schema_version(session: Session) -> str | None:
    try:
        return session.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar_one_or_none()
    except Exception:
        return None


class UniversalDataPackageService:
    """Builds a portable ZIP of business entities for migration/export (not DR restore)."""

    def build_package(
        self,
        *,
        session: Session,
        organization_id: UUID,
        output_path: Path,
        on_stage: StageCallback | None = None,
    ) -> tuple[BackupRunResult, dict[str, Any]]:
        settings = get_settings()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if on_stage:
            on_stage("preparing")

        exported_at = datetime.now(tz=UTC)
        entity_payloads: dict[str, list[dict[str, Any]]] = {}
        entity_counts: dict[str, int] = {}

        if on_stage:
            on_stage("dumping")

        for file_stem, model in ENTITY_EXPORTS:
            rows = (
                session.query(model)
                .filter(model.organization_id == organization_id)
                .order_by(model.id)
                .all()
            )
            entity_payloads[file_stem] = [_row_to_dict(row) for row in rows]
            entity_counts[file_stem] = len(rows)

        schema_version = _schema_version(session)
        metadata_doc = {
            "organization_id": str(organization_id),
            "exported_at": exported_at.isoformat(),
            "source_database": settings.database_url.rsplit("/", 1)[-1].split("?")[0],
            "entity_counts": entity_counts,
        }

        file_entries: list[dict[str, str]] = []
        checksums: dict[str, str] = {}

        if on_stage:
            on_stage("compressing")

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            for file_stem, payload in entity_payloads.items():
                file_name = f"{file_stem}.json"
                file_path = tmp / file_name
                file_path.write_text(
                    json.dumps(payload, default=_json_default, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                checksums[file_name] = sha256_file(file_path)
                file_entries.append({"name": file_name, "sha256": checksums[file_name]})

            metadata_path = tmp / "metadata.json"
            metadata_path.write_text(
                json.dumps(metadata_doc, default=_json_default, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            checksums["metadata.json"] = sha256_file(metadata_path)
            file_entries.append({"name": "metadata.json", "sha256": checksums["metadata.json"]})

            manifest = {
                "app": "fair-crm",
                "version": settings.app_version,
                "exported_at": exported_at.isoformat(),
                "source_database": metadata_doc["source_database"],
                "schema_version": schema_version,
                "entity_counts": entity_counts,
                "files": file_entries,
                "checksums": checksums,
            }
            manifest_path = tmp / "manifest.json"
            manifest_path.write_text(
                json.dumps(manifest, default=_json_default, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.write(manifest_path, "manifest.json")
                archive.write(metadata_path, "metadata.json")
                for file_stem in entity_payloads:
                    json_name = f"{file_stem}.json"
                    archive.write(tmp / json_name, json_name)

        package_checksum = sha256_file(output_path)
        size_bytes = output_path.stat().st_size
        if size_bytes <= 0:
            raise ValueError("Universal data package is empty")

        result = BackupRunResult(
            path=output_path,
            size_bytes=size_bytes,
            checksum_sha256=package_checksum,
            toc_entry_count=len(file_entries) + 1,
            toolchain="python-zip",
        )
        return result, manifest
