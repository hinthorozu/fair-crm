from datetime import UTC, datetime
from pathlib import Path

from app.shared.database_backup.formats import (
    ALLOWED_BACKUP_EXTENSIONS,
    FORMAT_EXTENSIONS,
    BackupFormat,
)
from app.shared.database_backup.database_keys import DatabaseKey

BACKUP_FILENAME_PREFIX = "faircrm_backup_"
BACKUP_EXTENSION = ".dump"


def get_repo_root() -> Path:
    # backend/app/shared/database_backup/paths.py -> fair-crm root
    return Path(__file__).resolve().parents[4]


def get_backups_dir(repo_root: Path | None = None) -> Path:
    root = repo_root or get_repo_root()
    return root / "backups"


def get_restore_uploads_dir(repo_root: Path | None = None) -> Path:
    root = repo_root or get_repo_root()
    return root / "data" / "restore_uploads"


def get_restore_logs_dir(repo_root: Path | None = None) -> Path:
    root = repo_root or get_repo_root()
    return root / "data" / "restore_logs"


def relative_repo_path(path: Path) -> str:
    repo_root = get_repo_root().resolve()
    resolved = path.resolve()
    return str(resolved.relative_to(repo_root)).replace("\\", "/")


def generate_backup_filename(
    *,
    database_key: DatabaseKey = DatabaseKey.FAIR_CRM,
    backup_format: BackupFormat = BackupFormat.POSTGRESQL_DUMP,
    now: datetime | None = None,
) -> str:
    ts = (now or datetime.now(tz=UTC)).strftime("%Y%m%d_%H%M%S")
    if backup_format == BackupFormat.UNIVERSAL_DATA_PACKAGE:
        prefix = "fair_crm_data_package_"
    else:
        prefix = f"{database_key.value}_backup_"
    extension = FORMAT_EXTENSIONS[backup_format]
    return f"{prefix}{ts}{extension}"


def resolve_backup_path(file_name: str, *, repo_root: Path | None = None) -> Path:
    if not file_name or file_name != Path(file_name).name:
        raise ValueError("Invalid backup file name")
    if ".." in file_name or "/" in file_name or "\\" in file_name:
        raise ValueError("Path traversal detected")
    if not any(file_name.endswith(ext) for ext in ALLOWED_BACKUP_EXTENSIONS):
        raise ValueError(
            "Backup file must use a supported extension: "
            + ", ".join(sorted(ALLOWED_BACKUP_EXTENSIONS))
        )
    backups_dir = get_backups_dir(repo_root).resolve()
    candidate = (backups_dir / file_name).resolve()
    if backups_dir not in candidate.parents and candidate != backups_dir:
        raise ValueError("Backup path escapes backups directory")
    return candidate
