from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.kyrox_core.client import HttpAuditAdapter, HttpAuthorizationAdapter
from app.integrations.kyrox_core.dev_bypass import (
    AllowAllAuthorizationAdapter,
    NoOpAuditAdapter,
    dev_bypass_enabled,
)
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.data_integration.application.get_import_job import GetImportJobUseCase
from app.modules.data_integration.application.import_job_runner import ImportJobRunner
from app.modules.data_integration.application.list_import_batches import ListImportBatchesUseCase
from app.modules.data_integration.application.select_import_sheet import SelectImportSheetUseCase
from app.modules.data_integration.application.start_import_analyze_job import StartImportAnalyzeJobUseCase
from app.modules.data_integration.application.start_import_apply_job import StartImportApplyJobUseCase
from app.modules.data_integration.infrastructure.repositories.job_repository import SqlAlchemyImportJobRepository
from app.modules.imports.api.dependencies import (
    get_analyze_import_use_case,
    get_apply_import_use_case,
    get_auth_context,
    get_bulk_row_decision_use_case,
    get_get_import_batch_use_case,
    get_import_batch_repository,
    get_import_row_repository,
    get_list_import_rows_use_case,
    get_set_column_mapping_use_case,
    get_set_row_decision_use_case,
    get_upload_raw_import_use_case,
    require_read_permission,
)
from app.modules.imports.infrastructure.repositories.import_repository import (
    SqlAlchemyImportBatchRepository,
    SqlAlchemyImportRowRepository,
)

_job_runner = ImportJobRunner()


def get_job_runner() -> ImportJobRunner:
    return _job_runner


def get_authorization_adapter() -> AuthorizationPort:
    if dev_bypass_enabled():
        return AllowAllAuthorizationAdapter()
    return HttpAuthorizationAdapter()


def get_audit_adapter() -> HttpAuditAdapter | NoOpAuditAdapter:
    if dev_bypass_enabled():
        return NoOpAuditAdapter()
    return HttpAuditAdapter()


def get_job_repository(db: Session = Depends(get_db)) -> SqlAlchemyImportJobRepository:
    return SqlAlchemyImportJobRepository(db)


def get_list_import_batches_use_case(
    batch_repository: SqlAlchemyImportBatchRepository = Depends(get_import_batch_repository),
    row_repository: SqlAlchemyImportRowRepository = Depends(get_import_row_repository),
) -> ListImportBatchesUseCase:
    return ListImportBatchesUseCase(batch_repository, row_repository)


def get_select_import_sheet_use_case(
    batch_repository: SqlAlchemyImportBatchRepository = Depends(get_import_batch_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> SelectImportSheetUseCase:
    return SelectImportSheetUseCase(batch_repository, authorization, audit)


def get_start_import_analyze_job_use_case(
    batch_repository: SqlAlchemyImportBatchRepository = Depends(get_import_batch_repository),
    job_repository: SqlAlchemyImportJobRepository = Depends(get_job_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> StartImportAnalyzeJobUseCase:
    return StartImportAnalyzeJobUseCase(batch_repository, job_repository, authorization)


def get_start_import_apply_job_use_case(
    batch_repository: SqlAlchemyImportBatchRepository = Depends(get_import_batch_repository),
    row_repository: SqlAlchemyImportRowRepository = Depends(get_import_row_repository),
    job_repository: SqlAlchemyImportJobRepository = Depends(get_job_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> StartImportApplyJobUseCase:
    return StartImportApplyJobUseCase(
        batch_repository, row_repository, job_repository, authorization
    )


def get_get_import_job_use_case(
    job_repository: SqlAlchemyImportJobRepository = Depends(get_job_repository),
) -> GetImportJobUseCase:
    return GetImportJobUseCase(job_repository)
