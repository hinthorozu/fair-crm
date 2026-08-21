"""Unit tests for import apply job authorization."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import ForbiddenError
from app.modules.data_integration.application.start_import_apply_job import (
    StartImportApplyJobCommand,
    StartImportApplyJobUseCase,
)


def test_start_import_apply_job_requires_execute_permission():
    organization_id = uuid4()
    user_id = uuid4()
    batch_id = uuid4()

    batch_repository = MagicMock()
    row_repository = MagicMock()
    job_repository = MagicMock()
    authorization = MagicMock()
    authorization.check_permission.return_value = False

    use_case = StartImportApplyJobUseCase(
        batch_repository,
        row_repository,
        job_repository,
        authorization,
    )

    with pytest.raises(ForbiddenError):
        use_case.execute(
            StartImportApplyJobCommand(
                organization_id=organization_id,
                user_id=user_id,
                access_token="token",
                batch_id=batch_id,
            )
        )

    authorization.check_permission.assert_called_once_with(
        organization_id=organization_id,
        user_id=user_id,
        permission_code="fair_crm.imports.execute",
        access_token="token",
    )
    batch_repository.get_by_id.assert_not_called()
