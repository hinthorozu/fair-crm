from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.integrations.kyrox_core.auth import AuthContext
from app.integrations.kyrox_core.client import HttpAuditAdapter, HttpAuthorizationAdapter
from app.integrations.kyrox_core.dev_bypass import (
    AllowAllAuthorizationAdapter,
    NoOpAuditAdapter,
    dev_bypass_enabled,
    resolve_auth_context,
)
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.system_admin.application.backup_job_runner import BackupJobRunner
from app.modules.system_admin.application.backup_service import (
    CreateSystemBackupUseCase,
    DownloadSystemBackupUseCase,
    GetSystemBackupUseCase,
    ListSystemBackupsUseCase,
    RestoreService,
)
from app.modules.system_admin.infrastructure.repositories.backup_repository import (
    SqlAlchemySystemBackupRepository,
)

bearer_scheme = HTTPBearer(auto_error=False)

PERMISSION_READ = "fair_crm.admin.backups.read"


def get_authorization_adapter() -> AuthorizationPort:
    if dev_bypass_enabled():
        return AllowAllAuthorizationAdapter()
    return HttpAuthorizationAdapter()


def get_audit_adapter() -> HttpAuditAdapter | NoOpAuditAdapter:
    if dev_bypass_enabled():
        return NoOpAuditAdapter()
    return HttpAuditAdapter()


def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    organization_id: UUID = Header(..., alias="X-Organization-Id"),
    dev_user_id: UUID | None = Header(default=None, alias="X-Dev-User-Id"),
) -> AuthContext:
    try:
        return resolve_auth_context(credentials, organization_id, dev_user_id=dev_user_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated") from exc


def require_admin_read_permission(
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> AuthContext:
    token = credentials.credentials if credentials and credentials.credentials else ""
    if not authorization.check_permission(
        organization_id=auth.organization_id,
        user_id=auth.user_id,
        permission_code=PERMISSION_READ,
        access_token=token,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required")
    return auth


def get_backup_repository(db: Session = Depends(get_db)) -> SqlAlchemySystemBackupRepository:
    return SqlAlchemySystemBackupRepository(db)


_backup_job_runner = BackupJobRunner()


def get_backup_job_runner() -> BackupJobRunner:
    return _backup_job_runner


def get_create_backup_use_case(
    repository: SqlAlchemySystemBackupRepository = Depends(get_backup_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> CreateSystemBackupUseCase:
    return CreateSystemBackupUseCase(repository, authorization)


def get_list_backups_use_case(
    repository: SqlAlchemySystemBackupRepository = Depends(get_backup_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> ListSystemBackupsUseCase:
    return ListSystemBackupsUseCase(repository, authorization)


def get_get_backup_use_case(
    repository: SqlAlchemySystemBackupRepository = Depends(get_backup_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> GetSystemBackupUseCase:
    return GetSystemBackupUseCase(repository, authorization)


def get_download_backup_use_case(
    repository: SqlAlchemySystemBackupRepository = Depends(get_backup_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> DownloadSystemBackupUseCase:
    return DownloadSystemBackupUseCase(repository, authorization)


def get_restore_service() -> RestoreService:
    return RestoreService()


def access_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    return credentials.credentials if credentials and credentials.credentials else ""
