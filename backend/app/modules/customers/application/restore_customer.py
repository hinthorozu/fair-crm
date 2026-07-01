from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.customers.application.commands import CustomerResult, RestoreCustomerCommand
from app.modules.customers.application.mappers import customer_to_result
from app.modules.customers.domain.exceptions import CustomerNotArchivedError, CustomerNotFoundError
from app.modules.customers.domain.ports import CustomerRepository

PERMISSION_RESTORE = "fair_crm.customers.archive"


class RestoreCustomerUseCase:
    def __init__(
        self,
        repository: CustomerRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: RestoreCustomerCommand) -> CustomerResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_RESTORE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        customer = self._repository.get_by_id_including_archived(
            command.organization_id, command.customer_id
        )
        if customer is None:
            raise CustomerNotFoundError("Customer not found")

        now = datetime.now(tz=UTC)
        try:
            customer.restore(now=now)
        except CustomerNotArchivedError:
            raise

        saved = self._repository.update(customer)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.customer.restored",
            resource_type="customer",
            resource_id=str(saved.id),
            metadata={"user_id": str(command.user_id)},
        )

        return customer_to_result(saved)
