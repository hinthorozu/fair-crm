"""Authorization regression tests for admin data-operation exports/downloads."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import ForbiddenError
from app.modules.system_admin.application.data_operation_service import (
    DownloadDataOperationFileUseCase,
    ExportDataOperationDatasetCustomersUseCase,
    ExportDataOperationDuplicateCustomersUseCase,
)


def _assert_execute_permission(authorization, *, organization_id, user_id):
    authorization.check_permission.assert_called_once_with(
        organization_id=organization_id,
        user_id=user_id,
        permission_code="fair_crm.admin.data_operations.execute",
        access_token="token",
    )


def test_dataset_customer_export_requires_execute_permission():
    organization_id = uuid4()
    user_id = uuid4()
    run_repository = MagicMock()
    dataset_repository = MagicMock()
    authorization = MagicMock()
    authorization.check_permission.return_value = False
    use_case = ExportDataOperationDatasetCustomersUseCase(
        run_repository, dataset_repository, authorization
    )

    with pytest.raises(ForbiddenError):
        use_case.execute(
            organization_id=organization_id,
            user_id=user_id,
            access_token="token",
            run_id=uuid4(),
        )

    _assert_execute_permission(
        authorization, organization_id=organization_id, user_id=user_id
    )
    run_repository.get_by_id.assert_not_called()
    dataset_repository.list_all_customers.assert_not_called()


def test_duplicate_customer_export_requires_execute_permission():
    organization_id = uuid4()
    user_id = uuid4()
    run_repository = MagicMock()
    dataset_repository = MagicMock()
    authorization = MagicMock()
    authorization.check_permission.return_value = False
    use_case = ExportDataOperationDuplicateCustomersUseCase(
        run_repository, dataset_repository, authorization
    )

    with pytest.raises(ForbiddenError):
        use_case.execute(
            organization_id=organization_id,
            user_id=user_id,
            access_token="token",
            run_id=uuid4(),
        )

    _assert_execute_permission(
        authorization, organization_id=organization_id, user_id=user_id
    )
    run_repository.get_by_id.assert_not_called()
    dataset_repository.list_all_duplicate_customers.assert_not_called()


def test_output_file_download_requires_execute_permission():
    organization_id = uuid4()
    user_id = uuid4()
    repository = MagicMock()
    authorization = MagicMock()
    authorization.check_permission.return_value = False
    use_case = DownloadDataOperationFileUseCase(repository, authorization)

    with pytest.raises(ForbiddenError):
        use_case.execute(
            organization_id=organization_id,
            user_id=user_id,
            access_token="token",
            run_id=uuid4(),
            file_id=uuid4(),
        )

    _assert_execute_permission(
        authorization, organization_id=organization_id, user_id=user_id
    )
    repository.get_by_id.assert_not_called()
