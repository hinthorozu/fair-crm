from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.customers.application.commands import CustomerResult, UpdateCustomerCommand
from app.modules.customers.application.mappers import customer_to_result
from app.modules.customers.domain.exceptions import CustomerNotFoundError
from app.modules.customers.domain.ports import CustomerRepository

PERMISSION_UPDATE = "fair_crm.customers.update"


class UpdateCustomerUseCase:
    def __init__(
        self,
        repository: CustomerRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: UpdateCustomerCommand) -> CustomerResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_UPDATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        customer = self._repository.get_by_id(command.organization_id, command.customer_id)
        if customer is None:
            raise CustomerNotFoundError("Customer not found")

        now = datetime.now(tz=UTC)
        customer.update_fields(
            display_name=command.display_name,
            legal_name=command.legal_name,
            trade_name=command.trade_name,
            customer_type=command.customer_type,
            status=command.status,
            website=command.website,
            phone=command.phone,
            email=command.email,
            tax_number=command.tax_number,
            tax_office=command.tax_office,
            country=command.country,
            city=command.city,
            district=command.district,
            address=command.address,
            description=command.description,
            source=command.source,
            now=now,
        )

        saved = self._repository.update(customer)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.customer.updated",
            resource_type="customer",
            resource_id=str(saved.id),
            new_values={"display_name": saved.display_name, "status": saved.status.value},
            metadata={"user_id": str(command.user_id)},
        )

        return customer_to_result(saved)
