from unittest.mock import MagicMock
from uuid import uuid4

import httpx

from app.integrations.kyrox_core.client import HttpAuditAdapter, KyroxCoreHttpClient
from app.modules.customers.application.commands import CreateCustomerCommand
from app.modules.customers.application.create_customer import CreateCustomerUseCase
from app.modules.customers.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)
from tests.conftest import AllowAllAuthorization


def test_http_audit_adapter_does_not_raise_on_http_error():
    http = MagicMock(spec=KyroxCoreHttpClient)
    http.request.return_value = httpx.Response(503, json={"detail": "unavailable"})

    adapter = HttpAuditAdapter(http_client=http)
    adapter.record_event(
        organization_id=uuid4(),
        access_token="token",
        action="fair_crm.customer.created",
        resource_type="customer",
        resource_id="abc",
    )


def test_http_audit_adapter_does_not_raise_on_network_error():
    http = MagicMock(spec=KyroxCoreHttpClient)
    http.request.side_effect = httpx.ConnectError("connection refused")

    adapter = HttpAuditAdapter(http_client=http)
    adapter.record_event(
        organization_id=uuid4(),
        access_token="token",
        action="fair_crm.customer.created",
        resource_type="customer",
        resource_id="abc",
    )


def test_create_customer_succeeds_when_audit_adapter_fails(db_session, organization_id):
    http = MagicMock(spec=KyroxCoreHttpClient)
    http.request.side_effect = httpx.ConnectError("connection refused")
    audit = HttpAuditAdapter(http_client=http)

    repo = SqlAlchemyCustomerRepository(db_session)
    use_case = CreateCustomerUseCase(repo, AllowAllAuthorization(), audit)

    result = use_case.execute(
        CreateCustomerCommand(
            organization_id=organization_id,
            access_token="token",
            user_id=uuid4(),
            display_name="Audit Resilience Co",
        )
    )

    assert result.display_name == "Audit Resilience Co"
    assert repo.get_by_id(organization_id, result.id) is not None
