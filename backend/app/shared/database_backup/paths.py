from datetime import UTC, datetime
from pathlib import Path

BACKUP_FILENAME_PREFIX = "faircrm_backup_"
BACKUP_EXTENSION = ".dump"


def get_repo_root() -> Path:
    # backend/app/shared/database_backup/paths.py -> fair-crm root
    return Path(__file__).resolve().parents[4]


def get_backups_dir(repo_root: Path | None = None) -> Path:
    root = repo_root or get_repo_root()
    return root / "backups"


def generate_backup_filename(*, now: datetime | None = None) -> str:
    ts = (now or datetime.now(tz=UTC)).strftime("%Y%m%d_%H%M%S")
    return f"{BACKUP_FILENAME_PREFIX}{ts}{BACKUP_EXTENSION}"


def resolve_backup_path(file_name: str, *, repo_root: Path | None = None) -> Path:
    if not file_name or file_name != Path(file_name).name:
        raise ValueError("Invalid backup file name")
    if ".." in file_name or "/" in file_name or "\\" in file_name:
        raise ValueError("Path traversal detected")
    if not file_name.endswith(BACKUP_EXTENSION):
        raise ValueError("Backup file must use .dump extension")
    backups_dir = get_backups_dir(repo_root).resolve()
    candidate = (backups_dir / file_name).resolve()
    if backups_dir not in candidate.parents and candidate != backups_dir:
        raise ValueError("Backup path escapes backups directory")
    return candidate
