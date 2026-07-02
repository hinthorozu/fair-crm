from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.shared.database_backup.connection import PostgresConnection, parse_database_url
from app.shared.database_backup.paths import get_backups_dir, resolve_backup_path


class DatabaseBackupError(Exception):
    pass


@dataclass(frozen=True)
class BackupVerificationResult:
    path: Path
    size_bytes: int
    toc_entry_count: int


@dataclass(frozen=True)
class BackupRunResult:
    path: Path
    size_bytes: int
    checksum_sha256: str
    toc_entry_count: int
    toolchain: str


StageCallback = Callable[[str], None]


def _resolve_pg_tool(tool_name: str) -> str | None:
    found = shutil.which(tool_name)
    if found:
        return found
    for root in (
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
    ):
        if not root:
            continue
        pg_root = Path(root) / "PostgreSQL"
        if not pg_root.exists():
            continue
        matches = sorted(pg_root.rglob(f"{tool_name}.exe"), reverse=True)
        if matches:
            return str(matches[0])
    return None


def _docker_container_running(name: str) -> bool:
    if not shutil.which("docker"):
        return False
    result = subprocess.run(
        ["docker", "ps", "--filter", f"name=^/{name}$", "--filter", "status=running", "-q"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def _get_toolchain(conn: PostgresConnection) -> tuple[str, str | None]:
    pg_dump = _resolve_pg_tool("pg_dump")
    pg_restore = _resolve_pg_tool("pg_restore")
    if pg_dump and pg_restore:
        return "local", None
    settings = get_settings()
    container = getattr(settings, "postgres_docker_container", "kyrox-postgres-dev")
    if conn.is_localhost and _docker_container_running(container):
        return "docker", container
    raise DatabaseBackupError(
        "pg_dump/pg_restore not found and Docker fallback unavailable. "
        f"Install PostgreSQL client tools or start {container}."
    )


def _run_command(args: list[str], *, env: dict[str, str] | None = None) -> None:
    result = subprocess.run(args, capture_output=True, text=True, env=env, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise DatabaseBackupError(detail or f"Command failed: {' '.join(args)}")


def _docker_exec(container: str, args: list[str]) -> None:
    result = subprocess.run(["docker", "exec", container, *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise DatabaseBackupError(detail or f"docker exec failed: {args}")


def _docker_cp_from(container: str, remote_path: str, local_path: Path) -> None:
    _run_command(["docker", "cp", f"{container}:{remote_path}", str(local_path)])


def _docker_cp_to(container: str, local_path: Path, remote_path: str) -> None:
    _run_command(["docker", "cp", str(local_path), f"{container}:{remote_path}"])


def pg_dump_custom(
    *,
    database_url: str,
    output_path: Path,
    on_stage: StageCallback | None = None,
) -> BackupRunResult:
    conn = parse_database_url(database_url)
    toolchain, container = _get_toolchain(conn)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if on_stage:
        on_stage("preparing")
    if on_stage:
        on_stage("dumping")

    if toolchain == "local":
        pg_dump = _resolve_pg_tool("pg_dump")
        assert pg_dump
        env = os.environ.copy()
        env["PGPASSWORD"] = conn.password
        _run_command(
            [
                pg_dump,
                "-Fc",
                "-h",
                conn.host,
                "-p",
                str(conn.port),
                "-U",
                conn.user,
                "-d",
                conn.database,
                "-f",
                str(output_path),
                "--no-owner",
                "--no-acl",
            ],
            env=env,
        )
    else:
        assert container
        remote_path = f"/tmp/faircrm_backup_{uuid.uuid4().hex}.dump"
        _docker_exec(
            container,
            [
                "env",
                f"PGPASSWORD={conn.password}",
                "pg_dump",
                "-Fc",
                "-U",
                conn.user,
                "-d",
                conn.database,
                "-f",
                remote_path,
                "--no-owner",
                "--no-acl",
            ],
        )
        _docker_cp_from(container, remote_path, output_path)
        _docker_exec(container, ["rm", "-f", remote_path])

    if on_stage:
        on_stage("compressing")

    verified = verify_backup_dump(database_url=database_url, dump_path=output_path)
    checksum = sha256_file(output_path)
    return BackupRunResult(
        path=output_path,
        size_bytes=verified.size_bytes,
        checksum_sha256=checksum,
        toc_entry_count=verified.toc_entry_count,
        toolchain=toolchain,
    )


def verify_backup_dump(*, database_url: str, dump_path: Path) -> BackupVerificationResult:
    conn = parse_database_url(database_url)
    if not dump_path.exists():
        raise DatabaseBackupError(f"Backup file not found: {dump_path}")
    size_bytes = dump_path.stat().st_size
    if size_bytes <= 0:
        raise DatabaseBackupError(f"Backup file is empty: {dump_path}")

    toolchain, container = _get_toolchain(conn)
    if toolchain == "local":
        pg_restore = _resolve_pg_tool("pg_restore")
        assert pg_restore
        result = subprocess.run([pg_restore, "-l", str(dump_path)], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise DatabaseBackupError(result.stderr or result.stdout or "pg_restore -l failed")
        lines = result.stdout.splitlines()
    else:
        assert container
        remote_path = f"/tmp/faircrm_verify_{uuid.uuid4().hex}.dump"
        _docker_cp_to(container, dump_path, remote_path)
        try:
            proc = subprocess.run(
                ["docker", "exec", container, "pg_restore", "-l", remote_path],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                raise DatabaseBackupError(proc.stderr or proc.stdout or "pg_restore -l failed")
            lines = proc.stdout.splitlines()
        finally:
            _docker_exec(container, ["rm", "-f", remote_path])

    toc_entry_count = sum(1 for line in lines if ";" in line and any(ch.isdigit() for ch in line))
    return BackupVerificationResult(path=dump_path, size_bytes=size_bytes, toc_entry_count=toc_entry_count)


def pg_restore_custom(
    *,
    database_url: str,
    dump_path: Path,
) -> None:
    conn = parse_database_url(database_url)
    toolchain, container = _get_toolchain(conn)
    if toolchain == "local":
        pg_restore = _resolve_pg_tool("pg_restore")
        assert pg_restore
        env = os.environ.copy()
        env["PGPASSWORD"] = conn.password
        _run_command(
            [
                pg_restore,
                "-h",
                conn.host,
                "-p",
                str(conn.port),
                "-U",
                conn.user,
                "-d",
                conn.database,
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-acl",
                "--exit-on-error",
                str(dump_path),
            ],
            env=env,
        )
        return

    assert container
    remote_path = f"/tmp/faircrm_restore_{uuid.uuid4().hex}.dump"
    _docker_cp_to(container, dump_path, remote_path)
    try:
        _docker_exec(
            container,
            [
                "env",
                f"PGPASSWORD={conn.password}",
                "pg_restore",
                "-U",
                conn.user,
                "-d",
                conn.database,
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-acl",
                "--exit-on-error",
                remote_path,
            ],
        )
    finally:
        _docker_exec(container, ["rm", "-f", remote_path])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_backups_dir(repo_root: Path | None = None) -> Path:
    directory = get_backups_dir(repo_root)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def safe_backup_file_path(file_name: str, *, repo_root: Path | None = None) -> Path:
    return resolve_backup_path(file_name, repo_root=repo_root)
