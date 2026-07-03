from __future__ import annotations

import os
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.modules.system_admin.application.data_operation_assign_fair import assign_customers_to_fair
from app.modules.system_admin.application.data_operation_delete_customers import delete_selected_customers
from app.modules.system_admin.application.data_operation_dataset_builders import (
    build_customers_without_fair_dataset,
    build_duplicate_customer_groups_dataset,
)
from app.modules.customers.application.customer_field_grouping import GROUP_BY_FIELDS
from app.modules.system_admin.application.data_operation_registry import get_operation_definition
from app.modules.system_admin.domain.data_operation_entities import DataOperationOutputFile, DataOperationRun
from app.modules.system_admin.domain.data_operation_value_objects import DataOperationRunResult
from app.modules.system_admin.infrastructure.repositories.data_operation_run_repository import (
    SqlAlchemyDataOperationRunRepository,
)
from app.shared.maintenance.paths import get_maintenance_dir, resolve_maintenance_file

_EXCEL_OUTPUT_RE = re.compile(r"^\s*Excel output:\s*(.+)\s*$")
_OUTPUT_DIR_RE = re.compile(r"^\s*Output directory:\s*(.+)\s*$")
_SUMMARY_RE = re.compile(r"^\s*Summary:\s*(.+)\s*$")
_STDOUT_MAX_CHARS = 32_000

_DATASET_BUILDERS = {
    "customers_without_fair": build_customers_without_fair_dataset,
    "duplicate_customer_groups": build_duplicate_customer_groups_dataset,
}


@dataclass(frozen=True)
class DataOperationJobCommand:
    organization_id: UUID
    run_id: UUID


