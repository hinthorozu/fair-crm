from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.integrations.kyrox_core.auth import create_test_token
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.main import create_app
from app.modules.activities.api.dependencies import (
    get_audit_adapter as get_activity_audit_adapter,
    get_authorization_adapter as get_activity_authorization_adapter,
)
from app.modules.activities.infrastructure.persistence.models import ActivityModel  # noqa: F401
from app.modules.contacts.api.dependencies import (
    get_audit_adapter as get_contact_audit_adapter,
    get_authorization_adapter as get_contact_authorization_adapter,
)
from app.modules.contacts.infrastructure.persistence.models import ContactModel  # noqa: F401
from app.modules.customers.api.dependencies import (
    get_audit_adapter as get_customer_audit_adapter,
    get_authorization_adapter as get_customer_authorization_adapter,
)
from app.modules.customers.infrastructure.persistence.communication_models import (  # noqa: F401
    CustomerEmailModel,
    CustomerPhoneModel,
    CustomerWebsiteModel,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel  # noqa: F401
from app.modules.fairs.api.dependencies import (
    get_audit_adapter as get_fair_audit_adapter,
    get_authorization_adapter as get_fair_authorization_adapter,
)
from app.modules.fairs.infrastructure.persistence.models import FairModel  # noqa: F401
from app.modules.data_integration.api.dependencies import (
    get_audit_adapter as get_data_integration_audit_adapter,
    get_authorization_adapter as get_data_integration_authorization_adapter,
)
from app.modules.data_integration.application.import_job_runner import ImportJobRunner
from app.modules.system_admin.api.dependencies import get_authorization_adapter as get_system_admin_authorization_adapter
from app.modules.system_admin.application.backup_job_runner import BackupJobRunner
from app.modules.system_admin.application.data_operation_job_runner import DataOperationJobRunner
from app.modules.data_integration.infrastructure.persistence.models import ImportJobModel  # noqa: F401
from app.modules.imports.api.dependencies import (
    get_audit_adapter as get_import_audit_adapter,
    get_authorization_adapter as get_import_authorization_adapter,
)
from app.modules.imports.infrastructure.persistence.models import ImportBatchModel, ImportRowModel  # noqa: F401
from app.modules.system_admin.infrastructure.persistence.models import (  # noqa: F401
    DuplicateGroupMergeAuditLogModel,
    SystemBackupModel,
    SystemDataOperationDatasetRowModel,
    SystemDataOperationRunModel,
)
from app.modules.participations.api.dependencies import (
    get_audit_adapter as get_participation_audit_adapter,
    get_authorization_adapter as get_participation_authorization_adapter,
)
from app.modules.participations.infrastructure.persistence.models import (  # noqa: F401
    CustomerFairParticipationModel,
)


class AllowAllAuthorization(AuthorizationPort):
    def check_permission(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        permission_code: str,
        access_token: str,
    ) -> bool:
        _ = (organization_id, user_id, permission_code, access_token)
        return True


class DenyAllAuthorization(AuthorizationPort):
    def check_permission(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        permission_code: str,
        access_token: str,
    ) -> bool:
        _ = (organization_id, user_id, permission_code, access_token)
        return False


class NoOpAudit:
    def record_event(self, **kwargs) -> None:
        _ = kwargs


@pytest.fixture
def test_engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _sqlite_enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    @event.listens_for(engine, "checkout")
    def _sqlite_enable_foreign_keys_on_checkout(dbapi_connection, _connection_record, _connection_proxy):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_engine) -> Generator[Session, None, None]:
    connection = test_engine.connect()
    transaction = connection.begin()
    TestingSessionLocal = sessionmaker(bind=connection)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def organization_id() -> UUID:
    return uuid4()


@pytest.fixture
def other_organization_id() -> UUID:
    return uuid4()


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def auth_headers(user_id: UUID, organization_id: UUID) -> dict[str, str]:
    token = create_test_token(user_id=user_id)
    return {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": str(organization_id),
    }


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("FAIR_CRM_DEV_BYPASS_CORE", "false")
    get_settings.cache_clear()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session
        db_session.flush()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_customer_authorization_adapter] = lambda: AllowAllAuthorization()
    app.dependency_overrides[get_customer_audit_adapter] = lambda: NoOpAudit()
    app.dependency_overrides[get_fair_authorization_adapter] = lambda: AllowAllAuthorization()
    app.dependency_overrides[get_fair_audit_adapter] = lambda: NoOpAudit()
    app.dependency_overrides[get_contact_authorization_adapter] = lambda: AllowAllAuthorization()
    app.dependency_overrides[get_contact_audit_adapter] = lambda: NoOpAudit()
    app.dependency_overrides[get_activity_authorization_adapter] = lambda: AllowAllAuthorization()
    app.dependency_overrides[get_activity_audit_adapter] = lambda: NoOpAudit()
    app.dependency_overrides[get_import_authorization_adapter] = lambda: AllowAllAuthorization()
    app.dependency_overrides[get_import_audit_adapter] = lambda: NoOpAudit()
    app.dependency_overrides[get_participation_authorization_adapter] = lambda: AllowAllAuthorization()
    app.dependency_overrides[get_participation_audit_adapter] = lambda: NoOpAudit()
    app.dependency_overrides[get_data_integration_authorization_adapter] = lambda: AllowAllAuthorization()
    app.dependency_overrides[get_data_integration_audit_adapter] = lambda: NoOpAudit()
    app.dependency_overrides[get_system_admin_authorization_adapter] = lambda: AllowAllAuthorization()

    import app.modules.data_integration.api.dependencies as data_integration_dependencies
    import app.modules.imports.api.dependencies as imports_dependencies
    import app.modules.system_admin.api.dependencies as system_admin_dependencies

    shared_job_runner = ImportJobRunner(session_factory=lambda: db_session)
    data_integration_dependencies._job_runner = shared_job_runner
    imports_dependencies._import_job_runner = shared_job_runner
    system_admin_dependencies._backup_job_runner = BackupJobRunner(session_factory=lambda: db_session)
    system_admin_dependencies._data_operation_job_runner = DataOperationJobRunner(
        session_factory=lambda: db_session
    )

    return TestClient(app)
