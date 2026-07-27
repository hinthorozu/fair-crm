"""Import/scraper create path uses Customer.create defaults for type and status."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

from app.modules.customers.domain.value_objects import CustomerSource, CustomerStatus, CustomerType
from app.modules.imports.application.apply_import import ApplyImportUseCase
from app.modules.imports.application.commands import ApplyImportCommand


def test_import_apply_create_customer_defaults_exhibitor_active():
    created = []

    def add(customer):
        created.append(customer)
        return customer

    customer_repo = MagicMock()
    customer_repo.add.side_effect = add
    communication_sync = MagicMock()

    use_case = ApplyImportUseCase(
        MagicMock(),
        MagicMock(),
        customer_repo,
        communication_sync,
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )
    command = ApplyImportCommand(
        organization_id=uuid4(),
        user_id=uuid4(),
        access_token="token",
        batch_id=uuid4(),
    )
    now = datetime.now(tz=UTC)

    customer = use_case._create_customer(
        {"company_name": "Import New Co", "country": "Türkiye"},
        command,
        now,
    )

    assert customer.customer_type == CustomerType.EXHIBITOR
    assert customer.status == CustomerStatus.ACTIVE
    assert customer.source == CustomerSource.EXCEL
    customer_repo.add.assert_called_once()
    communication_sync.sync_from_value_lists.assert_called_once()
