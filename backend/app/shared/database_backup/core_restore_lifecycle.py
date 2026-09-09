"""Adapter for the Kyrox Core-owned OL10 self-restore lifecycle guard."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.shared.database_backup.database_keys import resolve_alembic_workdir


@dataclass(frozen=True, slots=True)
class CoreRestoreLifecycleReconciliationResult:
    ok: bool
    organization_count: int = 0
    lifecycle_reapplied_count: int = 0
    resurrected_extra_tombstoned_count: int = 0
    error_message: str | None = None

    def log_lines(self) -> list[str]:
        lines = [
            "Core lifecycle self-reconciliation:",
            f"  organizations authoritative before restore: {self.organization_count}",
            f"  lifecycle rows reapplied: {self.lifecycle_reapplied_count}",
            (
                "  old-backup-only organizations soft-tombstoned: "
                f"{self.resurrected_extra_tombstoned_count}"
            ),
        ]
        if self.error_message:
            lines.append(f"  error: {self.error_message}")
        lines.append(f"  result: {'PASS' if self.ok else 'BLOCK'}")
        return lines

    def summary_text(self) -> str:
        return (
            "OL10 Core lifecycle reconciliation: "
            f"result={'PASS' if self.ok else 'BLOCK'}; "
            f"organizations={self.organization_count}; "
            f"reapplied={self.lifecycle_reapplied_count}; "
            f"old_only_tombstoned={self.resurrected_extra_tombstoned_count}"
        )


def _resolve_core_python(core_repo_root: Path) -> Path:
    candidates = (
        core_repo_root / ".venv" / "bin" / "python",
        core_repo_root / ".venv" / "Scripts" / "python.exe",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise ValueError(
        f"Kyrox Core virtualenv Python not found under {core_repo_root / '.venv'}"
    )


def _core_guard_command(*, operation: str, database_url: str) -> tuple[list[str], Path, dict[str, str]]:
    core_repo_root = resolve_alembic_workdir("kyrox_core")
    core_backend = core_repo_root / "backend"
    guard_module = (
        core_backend
        / "app"
        / "modules"
        / "identity"
        / "maintenance"
        / "restore_lifecycle_guard.py"
    )
    if not guard_module.is_file():
        raise ValueError(
            "Kyrox Core OL10 restore lifecycle guard is not installed; update kyrox-core before restore"
        )

    python = _resolve_core_python(core_repo_root)
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{core_backend}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else str(core_backend)
    )
    return (
        [
            str(python),
            "-m",
            "app.modules.identity.maintenance.restore_lifecycle_guard",
            operation,
            "--database-url",
            database_url,
        ],
        core_backend,
        env,
    )


def capture_core_restore_lifecycle_snapshot(*, database_url: str) -> str:
    """Capture current Core authority before destructive restore.

    The returned JSON remains in the FAIR maintenance process memory. It is never
    written into the database being restored and is not emitted to restore logs.
    """

    command, cwd, env = _core_guard_command(operation="capture", database_url=database_url)
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or "Core lifecycle capture failed"
        raise ValueError(f"Core lifecycle authority capture blocked restore: {detail[:500]}")
    raw = completed.stdout.strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Core lifecycle capture returned malformed JSON") from exc
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise ValueError("Core lifecycle capture returned unsupported snapshot data")
    if not isinstance(payload.get("organizations"), list):
        raise ValueError("Core lifecycle capture omitted organization authority")
    return raw


def reconcile_core_restore_lifecycle(
    *,
    database_url: str,
    snapshot_json: str | None,
) -> CoreRestoreLifecycleReconciliationResult:
    if not snapshot_json:
        return CoreRestoreLifecycleReconciliationResult(
            ok=False,
            error_message="Pre-restore Core lifecycle authority snapshot is unavailable",
        )

    try:
        command, cwd, env = _core_guard_command(
            operation="reconcile",
            database_url=database_url,
        )
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            input=snapshot_json,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return CoreRestoreLifecycleReconciliationResult(
            ok=False,
            error_message=f"Core lifecycle reconciliation could not run: {exc}",
        )

    raw = completed.stdout.strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        detail = completed.stderr.strip() or raw or "malformed Core reconciliation output"
        return CoreRestoreLifecycleReconciliationResult(
            ok=False,
            error_message=f"Core lifecycle reconciliation failed: {detail[:500]}",
        )
    if not isinstance(payload, dict):
        return CoreRestoreLifecycleReconciliationResult(
            ok=False,
            error_message="Core lifecycle reconciliation returned malformed result",
        )

    ok = payload.get("ok") is True and completed.returncode == 0
    return CoreRestoreLifecycleReconciliationResult(
        ok=ok,
        organization_count=_safe_nonnegative_int(payload.get("organization_count")),
        lifecycle_reapplied_count=_safe_nonnegative_int(payload.get("lifecycle_reapplied_count")),
        resurrected_extra_tombstoned_count=_safe_nonnegative_int(
            payload.get("resurrected_extra_tombstoned_count")
        ),
        error_message=None if ok else str(payload.get("error_message") or "Core restore blocked"),
    )


def _safe_nonnegative_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return value
