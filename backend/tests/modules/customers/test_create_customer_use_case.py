from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.customers.application.commands import CreateCustomerCommand
from app.modules.customers.application.customer_communication_sync import CustomerCommunicationSyncService
from app.modules.customers.application.create_customer import CreateCustomerUseCase
from app.modules.customers.domain.entities import Customer
from app.modules.customers.infrastructure.repositories.customer_communication_repository import (
    SqlAlchemyCustomerCommunicationRepository,
)
from app.modules.customers.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)
from tests.conftest import AllowAllAuthorization, NoOpAudit


def _create_use_case(db_session) -> CreateCustomerUseCase:
    repo = SqlAlchemyCustomerRepository(db_session)
    communication_sync = CustomerCommunicationSyncService(
        SqlAlchemyCustomerCommunicationRepository(db_session)
    )
    return CreateCustomerUseCase(repo, communication_sync, AllowAllAuthorization(), NoOpAudit())


def test_create_customer_use_case(db_session, organization_id):
    use_case = _create_use_case(db_session)

    result = use_case.execute(
        CreateCustomerCommand(
            organization_id=organization_id,
            access_token="token",
            user_id=uuid4(),
            display_name="Delta Otomasyon Ltd. Şti.",
            legal_name="Delta Otomasyon Ltd. Şti.",
            city="Istanbul",
        )
    )

    assert result.display_name == "Delta Otomasyon Ltd. Şti."
    assert result.normalized_name == "DELTA OTOMASYON"
    assert result.city == "Istanbul"


def test_create_customer_forbidden(db_session, organization_id):
    from tests.conftest import DenyAllAuthorization

    repo = SqlAlchemyCustomerRepository(db_session)
    communication_sync = CustomerCommunicationSyncService(
        SqlAlchemyCustomerCommunicationRepository(db_session)
    )
    use_case = CreateCustomerUseCase(repo, communication_sync, DenyAllAuthorization(), NoOpAudit())

    from app.core.exceptions import ForbiddenError

    with pytest.raises(ForbiddenError):
        use_case.execute(
            CreateCustomerCommand(
                organization_id=organization_id,
                access_token="token",
                user_id=uuid4(),
                display_name="Acme",
            )
        )