class DataOperationJobRunner:
    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory or SessionLocal

    def run_operation(self, command: DataOperationJobCommand) -> None:
        db = self._session_factory()
        try:
            repo = SqlAlchemyDataOperationRunRepository(db)
            run = repo.get_by_id(command.organization_id, command.run_id)
            if run is None:
                return

            definition = get_operation_definition(run.operation_key)
            if definition is None:
                run.mark_failed(error_message="Unknown operation", stdout_text=None, now=datetime.now(tz=UTC))
                repo.update(run)
                db.commit()
                return

            now = datetime.now(tz=UTC)
            run.mark_running(now=now)
            repo.update(run)
            db.commit()

            if definition.result_mode == "dataset":
                self._run_dataset_operation(
                    db=db,
                    repo=repo,
                    run=run,
                    definition=definition,
                    organization_id=command.organization_id,
                    run_id=command.run_id,
                )
                return

            maintenance_dir = get_maintenance_dir()
            if not definition.script_path:
                run.mark_failed(
                    error_message="Operation script path is not configured",
                    stdout_text=None,
                    now=datetime.now(tz=UTC),
                )
                repo.update(run)
                db.commit()
                return

            script_path = maintenance_dir / definition.script_path
            if not script_path.is_file():
                run.mark_failed(
                    error_message=f"Maintenance script not found: {definition.script_path}",
                    stdout_text=None,
                    now=datetime.now(tz=UTC),
                )
                repo.update(run)
                db.commit()
                return

            try:
                completed = subprocess.run(
                    [sys.executable, str(script_path)],
                    cwd=str(maintenance_dir.parents[1]),
                    capture_output=True,
                    text=True,
                    env=os.environ.copy(),
                    check=False,
                )
                stdout = completed.stdout or ""
                stderr = completed.stderr or ""
                combined = "\n".join(part for part in (stdout, stderr) if part).strip()
                truncated_stdout = combined[:_STDOUT_MAX_CHARS] if combined else None

                if completed.returncode != 0:
                    message = stderr.strip() or stdout.strip() or f"Script exited with code {completed.returncode}"
                    run.mark_failed(error_message=message, stdout_text=truncated_stdout, now=datetime.now(tz=UTC))
                    repo.update(run)
                    db.commit()
                    return

                output_files = _collect_output_files(stdout, maintenance_dir=maintenance_dir)
                summary = _parse_summary(stdout)
                finished = datetime.now(tz=UTC)
                run.mark_completed(
                    result=DataOperationRunResult.SUCCESS,
                    output_files=output_files,
                    stdout_text=truncated_stdout,
                    summary_json=summary,
                    now=finished,
                )
                repo.update(run)
                db.commit()
            except OSError as exc:
                db.rollback()
                run = repo.get_by_id(command.organization_id, command.run_id)
                if run:
                    run.mark_failed(error_message=str(exc), stdout_text=None, now=datetime.now(tz=UTC))
                    repo.update(run)
                    db.commit()
        finally:
            db.close()

    def run_assign_customers_to_fair(self, command: DataOperationJobCommand) -> None:
        db = self._session_factory()
        try:
            repo = SqlAlchemyDataOperationRunRepository(db)
            run = repo.get_by_id(command.organization_id, command.run_id)
            if run is None:
                return

            payload = run.summary_json or {}
            parent_run_id_raw = payload.get("parent_run_id")
            fair_id_raw = payload.get("fair_id")
            customer_ids_raw = payload.get("customer_ids") or []
            if not parent_run_id_raw or not fair_id_raw:
                run.mark_failed(
                    error_message="Assign job payload is incomplete",
                    stdout_text=None,
                    now=datetime.now(tz=UTC),
                )
                repo.update(run)
                db.commit()
                return

            now = datetime.now(tz=UTC)
            run.mark_running(now=now)
            repo.update(run)
            db.commit()

            try:
                result = assign_customers_to_fair(
                    db,
                    organization_id=command.organization_id,
                    parent_run_id=UUID(str(parent_run_id_raw)),
                    fair_id=UUID(str(fair_id_raw)),
                    customer_ids=[UUID(str(customer_id)) for customer_id in customer_ids_raw],
                )
                finished = datetime.now(tz=UTC)
                run = repo.get_by_id(command.organization_id, command.run_id)
                if run is None:
                    return
                summary = dict(run.summary_json or {})
                summary.update(result.to_summary_json())
                run.mark_completed(
                    result=DataOperationRunResult.SUCCESS,
                    output_files=[],
                    stdout_text=None,
                    summary_json=summary,
                    now=finished,
                )
                repo.update(run)
                db.commit()
            except Exception as exc:
                db.rollback()
                run = repo.get_by_id(command.organization_id, command.run_id)
                if run:
                    run.mark_failed(error_message=str(exc), stdout_text=None, now=datetime.now(tz=UTC))
                    repo.update(run)
                    db.commit()
        finally:
            db.close()

    def run_delete_selected_customers(self, command: DataOperationJobCommand) -> None:
        db = self._session_factory()
        try:
            repo = SqlAlchemyDataOperationRunRepository(db)
            run = repo.get_by_id(command.organization_id, command.run_id)
            if run is None:
                return

            payload = run.summary_json or {}
            parent_run_id_raw = payload.get("parent_run_id")
            customer_ids_raw = payload.get("customer_ids") or []
            if not parent_run_id_raw:
                run.mark_failed(
                    error_message="Delete job payload is incomplete",
                    stdout_text=None,
                    now=datetime.now(tz=UTC),
                )
                repo.update(run)
                db.commit()
                return

            now = datetime.now(tz=UTC)
            run.mark_running(now=now)
            repo.update(run)
            db.commit()

            try:
                result = delete_selected_customers(
                    db,
                    organization_id=command.organization_id,
                    parent_run_id=UUID(str(parent_run_id_raw)),
                    customer_ids=[UUID(str(customer_id)) for customer_id in customer_ids_raw],
                )
                finished = datetime.now(tz=UTC)
                run = repo.get_by_id(command.organization_id, command.run_id)
                if run is None:
                    return
                summary = dict(run.summary_json or {})
                summary.update(result.to_summary_json())
                run.mark_completed(
                    result=DataOperationRunResult.SUCCESS,
                    output_files=[],
                    stdout_text=None,
                    summary_json=summary,
                    now=finished,
                )
                repo.update(run)
                db.commit()
            except Exception as exc:
                db.rollback()
                run = repo.get_by_id(command.organization_id, command.run_id)
                if run:
                    run.mark_failed(error_message=str(exc), stdout_text=None, now=datetime.now(tz=UTC))
                    repo.update(run)
                    db.commit()
        finally:
            db.close()

    def _run_dataset_operation(
        self,
        *,
        db: Session,
        repo: SqlAlchemyDataOperationRunRepository,
        run: DataOperationRun,
        definition,
        organization_id: UUID,
        run_id: UUID,
    ) -> None:
        if not definition.dataset_kind:
            run.mark_failed(
                error_message="Dataset kind is not configured",
                stdout_text=None,
                now=datetime.now(tz=UTC),
            )
            repo.update(run)
            db.commit()
            return

        builder = _DATASET_BUILDERS.get(definition.dataset_kind)
        if builder is None:
            run.mark_failed(
                error_message=f"Unsupported dataset kind: {definition.dataset_kind}",
                stdout_text=None,
                now=datetime.now(tz=UTC),
            )
            repo.update(run)
            db.commit()
            return

        try:
            if definition.dataset_kind == "duplicate_customer_groups":
                payload = run.summary_json or {}
                group_by_raw = payload.get("group_by")
                if not group_by_raw or group_by_raw not in GROUP_BY_FIELDS:
                    raise ValueError(
                        "group_by is required for duplicate customer analysis "
                        "(company_name, email, website, or phone)"
                    )
                summary = build_duplicate_customer_groups_dataset(
                    db,
                    organization_id=organization_id,
                    run_id=run_id,
                    group_by=group_by_raw,  # type: ignore[arg-type]
                )
            else:
                summary = builder(db, organization_id=organization_id, run_id=run_id)
            finished = datetime.now(tz=UTC)
            run = repo.get_by_id(organization_id, run_id)
            if run is None:
                return
            run.mark_completed(
                result=DataOperationRunResult.SUCCESS,
                output_files=[],
                stdout_text=None,
                summary_json=summary.to_json(),
                now=finished,
            )
            repo.update(run)
            db.commit()
        except Exception as exc:
            db.rollback()
            run = repo.get_by_id(organization_id, run_id)
            if run:
                run.mark_failed(error_message=str(exc), stdout_text=None, now=datetime.now(tz=UTC))
                repo.update(run)
                db.commit()


