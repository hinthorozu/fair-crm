from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

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
from app.modules.activities.infrastructure.repositories.activity_repository import (
    SqlAlchemyActivityRepository,
)
from app.modules.contacts.infrastructure.repositories.contact_repository import (
    SqlAlchemyContactRepository,
)
from app.modules.customers.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)
from app.modules.imports.application.apply_import import ApplyImportUseCase
from app.modules.imports.application.get_import_batch import GetImportBatchUseCase
from app.modules.imports.application.list_import_rows import ListImportRowsUseCase
from app.modules.imports.application.set_row_decision import SetImportRowDecisionUseCase
from app.modules.imports.application.upload_import import UploadCustomerImportUseCase
from app.modules.imports.infrastructure.repositories.import_repository import (
    SqlAlchemyImportBatchRepository,
    SqlAlchemyImportRowRepository,
)

bearer_scheme = HTTPBearer(auto_error=False)

PERMISSION_READ = "fair_crm.imports.read"


def get_import_batch_repository(db: Session = Depends(get_db)) -> SqlAlchemyImportBatchRepository:
    return SqlAlchemyImportBatchRepository(db)


def get_import_row_repository(db: Session = Depends(get_db)) -> SqlAlchemyImportRowRepository:
    return SqlAlchemyImportRowRepository(db)


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


def require_read_permission(
    auth: AuthContext = Depends(get_auth_context),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AuthContext:
    if dev_bypass_enabled():
        return auth
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if not authorization.check_permission(
        organization_id=auth.organization_id,
        user_id=auth.user_id,
        permission_code=PERMISSION_READ,
        access_token=credentials.credentials,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return auth


def get_upload_import_use_case(
    batch_repository: SqlAlchemyImportBatchRepository = Depends(get_import_batch_repository),
    row_repository: SqlAlchemyImportRowRepository = Depends(get_import_row_repository),
    db: Session = Depends(get_db),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> UploadCustomerImportUseCase:
    return UploadCustomerImportUseCase(
        batch_repository,
        row_repository,
        SqlAlchemyCustomerRepository(db),
        authorization,
        audit,
    )


def get_get_import_batch_use_case(
    batch_repository: SqlAlchemyImportBatchRepository = Depends(get_import_batch_repository),
    row_repository: SqlAlchemyImportRowRepository = Depends(get_import_row_repository),
) -> GetImportBatchUseCase:
    return GetImportBatchUseCase(batch_repository, row_repository)


def get_list_import_rows_use_case(
    batch_repository: SqlAlchemyImportBatchRepository = Depends(get_import_batch_repository),
    row_repository: SqlAlchemyImportRowRepository = Depends(get_import_row_repository),
    db: Session = Depends(get_db),
) -> ListImportRowsUseCase:
    return ListImportRowsUseCase(
        batch_repository,
        row_repository,
        SqlAlchemyCustomerRepository(db),
    )


def get_set_row_decision_use_case(
    batch_repository: SqlAlchemyImportBatchRepository = Depends(get_import_batch_repository),
    row_repository: SqlAlchemyImportRowRepository = Depends(get_import_row_repository),
    db: Session = Depends(get_db),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> SetImportRowDecisionUseCase:
    return SetImportRowDecisionUseCase(
        batch_repository,
        row_repository,
        SqlAlchemyCustomerRepository(db),
        authorization,
        audit,
    )


def get_apply_import_use_case(
    batch_repository: SqlAlchemyImportBatchRepository = Depends(get_import_batch_repository),
    row_repository: SqlAlchemyImportRowRepository = Depends(get_import_row_repository),
    db: Session = Depends(get_db),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> ApplyImportUseCase:
    return ApplyImportUseCase(
        batch_repository,
        row_repository,
        SqlAlchemyCustomerRepository(db),
        SqlAlchemyContactRepository(db),
        SqlAlchemyActivityRepository(db),
        authorization,
        audit,
    )
