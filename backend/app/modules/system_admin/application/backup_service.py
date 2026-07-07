from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.core.pagination import normalize_sort_direction
from app.integrations.kyrox_core.ports import AuditPort, AuthorizationPort
from app.modules.system_admin.domain.entities import SystemBackup, SystemBackupRestoreJob
from app.modules.system_admin.domain.ports import SystemBackupRepository, SystemBackupRestoreJobRepository
from app.modules.system_admin.domain.value_objects import RestoreJobSourceType
from app.modules.system_admin.application.restore_job_service import (
    _to_result as _restore_job_to_result,
)
from app.shared.database_backup.paths import relative_repo_path
from app.shared.database_backup.engine import (
    DatabaseBackupError,
    is_custom_pg_dump,
    sha256_file,
    verify_backup_dump,
)
from app.shared.database_backup.formats import BackupFormat
from app.shared.database_backup.paths import generate_backup_filename, get_restore_uploads_dir, resolve_backup_path

PERMISSION_CREATE = "fair_crm.admin.backups.create"
PERMISSION_RESTORE = "fair_crm.admin.backups.create"
PERMISSION_DELETE = "fair_crm.admin.backups.create"

BACKUP_ALLOWED_SORT_FIELDS = frozenset(
    {
        "file_name",
        "backup_format",
        "started_at",
        "file_size",
        "duration_seconds",
        "status",
        "created_by_email",
        "notes",
        "download_count",
        "created_at",
    }
)
BACKUP_DEFAULT_SORT_FIELD = "started_at"
BACKUP_DEFAULT_SORT_DIRECTION = "desc"


@dataclass
class CreateSystemBackupCommand:
    organization_id: UUID
    user_id: UUID
    user_email: str | None
    access_token: str
    notes: str | None
    backup_format: BackupFormat = BackupFormat.POSTGRESQL_DUMP


@dataclass
class CreateSystemBackupResult:
    backup_id: UUID
    file_name: str
    backup_format: str
    status: str
    progress_stage: str


