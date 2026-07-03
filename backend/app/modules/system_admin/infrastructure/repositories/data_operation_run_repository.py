from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.modules.system_admin.domain.data_operation_entities import DataOperationOutputFile, DataOperationRun
from app.modules.system_admin.domain.data_operation_value_objects import (
    DataOperationRunResult,
    DataOperationRunStatus,
)
from app.modules.system_admin.infrastructure.persistence.models import SystemDataOperationRunModel

_ACTIVE_STATUSES = (
    DataOperationRunStatus.QUEUED.value,
    DataOperationRunStatus.RUNNING.value,
)


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _output_files_from_json(payload: list[dict] | None) -> list[DataOperationOutputFile]:
    if not payload:
        return []
    files: list[DataOperationOutputFile] = []
    for item in payload:
        files.append(
            DataOperationOutputFile(
                id=UUID(str(item["id"])),
                relative_path=str(item["relative_path"]),
                file_name=str(item["file_name"]),
                size_bytes=item.get("size_bytes"),
            )
        )
    return files


def _output_files_to_json(files: list[DataOperationOutputFile]) -> list[dict]:
    return [
        {
            "id": str(file.id),
            "relative_path": file.relative_path,
            "file_name": file.file_name,
            "size_bytes": file.size_bytes,
        }
        for file in files
    ]


def _to_entity(model: SystemDataOperationRunModel) -> DataOperationRun:
    return DataOperationRun(
        id=model.id,
        organization_id=model.organization_id,
        operation_key=model.operation_key,
        status=DataOperationRunStatus(model.status),
        started_by=model.started_by,
        started_by_email=model.started_by_email,
        started_at=_ensure_utc(model.started_at),
        completed_at=_ensure_utc(model.completed_at),
        duration_seconds=model.duration_seconds,
        result=DataOperationRunResult(model.result) if model.result else None,
        error_message=model.error_message,
        stdout_text=model.stdout_text,
        output_files=_output_files_from_json(model.output_files_json),
        summary_json=model.summary_json,
        created_at=_ensure_utc(model.created_at),
        updated_at=_ensure_utc(model.updated_at),
    )


def _to_model(entity: DataOperationRun) -> SystemDataOperationRunModel:
    return SystemDataOperationRunModel(
        id=entity.id,
        organization_id=entity.organization_id,
        operation_key=entity.operation_key,
        status=entity.status.value,
        started_by=entity.started_by,
        started_by_email=entity.started_by_email,
        started_at=entity.started_at,
        completed_at=entity.completed_at,
        duration_seconds=entity.duration_seconds,
        result=entity.result.value if entity.result else None,
        error_message=entity.error_message,
        stdout_text=entity.stdout_text,
        output_files_json=_output_files_to_json(entity.output_files) or None,
        summary_json=entity.summary_json,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def _update_model(model: SystemDataOperationRunModel, entity: DataOperationRun) -> None:
    model.status = entity.status.value
    model.completed_at = entity.completed_at
    model.duration_seconds = entity.duration_seconds
    model.result = entity.result.value if entity.result else None
    model.error_message = entity.error_message
    model.stdout_text = entity.stdout_text
    model.output_files_json = _output_files_to_json(entity.output_files) or None
    model.summary_json = entity.summary_json
    model.updated_at = entity.updated_at


class SqlAlchemyDataOperationRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, run: DataOperationRun) -> DataOperationRun:
        model = _to_model(run)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return _to_entity(model)

    def update(self, run: DataOperationRun) -> DataOperationRun:
        model = (
            self._session.query(SystemDataOperationRunModel)
            .filter(
                SystemDataOperationRunModel.organization_id == run.organization_id,
                SystemDataOperationRunModel.id == run.id,
            )
            .one()
        )
        _update_model(model, run)
        self._session.flush()
        self._session.refresh(model)
        return _to_entity(model)

    def get_by_id(self, organization_id: UUID, run_id: UUID) -> DataOperationRun | None:
        model = (
            self._session.query(SystemDataOperationRunModel)
            .filter(
                SystemDataOperationRunModel.organization_id == organization_id,
                SystemDataOperationRunModel.id == run_id,
            )
            .one_or_none()
        )
        return _to_entity(model) if model else None

    def get_active_for_operation(self, organization_id: UUID, operation_key: str) -> DataOperationRun | None:
        model = (
            self._session.query(SystemDataOperationRunModel)
            .filter(
                SystemDataOperationRunModel.organization_id == organization_id,
                SystemDataOperationRunModel.operation_key == operation_key,
                SystemDataOperationRunModel.status.in_(_ACTIVE_STATUSES),
            )
            .order_by(desc(SystemDataOperationRunModel.started_at))
            .first()
        )
        return _to_entity(model) if model else None

    def latest_run_by_operation_key(self, organization_id: UUID) -> dict[str, DataOperationRun]:
        models = (
            self._session.query(SystemDataOperationRunModel)
            .filter(SystemDataOperationRunModel.organization_id == organization_id)
            .order_by(desc(SystemDataOperationRunModel.started_at))
            .all()
        )
        latest: dict[str, DataOperationRun] = {}
        for model in models:
            if model.operation_key not in latest:
                latest[model.operation_key] = _to_entity(model)
        return latest

    def active_runs_by_operation_key(self, organization_id: UUID) -> dict[str, DataOperationRun]:
        models = (
            self._session.query(SystemDataOperationRunModel)
            .filter(
                SystemDataOperationRunModel.organization_id == organization_id,
                SystemDataOperationRunModel.status.in_(_ACTIVE_STATUSES),
            )
            .all()
        )
        return {model.operation_key: _to_entity(model) for model in models}
