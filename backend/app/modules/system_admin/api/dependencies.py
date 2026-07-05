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
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
from app.modules.system_admin.application.backup_job_runner import BackupJobRunner
from app.modules.system_admin.application.backup_service import (
    CreateSystemBackupUseCase,
    DownloadSystemBackupUseCase,
    GetSystemBackupUseCase,
    ListSystemBackupsUseCase,
    RestoreService,
)
from app.modules.customers.infrastructure.repositories.customer_communication_repository import (
    SqlAlchemyCustomerCommunicationRepository,
)
from app.modules.system_admin.application.duplicate_group_merge_audit import DuplicateGroupMergeAuditRecorder
from app.modules.system_admin.application.data_operation_job_runner import DataOperationJobRunner
from app.modules.system_admin.application.data_operation_service import (
    AssignCustomersToFairUseCase,
    DeleteSelectedCustomersUseCase,
    DownloadDataOperationFileUseCase,
    ExportDataOperationDatasetCustomersUseCase,
    ExportDataOperationDuplicateCustomersUseCase,
    GetDataOperationDuplicateGroupDetailUseCase,
    GetDataOperationRunUseCase,
    ListDataOperationDatasetCustomersUseCase,
    ListDataOperationDuplicateCustomersUseCase,
    ListDataOperationDuplicateGroupsUseCase,
    ListDataOperationsUseCase,
    PERMISSION_READ as DATA_OPERATIONS_PERMISSION_READ,
    PERMISSION_RUN as DATA_OPERATIONS_PERMISSION_RUN,
    PreviewDuplicateGroupMergeUseCase,
    ExecuteDuplicateGroupMergeUseCase,
    RunDataOperationUseCase,
)
from app.modules.system_admin.infrastructure.repositories.backup_repository import (
    SqlAlchemySystemBackupRepository,
)
from app.modules.system_admin.infrastructure.repositories.data_operation_dataset_repository import (
    SqlAlchemyDataOperationDatasetRepository,
)
from app.modules.system_admin.infrastructure.repositories.data_operation_run_repository import (
    SqlAlchemyDataOperationRunRepository,
)

bearer_scheme = HTTPBearer(auto_error=False)

PERMISSION_READ = "fair_crm.admin.backups.read"
PERMISSION_CREATE = "fair_crm.admin.backups.create"
PERMISSION_DOWNLOAD = "fair_crm.admin.backups.download"


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


