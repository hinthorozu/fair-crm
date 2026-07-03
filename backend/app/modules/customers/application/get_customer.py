from app.modules.customers.application.commands import CustomerResult, GetCustomerQuery
from app.modules.customers.application.customer_communication_sync import CustomerCommunicationSyncService
from app.modules.customers.application.mappers import customer_to_result
from app.modules.customers.domain.exceptions import CustomerNotFoundError
from app.modules.customers.domain.ports import CustomerRepository


class GetCustomerUseCase:
    def __init__(
        self,
        repository: CustomerRepository,
        communication_sync: CustomerCommunicationSyncService,
    ) -> None:
        self._repository = repository
        self._communication_sync = communication_sync

    def execute(self, query: GetCustomerQuery) -> CustomerResult:
        customer = self._repository.get_by_id(query.organization_id, query.customer_id)
        if customer is None:
            raise CustomerNotFoundError("Customer not found")
        communications = self._communication_sync.load_for_customer(customer.id)
        return customer_to_result(customer, communications=communications)
