from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.customers.application.commands import CreateCustomerCommand
from app.modules.customers.application.create_customer import CreateCustomerUseCase
from app.modules.customers.domain.entities import Customer
from app.modules.customers.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)
from tests.conftest import AllowAllAuthorization, NoOpAudit


def test_create_customer_use_case(db_session, organization_id):
    repo = SqlAlchemyCustomerRepository(db_session)
    use_case = CreateCustomerUseCase(repo, AllowAllAuthorization(), NoOpAudit())

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
    use_case = CreateCustomerUseCase(repo, DenyAllAuthorization(), NoOpAudit())

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