def _collect_output_files(stdout: str, *, maintenance_dir: Path) -> list[DataOperationOutputFile]:
    paths: list[Path] = []
    output_dir: Path | None = None

    for line in stdout.splitlines():
        excel_match = _EXCEL_OUTPUT_RE.match(line)
        if excel_match:
            paths.append(Path(excel_match.group(1).strip()))
            continue
        dir_match = _OUTPUT_DIR_RE.match(line)
        if dir_match:
            output_dir = Path(dir_match.group(1).strip())
            continue
        summary_match = _SUMMARY_RE.match(line)
        if summary_match:
            paths.append(Path(summary_match.group(1).strip()))

    if output_dir is not None and output_dir.is_dir():
        for xlsx in sorted(output_dir.glob("*.xlsx")):
            if xlsx not in paths:
                paths.append(xlsx)

    maintenance_resolved = maintenance_dir.resolve()
    files: list[DataOperationOutputFile] = []
    seen: set[str] = set()
    for path in paths:
        resolved = path.resolve()
        try:
            relative = resolved.relative_to(maintenance_resolved)
        except ValueError:
            relative = Path(resolved.name)
        relative_str = relative.as_posix()
        if relative_str in seen or not resolved.is_file():
            continue
        seen.add(relative_str)
        files.append(
            DataOperationOutputFile(
                id=uuid4(),
                relative_path=relative_str,
                file_name=resolved.name,
                size_bytes=resolved.stat().st_size,
            )
        )
    return files


def _parse_summary(stdout: str) -> dict[str, str] | None:
    summary: dict[str, str] = {}
    for line in stdout.splitlines():
        stripped = line.strip()
        if not stripped or ":" not in stripped:
            continue
        if stripped.startswith("Excel output:") or stripped.startswith("Output directory:"):
            continue
        if stripped.startswith("Database:") or stripped.startswith("Input:"):
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key and value:
            summary[key] = value
    return summary or None


def resolve_run_output_file(run: DataOperationRun, file_id: UUID) -> Path:
    for output_file in run.output_files:
        if output_file.id == file_id:
            return resolve_maintenance_file(output_file.relative_path)
    raise LookupError("Output file not found")
