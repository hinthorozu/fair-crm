from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.core.exceptions import ForbiddenError
from app.modules.email_accounts.application.manage_email_accounts import (
    SendTestEmailAccountMailUseCase,
)
from app.modules.smtp.application.commands import SendTestSmtpMailCommand
from app.modules.smtp.application.send_test_smtp_mail import SendTestSmtpMailUseCase

PERMISSION_EXECUTE = "fair_crm.mail_send_operations.execute"


def test_provider_test_mail_requires_mail_send_execute_before_resource_lookup() -> None:
    organization_id = uuid4()
    user_id = uuid4()
    account_id = uuid4()
    repository = Mock()
    authorization = Mock()
    authorization.check_permission.return_value = False

    use_case = SendTestEmailAccountMailUseCase(
        repository=repository,
        authorization=authorization,
        audit=Mock(),
        mail_send_operations=Mock(),
        session=Mock(),
    )

    with pytest.raises(ForbiddenError):
        use_case.execute(
            organization_id=organization_id,
            account_id=account_id,
            access_token="token",
            user_id=user_id,
            recipient="recipient@example.com",
        )

    authorization.check_permission.assert_called_once_with(
        organization_id=organization_id,
        user_id=user_id,
        permission_code=PERMISSION_EXECUTE,
        access_token="token",
    )
    repository.get_by_id.assert_not_called()


def test_smtp_test_mail_requires_mail_send_execute_before_resource_lookup() -> None:
    organization_id = uuid4()
    user_id = uuid4()
    account_id = uuid4()
    repository = Mock()
    authorization = Mock()
    authorization.check_permission.return_value = False

    use_case = SendTestSmtpMailUseCase(
        repository=repository,
        authorization=authorization,
        audit=Mock(),
        mail_send_operations=Mock(),
        session=Mock(),
    )

    with pytest.raises(ForbiddenError):
        use_case.execute(
            SendTestSmtpMailCommand(
                organization_id=organization_id,
                account_id=account_id,
                access_token="token",
                user_id=user_id,
                recipient="recipient@example.com",
            )
        )

    authorization.check_permission.assert_called_once_with(
        organization_id=organization_id,
        user_id=user_id,
        permission_code=PERMISSION_EXECUTE,
        access_token="token",
    )
    repository.get_by_id.assert_not_called()
