from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.customers.application.commands import CreateCustomerCommand, CustomerResult
from app.modules.customers.application.mappers import customer_to_result
from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.ports import CustomerRepository

PERMISSION_CREATE = "fair_crm.customers.create"


class CreateCustomerUseCase:
    def __init__(
        self,
        repository: CustomerRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: CreateCustomerCommand) -> CustomerResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_CREATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        now = datetime.now(tz=UTC)
        customer = Customer.create(
            organization_id=command.organization_id,
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

        saved = self._repository.add(customer)
        duplicates = self._repository.find_by_normalized_name(
            command.organization_id,
            saved.normalized_name,
            exclude_id=saved.id,
        )

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.customer.created",
            resource_type="customer",
            resource_id=str(saved.id),
            new_values={"display_name": saved.display_name, "status": saved.status.value},
            metadata={"user_id": str(command.user_id)},
        )

        duplicate_ids = [item.id for item in duplicates] if duplicates else None
        return customer_to_result(saved, possible_duplicates=duplicate_ids)
