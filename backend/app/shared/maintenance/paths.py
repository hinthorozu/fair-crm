from pathlib import Path

from app.shared.database_backup.paths import get_repo_root


def get_maintenance_dir(*, repo_root: Path | None = None) -> Path:
    root = repo_root or get_repo_root()
    return root / "scripts" / "maintenance"


def resolve_maintenance_file(relative_path: str, *, repo_root: Path | None = None) -> Path:
    if not relative_path or relative_path != Path(relative_path).as_posix():
        raise ValueError("Invalid maintenance file path")
    normalized = relative_path.replace("\\", "/")
    if ".." in normalized.split("/"):
        raise ValueError("Path traversal detected")
    maintenance_dir = get_maintenance_dir(repo_root=repo_root).resolve()
    candidate = (maintenance_dir / normalized).resolve()
    if maintenance_dir not in candidate.parents and candidate != maintenance_dir:
        raise ValueError("Maintenance path escapes maintenance directory")
    return candidate