def require_admin_create_permission(
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> AuthContext:
    token = credentials.credentials if credentials and credentials.credentials else ""
    if not authorization.check_permission(
        organization_id=auth.organization_id,
        user_id=auth.user_id,
        permission_code=PERMISSION_CREATE,
        access_token=token,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required")
    return auth


def require_admin_download_permission(
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> AuthContext:
    token = credentials.credentials if credentials and credentials.credentials else ""
    if not authorization.check_permission(
        organization_id=auth.organization_id,
        user_id=auth.user_id,
        permission_code=PERMISSION_DOWNLOAD,
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


def get_data_operation_run_repository(db: Session = Depends(get_db)) -> SqlAlchemyDataOperationRunRepository:
    return SqlAlchemyDataOperationRunRepository(db)


def get_data_operation_dataset_repository(
    db: Session = Depends(get_db),
) -> SqlAlchemyDataOperationDatasetRepository:
    return SqlAlchemyDataOperationDatasetRepository(db)


_data_operation_job_runner = DataOperationJobRunner()


def get_data_operation_job_runner() -> DataOperationJobRunner:
    return _data_operation_job_runner


def require_data_operations_read_permission(
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> AuthContext:
    token = credentials.credentials if credentials and credentials.credentials else ""
    if not authorization.check_permission(
        organization_id=auth.organization_id,
        user_id=auth.user_id,
        permission_code=DATA_OPERATIONS_PERMISSION_READ,
        access_token=token,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required")
    return auth


def require_data_operations_run_permission(
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> AuthContext:
    token = credentials.credentials if credentials and credentials.credentials else ""
    if not authorization.check_permission(
        organization_id=auth.organization_id,
        user_id=auth.user_id,
        permission_code=DATA_OPERATIONS_PERMISSION_RUN,
        access_token=token,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required")
    return auth


def get_list_data_operations_use_case(
    repository: SqlAlchemyDataOperationRunRepository = Depends(get_data_operation_run_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> ListDataOperationsUseCase:
    return ListDataOperationsUseCase(repository, authorization)


def get_run_data_operation_use_case(
    repository: SqlAlchemyDataOperationRunRepository = Depends(get_data_operation_run_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> RunDataOperationUseCase:
    return RunDataOperationUseCase(repository, authorization)


def get_get_data_operation_run_use_case(
    repository: SqlAlchemyDataOperationRunRepository = Depends(get_data_operation_run_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> GetDataOperationRunUseCase:
    return GetDataOperationRunUseCase(repository, authorization)


def get_download_data_operation_file_use_case(
    repository: SqlAlchemyDataOperationRunRepository = Depends(get_data_operation_run_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> DownloadDataOperationFileUseCase:
    return DownloadDataOperationFileUseCase(repository, authorization)


def get_list_data_operation_dataset_customers_use_case(
    run_repository: SqlAlchemyDataOperationRunRepository = Depends(get_data_operation_run_repository),
    dataset_repository: SqlAlchemyDataOperationDatasetRepository = Depends(get_data_operation_dataset_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> ListDataOperationDatasetCustomersUseCase:
    return ListDataOperationDatasetCustomersUseCase(run_repository, dataset_repository, authorization)


def get_export_data_operation_dataset_customers_use_case(
    run_repository: SqlAlchemyDataOperationRunRepository = Depends(get_data_operation_run_repository),
    dataset_repository: SqlAlchemyDataOperationDatasetRepository = Depends(get_data_operation_dataset_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> ExportDataOperationDatasetCustomersUseCase:
    return ExportDataOperationDatasetCustomersUseCase(run_repository, dataset_repository, authorization)


def get_list_data_operation_duplicate_groups_use_case(
    run_repository: SqlAlchemyDataOperationRunRepository = Depends(get_data_operation_run_repository),
    dataset_repository: SqlAlchemyDataOperationDatasetRepository = Depends(get_data_operation_dataset_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> ListDataOperationDuplicateGroupsUseCase:
    return ListDataOperationDuplicateGroupsUseCase(run_repository, dataset_repository, authorization)


def get_get_data_operation_duplicate_group_detail_use_case(
    run_repository: SqlAlchemyDataOperationRunRepository = Depends(get_data_operation_run_repository),
    dataset_repository: SqlAlchemyDataOperationDatasetRepository = Depends(get_data_operation_dataset_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> GetDataOperationDuplicateGroupDetailUseCase:
    return GetDataOperationDuplicateGroupDetailUseCase(run_repository, dataset_repository, authorization)


def get_preview_duplicate_group_merge_use_case(
    run_repository: SqlAlchemyDataOperationRunRepository = Depends(get_data_operation_run_repository),
    dataset_repository: SqlAlchemyDataOperationDatasetRepository = Depends(get_data_operation_dataset_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    db: Session = Depends(get_db),
) -> PreviewDuplicateGroupMergeUseCase:
    return PreviewDuplicateGroupMergeUseCase(
        run_repository,
        dataset_repository,
        authorization,
        SqlAlchemyCustomerCommunicationRepository(db),
    )


def get_execute_duplicate_group_merge_use_case(
    run_repository: SqlAlchemyDataOperationRunRepository = Depends(get_data_operation_run_repository),
    dataset_repository: SqlAlchemyDataOperationDatasetRepository = Depends(get_data_operation_dataset_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    db: Session = Depends(get_db),
) -> ExecuteDuplicateGroupMergeUseCase:
    return ExecuteDuplicateGroupMergeUseCase(
        run_repository,
        dataset_repository,
        authorization,
        SqlAlchemyCustomerCommunicationRepository(db),
        db,
    )


def get_duplicate_group_merge_audit_recorder(
    db: Session = Depends(get_db),
) -> DuplicateGroupMergeAuditRecorder:
    return DuplicateGroupMergeAuditRecorder(
        db,
        SqlAlchemyCustomerCommunicationRepository(db),
    )


def get_list_data_operation_duplicate_customers_use_case(
    run_repository: SqlAlchemyDataOperationRunRepository = Depends(get_data_operation_run_repository),
    dataset_repository: SqlAlchemyDataOperationDatasetRepository = Depends(get_data_operation_dataset_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> ListDataOperationDuplicateCustomersUseCase:
    return ListDataOperationDuplicateCustomersUseCase(run_repository, dataset_repository, authorization)


def get_export_data_operation_duplicate_customers_use_case(
    run_repository: SqlAlchemyDataOperationRunRepository = Depends(get_data_operation_run_repository),
    dataset_repository: SqlAlchemyDataOperationDatasetRepository = Depends(get_data_operation_dataset_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> ExportDataOperationDuplicateCustomersUseCase:
    return ExportDataOperationDuplicateCustomersUseCase(run_repository, dataset_repository, authorization)


def get_assign_customers_to_fair_use_case(
    run_repository: SqlAlchemyDataOperationRunRepository = Depends(get_data_operation_run_repository),
    dataset_repository: SqlAlchemyDataOperationDatasetRepository = Depends(get_data_operation_dataset_repository),
    db: Session = Depends(get_db),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> AssignCustomersToFairUseCase:
    return AssignCustomersToFairUseCase(
        run_repository,
        dataset_repository,
        SqlAlchemyFairRepository(db),
        authorization,
    )


def get_delete_selected_customers_use_case(
    run_repository: SqlAlchemyDataOperationRunRepository = Depends(get_data_operation_run_repository),
    dataset_repository: SqlAlchemyDataOperationDatasetRepository = Depends(get_data_operation_dataset_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> DeleteSelectedCustomersUseCase:
    return DeleteSelectedCustomersUseCase(run_repository, dataset_repository, authorization)


def access_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    return credentials.credentials if credentials and credentials.credentials else ""
