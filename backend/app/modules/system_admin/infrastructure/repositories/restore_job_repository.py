from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.system_admin.domain.entities import SystemBackupRestoreJob
from app.modules.system_admin.domain.value_objects import RestoreJobSourceType, RestoreJobStatus
from app.modules.system_admin.infrastructure.persistence.models import SystemBackupRestoreJobModel
from app.shared.database_backup.database_keys import DatabaseKey

RESTORE_JOB_SORT_FIELDS = {
    "status": SystemBackupRestoreJobModel.status,
    "source_type": SystemBackupRestoreJobModel.source_type,
    "source_database_key": SystemBackupRestoreJobModel.source_database_key,
    "target_database_key": SystemBackupRestoreJobModel.target_database_key,
    "source_file_name": SystemBackupRestoreJobModel.source_file_name,
    "requested_at": SystemBackupRestoreJobModel.requested_at,
    "requested_by_email": SystemBackupRestoreJobModel.requested_by_email,
    "notes": SystemBackupRestoreJobModel.notes,
    "created_at": SystemBackupRestoreJobModel.created_at,
}


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _to_entity(model: SystemBackupRestoreJobModel) -> SystemBackupRestoreJob:
    return SystemBackupRestoreJob(
        id=model.id,
        organization_id=model.organization_id,
        source_type=RestoreJobSourceType(model.source_type),
        source_database_key=DatabaseKey(model.source_database_key),
        target_database_key=DatabaseKey(model.target_database_key),
        backup_id=model.backup_id,
        uploaded_file_path=model.uploaded_file_path,
        source_file_name=model.source_file_name,
        checksum_sha256=model.checksum_sha256,
        status=RestoreJobStatus(model.status),
        notes=model.notes,
        requested_by_user_id=model.requested_by_user_id,
        requested_by_email=model.requested_by_email,
        requested_at=_ensure_utc(model.requested_at),
        started_at=_ensure_utc(model.started_at),
        completed_at=_ensure_utc(model.completed_at),
        failed_at=_ensure_utc(model.failed_at),
        error_message=model.error_message,
        restore_log_path=model.restore_log_path,
        created_at=_ensure_utc(model.created_at),
        updated_at=_ensure_utc(model.updated_at),
    )


def _to_model(entity: SystemBackupRestoreJob) -> SystemBackupRestoreJobModel:
    return SystemBackupRestoreJobModel(
        id=entity.id,
        organization_id=entity.organization_id,
        source_type=entity.source_type.value,
        source_database_key=entity.source_database_key.value,
        target_database_key=entity.target_database_key.value,
        backup_id=entity.backup_id,
        uploaded_file_path=entity.uploaded_file_path,
        source_file_name=entity.source_file_name,
        checksum_sha256=entity.checksum_sha256,
        status=entity.status.value,
        notes=entity.notes,
        requested_by_user_id=entity.requested_by_user_id,
        requested_by_email=entity.requested_by_email,
        requested_at=entity.requested_at,
        started_at=entity.started_at,
        completed_at=entity.completed_at,
        failed_at=entity.failed_at,
        error_message=entity.error_message,
        restore_log_path=entity.restore_log_path,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def _update_model(model: SystemBackupRestoreJobModel, entity: SystemBackupRestoreJob) -> None:
    model.source_type = entity.source_type.value
    model.source_database_key = entity.source_database_key.value
    model.target_database_key = entity.target_database_key.value
    model.backup_id = entity.backup_id
    model.uploaded_file_path = entity.uploaded_file_path
    model.source_file_name = entity.source_file_name
    model.checksum_sha256 = entity.checksum_sha256
    model.status = entity.status.value
    model.notes = entity.notes
    model.requested_by_email = entity.requested_by_email
    model.started_at = entity.started_at
    model.completed_at = entity.completed_at
    model.failed_at = entity.failed_at
    model.error_message = entity.error_message
    model.restore_log_path = entity.restore_log_path
    model.updated_at = entity.updated_at


class SqlAlchemySystemBackupRestoreJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, job: SystemBackupRestoreJob) -> SystemBackupRestoreJob:
        model = _to_model(job)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return _to_entity(model)

    def update(self, job: SystemBackupRestoreJob) -> SystemBackupRestoreJob:
        model = self._session.query(SystemBackupRestoreJobModel).filter(SystemBackupRestoreJobModel.id == job.id).one()
        _update_model(model, job)
        self._session.flush()
        self._session.refresh(model)
        return _to_entity(model)

    def get_by_id(self, organization_id: UUID, job_id: UUID) -> SystemBackupRestoreJob | None:
        model = (
            self._session.query(SystemBackupRestoreJobModel)
            .filter(
                SystemBackupRestoreJobModel.organization_id == organization_id,
                SystemBackupRestoreJobModel.id == job_id,
            )
            .one_or_none()
        )
        return _to_entity(model) if model else None

    def get_by_id_global(self, job_id: UUID) -> SystemBackupRestoreJob | None:
        model = (
            self._session.query(SystemBackupRestoreJobModel)
            .filter(SystemBackupRestoreJobModel.id == job_id)
            .one_or_none()
        )
        return _to_entity(model) if model else None

    def list_recent(
        self,
        organization_id: UUID,
        *,
        page: int,
        page_size: int,
        sort_by: str = "requested_at",
        sort_dir: str = "desc",
    ) -> tuple[list[SystemBackupRestoreJob], int]:
        query = self._session.query(SystemBackupRestoreJobModel).filter(
            SystemBackupRestoreJobModel.organization_id == organization_id
        )
        total = query.count()
        sort_column = RESTORE_JOB_SORT_FIELDS.get(sort_by, SystemBackupRestoreJobModel.requested_at)
        ordered = sort_column.desc() if sort_dir == "desc" else sort_column.asc()
        models = (
            query.order_by(ordered)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return [_to_entity(model) for model in models], total