class CreateSystemBackupUseCase:
    def __init__(
        self,
        repository: SystemBackupRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._repository = repository
        self._authorization = authorization

    def execute(self, command: CreateSystemBackupCommand) -> CreateSystemBackupResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_CREATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        now = datetime.now(tz=UTC)
        file_name = generate_backup_filename(backup_format=command.backup_format, now=now)
        backup = SystemBackup.create(
            organization_id=command.organization_id,
            file_name=file_name,
            backup_format=command.backup_format,
            created_by=command.user_id,
            created_by_email=command.user_email,
            notes=command.notes,
            now=now,
        )
        saved = self._repository.add(backup)
        return CreateSystemBackupResult(
            backup_id=saved.id,
            file_name=saved.file_name,
            backup_format=saved.backup_format.value,
            status=saved.status.value,
            progress_stage=saved.progress_stage.value,
        )


@dataclass
class GetSystemBackupResult:
    id: UUID
    file_name: str
    backup_format: str
    file_size: int | None
    status: str
    progress_stage: str
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: int | None
    created_by: UUID
    created_by_email: str | None
    notes: str | None
    checksum: str | None
    manifest_json: dict | None
    download_count: int
    error_message: str | None


class GetSystemBackupUseCase:
    def __init__(
        self,
        repository: SystemBackupRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._repository = repository
        self._authorization = authorization

    def execute(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        access_token: str,
        backup_id: UUID,
        permission_code: str,
    ) -> GetSystemBackupResult:
        if not self._authorization.check_permission(
            organization_id=organization_id,
            user_id=user_id,
            permission_code=permission_code,
            access_token=access_token,
        ):
            raise ForbiddenError("Permission denied")

        backup = self._repository.get_by_id(organization_id, backup_id)
        if backup is None:
            raise LookupError("Backup not found")
        return _to_result(backup)


class ListSystemBackupsUseCase:
    def __init__(
        self,
        repository: SystemBackupRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._repository = repository
        self._authorization = authorization

    def execute(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        access_token: str,
        page: int,
        page_size: int,
        sort_by: str = BACKUP_DEFAULT_SORT_FIELD,
        sort_dir: str = BACKUP_DEFAULT_SORT_DIRECTION,
    ) -> tuple[list[GetSystemBackupResult], int, str, str]:
        if not self._authorization.check_permission(
            organization_id=organization_id,
            user_id=user_id,
            permission_code="fair_crm.admin.backups.read",
            access_token=access_token,
        ):
            raise ForbiddenError("Permission denied")

        resolved_sort = sort_by if sort_by in BACKUP_ALLOWED_SORT_FIELDS else BACKUP_DEFAULT_SORT_FIELD
        resolved_dir = normalize_sort_direction(sort_dir or BACKUP_DEFAULT_SORT_DIRECTION)
        items, total = self._repository.list_recent(
            organization_id,
            page=page,
            page_size=page_size,
            sort_by=resolved_sort,
            sort_dir=resolved_dir,
        )
        return [_to_result(item) for item in items], total, resolved_sort, resolved_dir


class DownloadSystemBackupUseCase:
    def __init__(
        self,
        repository: SystemBackupRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._repository = repository
        self._authorization = authorization

    def execute(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        access_token: str,
        backup_id: UUID,
    ) -> tuple[SystemBackup, str]:
        if not self._authorization.check_permission(
            organization_id=organization_id,
            user_id=user_id,
            permission_code="fair_crm.admin.backups.download",
            access_token=access_token,
        ):
            raise ForbiddenError("Permission denied")

        backup = self._repository.get_by_id(organization_id, backup_id)
        if backup is None:
            raise LookupError("Backup not found")
        if backup.status.value != "completed":
            raise ValueError("Backup is not ready for download")

        path = resolve_backup_path(backup.file_name)
        if not path.exists():
            raise FileNotFoundError("Backup file missing on disk")

        now = datetime.now(tz=UTC)
        backup.increment_download(now=now)
        self._repository.update(backup)
        return backup, str(path)


def media_type_for_backup_file(file_name: str) -> str:
    if file_name.endswith(".sql"):
        return "application/sql"
    if file_name.endswith(".zip"):
        return "application/zip"
    return "application/octet-stream"


def _to_result(backup: SystemBackup) -> GetSystemBackupResult:
    return GetSystemBackupResult(
        id=backup.id,
        file_name=backup.file_name,
        backup_format=backup.backup_format.value,
        file_size=backup.file_size,
        status=backup.status.value,
        progress_stage=backup.progress_stage.value,
        started_at=backup.started_at,
        completed_at=backup.completed_at,
        duration_seconds=backup.duration_seconds,
        created_by=backup.created_by,
        created_by_email=backup.created_by_email,
        notes=backup.notes,
        checksum=backup.checksum,
        manifest_json=backup.manifest_json,
        download_count=backup.download_count,
        error_message=backup.error_message,
    )


class RestoreService:
    """Restore foundation — automatic restore disabled for production safety.

    In-process pg_restore against the API's own database connection is not
    production-safe. Use the maintenance restore script for real restores.
    """

    FEATURE_DISABLED_MESSAGE = "Database restore is not enabled in this environment."

    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def enabled(self) -> bool:
        return self._settings.database_restore_enabled

    def restore_backup(self, *, file_name: str) -> None:
        if not self.enabled:
            raise PermissionError(self.FEATURE_DISABLED_MESSAGE)
        from app.shared.database_backup.engine import pg_restore_custom

        path = resolve_backup_path(file_name)
        pg_restore_custom(database_url=self._settings.database_url, dump_path=path)


@dataclass
class RestoreSystemBackupCommand:
    organization_id: UUID
    user_id: UUID
    user_email: str | None
    access_token: str
    backup_id: UUID


@dataclass
class RestoreSystemBackupFromUploadCommand:
    organization_id: UUID
    user_id: UUID
    user_email: str | None
    access_token: str
    original_file_name: str
    file_bytes: bytes
    notes: str | None


@dataclass
class DeleteSystemBackupCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    backup_id: UUID


@dataclass
class SystemBackupRestoreJobResult:
    id: UUID
    status: str
    source_type: str
    backup_id: UUID | None
    source_file_name: str
    checksum_sha256: str | None
    notes: str | None
    requested_by_user_id: UUID
    requested_by_email: str | None
    requested_at: datetime
    message: str
    uploaded: bool


def _restore_job_to_api_result(job: SystemBackupRestoreJob) -> SystemBackupRestoreJobResult:
    mapped = _restore_job_to_result(job)
    return SystemBackupRestoreJobResult(
        id=mapped.id,
        status=mapped.status,
        source_type=mapped.source_type,
        backup_id=mapped.backup_id,
        source_file_name=mapped.source_file_name,
        checksum_sha256=mapped.checksum_sha256,
        notes=mapped.notes,
        requested_by_user_id=mapped.requested_by_user_id,
        requested_by_email=mapped.requested_by_email,
        requested_at=mapped.requested_at,
        message=mapped.message,
        uploaded=mapped.uploaded,
    )


@dataclass
class DeleteSystemBackupResult:
    id: UUID
    file_name: str


class RestoreSystemBackupUseCase:
    def __init__(
        self,
        repository: SystemBackupRepository,
        restore_job_repository: SystemBackupRestoreJobRepository,
        authorization: AuthorizationPort,
        audit: AuditPort,
    ) -> None:
        self._repository = repository
        self._restore_job_repository = restore_job_repository
        self._authorization = authorization
        self._audit = audit
        self._settings = get_settings()

    def execute(self, command: RestoreSystemBackupCommand) -> SystemBackupRestoreJobResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_RESTORE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        backup = self._repository.get_by_id(command.organization_id, command.backup_id)
        if backup is None:
            raise LookupError("Backup not found")
        if backup.status.value != "completed":
            raise ValueError("Only completed backups can be restored")
        if backup.backup_format != BackupFormat.POSTGRESQL_DUMP:
            raise ValueError("Only PostgreSQL custom dump (.dump) backups can be restored")

        path = resolve_backup_path(backup.file_name)
        if not path.exists():
            raise FileNotFoundError("Backup file missing on disk")

        if not is_custom_pg_dump(path):
            raise ValueError("Backup file is not a PostgreSQL custom-format dump")

        try:
            verify_backup_dump(database_url=self._settings.database_url, dump_path=path)
        except DatabaseBackupError as exc:
            raise ValueError(str(exc)) from exc

        now = datetime.now(tz=UTC)
        job = SystemBackupRestoreJob.create(
            organization_id=command.organization_id,
            source_type=RestoreJobSourceType.EXISTING_BACKUP,
            backup_id=backup.id,
            uploaded_file_path=None,
            source_file_name=backup.file_name,
            checksum_sha256=backup.checksum,
            notes=None,
            requested_by_user_id=command.user_id,
            requested_by_email=command.user_email,
            now=now,
        )
        saved = self._restore_job_repository.add(job)
        result = _restore_job_to_api_result(saved)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.system_backup.restore_requested",
            resource_type="system_backup_restore_job",
            resource_id=str(saved.id),
            new_values={
                "status": result.status,
                "backup_id": str(backup.id),
                "source_file_name": backup.file_name,
                "checksum_sha256": backup.checksum,
            },
            metadata={"user_id": str(command.user_id), "source": "existing_backup"},
        )
        return result


class RestoreSystemBackupFromUploadUseCase:
    def __init__(
        self,
        restore_job_repository: SystemBackupRestoreJobRepository,
        authorization: AuthorizationPort,
        audit: AuditPort,
    ) -> None:
        self._restore_job_repository = restore_job_repository
        self._authorization = authorization
        self._audit = audit
        self._settings = get_settings()

    def execute(self, command: RestoreSystemBackupFromUploadCommand) -> SystemBackupRestoreJobResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_RESTORE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        original_name = Path(command.original_file_name).name
        if not original_name.lower().endswith(".dump"):
            raise ValueError("Only .dump files are accepted")
        if not command.file_bytes:
            raise ValueError("Uploaded file is empty")

        uploads_dir = get_restore_uploads_dir()
        uploads_dir.mkdir(parents=True, exist_ok=True)
        stored_name = generate_backup_filename(backup_format=BackupFormat.POSTGRESQL_DUMP)
        stored_path = uploads_dir / stored_name
        stored_path.write_bytes(command.file_bytes)

        if not is_custom_pg_dump(stored_path):
            stored_path.unlink(missing_ok=True)
            raise ValueError("File is not a PostgreSQL custom-format dump")

        try:
            verify_backup_dump(database_url=self._settings.database_url, dump_path=stored_path)
        except DatabaseBackupError as exc:
            stored_path.unlink(missing_ok=True)
            raise ValueError(str(exc)) from exc

        checksum = sha256_file(stored_path)
        now = datetime.now(tz=UTC)
        job = SystemBackupRestoreJob.create(
            organization_id=command.organization_id,
            source_type=RestoreJobSourceType.UPLOADED_FILE,
            backup_id=None,
            uploaded_file_path=relative_repo_path(stored_path),
            source_file_name=original_name,
            checksum_sha256=checksum,
            notes=command.notes,
            requested_by_user_id=command.user_id,
            requested_by_email=command.user_email,
            now=now,
        )
        saved = self._restore_job_repository.add(job)
        result = _restore_job_to_api_result(saved)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.system_backup.restore_upload_requested",
            resource_type="system_backup_restore_job",
            resource_id=str(saved.id),
            new_values={
                "status": result.status,
                "source_file_name": original_name,
                "stored_file_name": stored_name,
                "checksum_sha256": checksum,
                "uploaded_file_path": relative_repo_path(stored_path),
                "notes": command.notes,
            },
            metadata={"user_id": str(command.user_id), "source": "file_upload"},
        )
        return result


class DeleteSystemBackupUseCase:
    def __init__(
        self,
        repository: SystemBackupRepository,
        authorization: AuthorizationPort,
        audit: AuditPort,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: DeleteSystemBackupCommand) -> DeleteSystemBackupResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_DELETE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        backup = self._repository.get_by_id(command.organization_id, command.backup_id)
        if backup is None:
            raise LookupError("Backup not found")

        file_name = backup.file_name
        try:
            path = resolve_backup_path(file_name)
            if path.exists():
                path.unlink()
        except ValueError:
            pass

        if not self._repository.delete(command.organization_id, command.backup_id):
            raise LookupError("Backup not found")

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.system_backup.deleted",
            resource_type="system_backup",
            resource_id=str(command.backup_id),
            old_values={"file_name": file_name, "backup_format": backup.backup_format.value},
            metadata={"user_id": str(command.user_id)},
        )
        return DeleteSystemBackupResult(id=command.backup_id, file_name=file_name)
