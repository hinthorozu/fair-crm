"""Supported platform database keys for backup/restore operations."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from app.core.config import get_settings
from app.shared.database_backup.connection import parse_database_url
from app.shared.database_backup.formats import BackupFormat


class DatabaseKey(StrEnum):
    KYROX_CORE = "kyrox_core"
    FAIR_CRM = "fair_crm"


SUPPORTED_DATABASE_KEYS: frozenset[DatabaseKey] = frozenset(DatabaseKey)

DATABASE_KEY_SORT_FIELDS: frozenset[str] = frozenset(key.value for key in DatabaseKey)

DATABASE_LABELS: dict[DatabaseKey, str] = {
    DatabaseKey.KYROX_CORE: "KYROX Core",
    DatabaseKey.FAIR_CRM: "FAIR CRM",
}


def database_label(database_key: DatabaseKey | str) -> str:
    return DATABASE_LABELS[DatabaseKey(database_key)]


def infer_database_key_from_backup_filename(file_name: str) -> DatabaseKey | None:
    name = Path(file_name).name.lower()
    for key in DatabaseKey:
        if name.startswith(f"{key.value}_backup_"):
            return key
    if name.startswith("fair_crm_data_package_"):
        return DatabaseKey.FAIR_CRM
    if name.startswith("faircrm_backup_") or name.startswith("faircrm_data_package_"):
        return DatabaseKey.FAIR_CRM
    return None


def assert_upload_database_key_matches(*, file_name: str, database_key: DatabaseKey) -> None:
    inferred = infer_database_key_from_backup_filename(file_name)
    if inferred is not None and inferred != database_key:
        raise ValueError(
            f"Uploaded file name indicates {inferred.value} backup; "
            f"selected target database is {database_key.value}"
        )


def parse_database_keys(raw: list[str] | None) -> list[DatabaseKey]:
    if not raw:
        return [DatabaseKey.FAIR_CRM]
    if not raw:
        raise ValueError("At least one database must be selected")
    seen: set[DatabaseKey] = set()
    parsed: list[DatabaseKey] = []
    for item in raw:
        key = DatabaseKey(item)
        if key not in seen:
            seen.add(key)
            parsed.append(key)
    if not parsed:
        raise ValueError("At least one database must be selected")
    return parsed


def resolve_database_url(database_key: DatabaseKey | str) -> str:
    key = DatabaseKey(database_key)
    settings = get_settings()
    if key == DatabaseKey.KYROX_CORE:
        return settings.kyrox_core_database_url
    return settings.database_url


def expected_database_name(database_key: DatabaseKey | str) -> str:
    key = DatabaseKey(database_key)
    return parse_database_url(resolve_database_url(key)).database


def assert_target_url_matches_database_key(database_url: str, database_key: DatabaseKey | str) -> None:
    key = DatabaseKey(database_key)
    actual = parse_database_url(database_url).database
    expected = expected_database_name(key)
    if actual != expected:
        raise ValueError(
            f"TARGET_DATABASE_URL points to database {actual!r}; "
            f"restore job target is {key.value} ({expected!r})"
        )


def validate_backup_format_for_database(database_key: DatabaseKey, backup_format: BackupFormat) -> None:
    if database_key == DatabaseKey.KYROX_CORE and backup_format == BackupFormat.UNIVERSAL_DATA_PACKAGE:
        raise ValueError("Universal data package backups are only supported for fair_crm")


def resolve_alembic_workdir(database_key: DatabaseKey | str) -> Path:
    key = DatabaseKey(database_key)
    repo_root = Path(__file__).resolve().parents[4]
    if key == DatabaseKey.KYROX_CORE:
        settings = get_settings()
        if settings.kyrox_core_repo_path:
            return Path(settings.kyrox_core_repo_path).resolve()
        raise ValueError(
            "KYROX_CORE_REPO_PATH is required to run alembic migrations for kyrox_core restores"
        )
    return repo_root
