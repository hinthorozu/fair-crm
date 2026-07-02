from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.system_admin.domain.entities import SystemBackup
from app.modules.system_admin.domain.value_objects import SystemBackupStage, SystemBackupStatus
from app.modules.system_admin.infrastructure.persistence.models import SystemBackupModel

BACKUP_SORT_FIELDS = {
    "file_name": SystemBackupModel.file_name,
    "started_at": SystemBackupModel.started_at,
    "file_size": SystemBackupModel.file_size,
    "duration_seconds": SystemBackupModel.duration_seconds,
    "status": SystemBackupModel.status,
    "created_by_email": SystemBackupModel.created_by_email,
    "notes": SystemBackupModel.notes,
    "download_count": SystemBackupModel.download_count,
    "created_at": SystemBackupModel.created_at,
}


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _to_entity(model: SystemBackupModel) -> SystemBackup:
    return SystemBackup(
        id=model.id,
        organization_id=model.organization_id,
        file_name=model.file_name,
        file_size=model.file_size,
        status=SystemBackupStatus(model.status),
        progress_stage=SystemBackupStage(model.progress_stage),
        started_at=_ensure_utc(model.started_at),
        completed_at=_ensure_utc(model.completed_at),
        duration_seconds=model.duration_seconds,
        created_by=model.created_by,
        created_by_email=model.created_by_email,
        notes=model.notes,
        checksum=model.checksum,
        download_count=model.download_count,
        error_message=model.error_message,
        created_at=_ensure_utc(model.created_at),
        updated_at=_ensure_utc(model.updated_at),
    )


def _to_model(entity: SystemBackup) -> SystemBackupModel:
    return SystemBackupModel(
        id=entity.id,
        organization_id=entity.organization_id,
        file_name=entity.file_name,
        file_size=entity.file_size,
        status=entity.status.value,
        progress_stage=entity.progress_stage.value,
        started_at=entity.started_at,
        completed_at=entity.completed_at,
        duration_seconds=entity.duration_seconds,
        created_by=entity.created_by,
        created_by_email=entity.created_by_email,
        notes=entity.notes,
        checksum=entity.checksum,
        download_count=entity.download_count,
        error_message=entity.error_message,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def _update_model(model: SystemBackupModel, entity: SystemBackup) -> None:
    model.file_name = entity.file_name
    model.file_size = entity.file_size
    model.status = entity.status.value
    model.progress_stage = entity.progress_stage.value
    model.started_at = entity.started_at
    model.completed_at = entity.completed_at
    model.duration_seconds = entity.duration_seconds
    model.created_by_email = entity.created_by_email
    model.notes = entity.notes
    model.checksum = entity.checksum
    model.download_count = entity.download_count
    model.error_message = entity.error_message
    model.updated_at = entity.updated_at


class SqlAlchemySystemBackupRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, backup: SystemBackup) -> SystemBackup:
        model = _to_model(backup)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return _to_entity(model)

    def update(self, backup: SystemBackup) -> SystemBackup:
        model = (
            self._session.query(SystemBackupModel)
            .filter(
                SystemBackupModel.organization_id == backup.organization_id,
                SystemBackupModel.id == backup.id,
            )
            .one()
        )
        _update_model(model, backup)
        self._session.flush()
        self._session.refresh(model)
        return _to_entity(model)

    def get_by_id(self, organization_id: UUID, backup_id: UUID) -> SystemBackup | None:
        model = (
            self._session.query(SystemBackupModel)
            .filter(
                SystemBackupModel.organization_id == organization_id,
                SystemBackupModel.id == backup_id,
            )
            .one_or_none()
        )
        return _to_entity(model) if model else None

    def list_recent(
        self,
        organization_id: UUID,
        *,
        page: int,
        page_size: int,
        sort_by: str = "started_at",
        sort_dir: str = "desc",
    ) -> tuple[list[SystemBackup], int]:
        query = self._session.query(SystemBackupModel).filter(
            SystemBackupModel.organization_id == organization_id
        )
        total = query.count()
        sort_column = BACKUP_SORT_FIELDS.get(sort_by, SystemBackupModel.started_at)
        ordered = sort_column.desc() if sort_dir == "desc" else sort_column.asc()
        models = (
            query.order_by(ordered)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return [_to_entity(model) for model in models], total
