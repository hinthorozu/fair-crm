"""Authorization tests for operation type capability updates."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import ForbiddenError
from app.modules.operations.application.update_operation_type_capabilities import (
    UpdateOperationTypeCapabilitiesCommand,
    UpdateOperationTypeCapabilitiesUseCase,
)
from app.modules.operations.domain.value_objects import HandlerCapabilities


def _command() -> UpdateOperationTypeCapabilitiesCommand:
    return UpdateOperationTypeCapabilitiesCommand(
        organization_id=uuid4(),
        user_id=uuid4(),
        access_token="token",
        key="reminder",
        capabilities=HandlerCapabilities(
            supports_pause=True,
            supports_resume=False,
            supports_retry=True,
            supports_schedule=True,
            supports_items=True,
        ),
        is_active=True,
    )


def test_update_operation_type_capabilities_requires_update_permission():
    repository = MagicMock()
    authorization = MagicMock()
    authorization.check_permission.return_value = False
    command = _command()

    use_case = UpdateOperationTypeCapabilitiesUseCase(repository, authorization)

    with pytest.raises(ForbiddenError):
        use_case.execute(command)

    authorization.check_permission.assert_called_once_with(
        organization_id=command.organization_id,
        user_id=command.user_id,
        permission_code="fair_crm.operations.update",
        access_token=command.access_token,
    )
    repository.update_capabilities.assert_not_called()


def test_update_operation_type_capabilities_allows_update_permission():
    repository = MagicMock()
    authorization = MagicMock()
    authorization.check_permission.return_value = True
    command = _command()
    repository.update_capabilities.return_value = SimpleNamespace(
        key="reminder",
        name="Reminder",
        is_active=True,
        sort_order=20,
        supports_pause=True,
        supports_resume=False,
        supports_retry=True,
        supports_schedule=True,
        supports_items=True,
        updated_at=datetime.now(tz=UTC),
    )

    use_case = UpdateOperationTypeCapabilitiesUseCase(repository, authorization)
    result = use_case.execute(command)

    authorization.check_permission.assert_called_once_with(
        organization_id=command.organization_id,
        user_id=command.user_id,
        permission_code="fair_crm.operations.update",
        access_token=command.access_token,
    )
    repository.update_capabilities.assert_called_once_with(
        command.key,
        command.capabilities,
        is_active=True,
    )
    assert result.key == "reminder"
    assert result.supports_pause is True
    assert result.supports_retry is True
    assert result.is_active is True
