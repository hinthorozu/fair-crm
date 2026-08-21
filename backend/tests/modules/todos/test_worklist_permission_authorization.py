from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.todos.api.dependencies import get_authorization_adapter
from app.modules.todos.application.record_todo_worklist_activity import (
    PERMISSION_UPDATE,
    RecordTodoWorklistActivityUseCase,
)
from app.modules.todos.application.send_manual_task_mail import (
    PERMISSION_MAIL_SEND_EXECUTE,
    SendManualTaskMailUseCase,
)
from app.modules.todos.application.worklist_commands import (
    RecordTodoWorklistActivityCommand,
    SendManualTaskMailCommand,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from fair_crm_role_matrix import ALL_FAIR_CRM_PERMISSIONS, permissions_for_role, role_slugs  # noqa: E402

PERMISSION_CREATE = ".".join(("fair_crm", "todos", "create"))
PERMISSION_TODOS_EXECUTE = ".".join(("fair_crm", "todos", "execute"))


class SelectiveAuthorization(AuthorizationPort):
    def __init__(self, *, denied: set[str] | None = None) -> None:
        self._denied = denied or set()

    def check_permission(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        permission_code: str,
        access_token: str,
    ) -> bool:
        _ = (organization_id, user_id, access_token)
        return permission_code not in self._denied


def _activity_command() -> RecordTodoWorklistActivityCommand:
    return RecordTodoWorklistActivityCommand(
        organization_id=uuid4(),
        access_token="token",
        user_id=uuid4(),
        todo_id=uuid4(),
        customer_id=uuid4(),
        outcome_id=uuid4(),
        note="Permission regression",
    )


def _manual_mail_command() -> SendManualTaskMailCommand:
    return SendManualTaskMailCommand(
        organization_id=uuid4(),
        access_token="token",
        user_id=uuid4(),
        todo_id=uuid4(),
        customer_id=uuid4(),
        email_account_id=uuid4(),
        recipients="recipient@example.com",
        subject="Permission regression",
        body="Body",
    )


def test_record_worklist_activity_requires_todo_update_before_resource_lookup() -> None:
    authorization = Mock()
    authorization.check_permission.return_value = False
    todo_repository = Mock()
    use_case = RecordTodoWorklistActivityUseCase(
        todo_repository=todo_repository,
        outcome_repository=Mock(),
        worklist_state_repository=Mock(),
        worklist_query_repository=Mock(),
        activity_repository=Mock(),
        participation_repository=Mock(),
        authorization=authorization,
    )
    command = _activity_command()

    with pytest.raises(ForbiddenError):
        use_case.execute(command)

    authorization.check_permission.assert_called_once_with(
        organization_id=command.organization_id,
        user_id=command.user_id,
        permission_code=PERMISSION_UPDATE,
        access_token=command.access_token,
    )
    todo_repository.get_by_id.assert_not_called()


def test_manual_task_mail_requires_mail_send_execute_before_resource_lookup() -> None:
    authorization = Mock()
    authorization.check_permission.return_value = False
    todo_repository = Mock()
    use_case = SendManualTaskMailUseCase(
        todo_repository=todo_repository,
        participation_repository=Mock(),
        smtp_repository=Mock(),
        template_repository=Mock(),
        mail_send_operations=Mock(),
        authorization=authorization,
    )
    command = _manual_mail_command()

    with pytest.raises(ForbiddenError):
        use_case.execute(command)

    authorization.check_permission.assert_called_once_with(
        organization_id=command.organization_id,
        user_id=command.user_id,
        permission_code=PERMISSION_MAIL_SEND_EXECUTE,
        access_token=command.access_token,
    )
    todo_repository.get_by_id.assert_not_called()


def test_worklist_activity_endpoint_denies_update_before_resource_lookup(
    client,
    auth_headers,
) -> None:
    client.app.dependency_overrides[get_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={PERMISSION_UPDATE}
    )
    try:
        response = client.post(
            f"/api/v1/todos/{uuid4()}/worklist/customers/{uuid4()}/activities",
            headers=auth_headers,
            json={"outcome_id": str(uuid4()), "note": "Denied"},
        )
    finally:
        client.app.dependency_overrides.pop(get_authorization_adapter, None)

    assert response.status_code == 403


def test_worklist_activity_endpoint_does_not_require_todo_create(
    client,
    auth_headers,
) -> None:
    client.app.dependency_overrides[get_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={PERMISSION_CREATE}
    )
    try:
        response = client.post(
            f"/api/v1/todos/{uuid4()}/worklist/customers/{uuid4()}/activities",
            headers=auth_headers,
            json={"outcome_id": str(uuid4()), "note": "Allowed past guard"},
        )
    finally:
        client.app.dependency_overrides.pop(get_authorization_adapter, None)

    assert response.status_code == 404


def test_manual_mail_endpoint_denies_execute_before_resource_lookup(
    client,
    auth_headers,
) -> None:
    client.app.dependency_overrides[get_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={PERMISSION_MAIL_SEND_EXECUTE}
    )
    try:
        response = client.post(
            f"/api/v1/todos/{uuid4()}/worklist/customers/{uuid4()}/manual-mail",
            headers=auth_headers,
            json={
                "email_account_id": str(uuid4()),
                "recipients": "recipient@example.com",
                "subject": "Denied",
                "body": "Body",
            },
        )
    finally:
        client.app.dependency_overrides.pop(get_authorization_adapter, None)

    assert response.status_code == 403


def test_manual_mail_endpoint_does_not_require_todo_create(
    client,
    auth_headers,
) -> None:
    client.app.dependency_overrides[get_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={PERMISSION_CREATE}
    )
    try:
        response = client.post(
            f"/api/v1/todos/{uuid4()}/worklist/customers/{uuid4()}/manual-mail",
            headers=auth_headers,
            json={
                "email_account_id": str(uuid4()),
                "recipients": "recipient@example.com",
                "subject": "Allowed past guard",
                "body": "Body",
            },
        )
    finally:
        client.app.dependency_overrides.pop(get_authorization_adapter, None)

    assert response.status_code == 404


def test_role_matrix_references_worklist_permissions_without_todos_execute() -> None:
    assert PERMISSION_UPDATE in ALL_FAIR_CRM_PERMISSIONS
    assert PERMISSION_MAIL_SEND_EXECUTE in ALL_FAIR_CRM_PERMISSIONS
    assert PERMISSION_TODOS_EXECUTE not in ALL_FAIR_CRM_PERMISSIONS

    for role_slug in role_slugs():
        assert PERMISSION_TODOS_EXECUTE not in permissions_for_role(role_slug)

    organization_admin = permissions_for_role("organization_admin")
    assert PERMISSION_UPDATE in organization_admin
    assert PERMISSION_MAIL_SEND_EXECUTE in organization_admin
