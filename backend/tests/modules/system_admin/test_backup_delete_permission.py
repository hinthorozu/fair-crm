from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.system_admin.api.dependencies import get_authorization_adapter
from app.modules.system_admin.application.backup_service import (
    DeleteSystemBackupCommand,
    DeleteSystemBackupUseCase,
)
from app.modules.system_admin.domain.entities import SystemBackup
from app.modules.system_admin.infrastructure.repositories.backup_repository import (
    SqlAlchemySystemBackupRepository,
)
from app.shared.database_backup.database_keys import DatabaseKey
from app.shared.database_backup.formats import BackupFormat


PERMISSION_CREATE = "fair_crm.admin.backups.create"
PERMISSION_DELETE = "fair_crm.admin.backups.delete"


class SelectiveAuthorization(AuthorizationPort):
    def __init__(self, allowed: set[str]) -> None:
        self.allowed = allowed
        self.requested: list[str] = []

    def check_permission(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        permission_code: str,
        access_token: str,
    ) -> bool:
        _ = (organization_id, user_id, access_token)
        self.requested.append(permission_code)
        return permission_code in self.allowed


def test_delete_backup_use_case_checks_delete_before_repository_access() -> None:
    repository = MagicMock()
    authorization = MagicMock()
    authorization.check_permission.return_value = False
    audit = MagicMock()
    use_case = DeleteSystemBackupUseCase(repository, authorization, audit)
    organization_id = uuid4()
    user_id = uuid4()
    backup_id = uuid4()

    with pytest.raises(ForbiddenError):
        use_case.execute(
            DeleteSystemBackupCommand(
                organization_id=organization_id,
                user_id=user_id,
                access_token="token",
                backup_id=backup_id,
            )
        )

    authorization.check_permission.assert_called_once_with(
        organization_id=organization_id,
        user_id=user_id,
        permission_code=PERMISSION_DELETE,
        access_token="token",
    )
    repository.get_by_id.assert_not_called()
    repository.delete.assert_not_called()
    audit.record_event.assert_not_called()


def test_delete_backup_route_rejects_create_without_delete(client, auth_headers) -> None:
    authorization = SelectiveAuthorization({PERMISSION_CREATE})
    client.app.dependency_overrides[get_authorization_adapter] = lambda: authorization
    try:
        response = client.delete(
            f"/api/v1/admin/backups/{uuid4()}",
            headers=auth_headers,
        )
    finally:
        client.app.dependency_overrides.pop(get_authorization_adapter, None)

    assert response.status_code == 403
    assert authorization.requested == [PERMISSION_DELETE]


def test_delete_backup_route_accepts_delete_without_create(client, auth_headers) -> None:
    authorization = SelectiveAuthorization({PERMISSION_DELETE})
    client.app.dependency_overrides[get_authorization_adapter] = lambda: authorization
    try:
        response = client.delete(
            f"/api/v1/admin/backups/{uuid4()}",
            headers=auth_headers,
        )
    finally:
        client.app.dependency_overrides.pop(get_authorization_adapter, None)

    assert response.status_code == 404
    assert authorization.requested == [PERMISSION_DELETE, PERMISSION_DELETE]


def test_delete_backup_cannot_cross_organization_scope(
    client,
    auth_headers,
    organization_id,
    other_organization_id,
    user_id,
    db_session,
) -> None:
    repository = SqlAlchemySystemBackupRepository(db_session)
    backup = repository.add(
        SystemBackup.create(
            organization_id=organization_id,
            database_key=DatabaseKey.FAIR_CRM,
            file_name="tenant_scope_delete_test.dump",
            backup_format=BackupFormat.POSTGRESQL_DUMP,
            created_by=user_id,
            created_by_email=None,
            notes="tenant-scope-delete-test",
            now=datetime.now(tz=UTC),
        )
    )
    authorization = SelectiveAuthorization({PERMISSION_DELETE})
    client.app.dependency_overrides[get_authorization_adapter] = lambda: authorization
    try:
        wrong_org_headers = dict(auth_headers)
        wrong_org_headers["X-Organization-Id"] = str(other_organization_id)
        wrong_org_delete = client.delete(
            f"/api/v1/admin/backups/{backup.id}",
            headers=wrong_org_headers,
        )
    finally:
        client.app.dependency_overrides.pop(get_authorization_adapter, None)

    assert wrong_org_delete.status_code == 404
    assert repository.get_by_id(organization_id, backup.id) is not None


def test_delete_restore_job_route_requires_delete_permission(client, auth_headers) -> None:
    authorization = SelectiveAuthorization({PERMISSION_CREATE})
    client.app.dependency_overrides[get_authorization_adapter] = lambda: authorization
    try:
        response = client.delete(
            f"/api/v1/admin/backups/restore-jobs/{uuid4()}",
            headers=auth_headers,
        )
    finally:
        client.app.dependency_overrides.pop(get_authorization_adapter, None)

    assert response.status_code == 403
    assert authorization.requested == [PERMISSION_DELETE]


def test_restore_stays_on_create_permission(client, auth_headers) -> None:
    authorization = SelectiveAuthorization({PERMISSION_CREATE})
    client.app.dependency_overrides[get_authorization_adapter] = lambda: authorization
    try:
        response = client.post(
            f"/api/v1/admin/backups/{uuid4()}/restore",
            headers=auth_headers,
        )
    finally:
        client.app.dependency_overrides.pop(get_authorization_adapter, None)

    assert response.status_code == 404
    assert authorization.requested == [PERMISSION_CREATE, PERMISSION_CREATE]
