from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.core.pagination import normalize_sort_direction
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.system_admin.domain.entities import SystemBackup
from app.modules.system_admin.domain.ports import SystemBackupRepository
from app.shared.database_backup.paths import generate_backup_filename, resolve_backup_path

PERMISSION_CREATE = "fair_crm.admin.backups.create"

BACKUP_ALLOWED_SORT_FIELDS = frozenset(
    {
        "file_name",
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


@dataclass
class CreateSystemBackupResult:
    backup_id: UUID
    file_name: str
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
        file_name = generate_backup_filename(now=now)
        backup = SystemBackup.create(
            organization_id=command.organization_id,
            file_name=file_name,
            created_by=command.user_id,
            created_by_email=command.user_email,
            notes=command.notes,
            now=now,
        )
        saved = self._repository.add(backup)
        return CreateSystemBackupResult(
            backup_id=saved.id,
            file_name=saved.file_name,
            status=saved.status.value,
            progress_stage=saved.progress_stage.value,
        )


@dataclass
class GetSystemBackupResult:
    id: UUID
    file_name: str
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


def _to_result(backup: SystemBackup) -> GetSystemBackupResult:
    return GetSystemBackupResult(
        id=backup.id,
        file_name=backup.file_name,
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
        download_count=backup.download_count,
        error_message=backup.error_message,
    )


class RestoreService:
    """Restore foundation — disabled until explicitly enabled in configuration."""

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
