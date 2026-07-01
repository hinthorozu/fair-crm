from app.modules.customers.application.commands import CustomerResult, GetCustomerQuery
from app.modules.customers.application.mappers import customer_to_result
from app.modules.customers.domain.exceptions import CustomerNotFoundError
from app.modules.customers.domain.ports import CustomerRepository


class GetCustomerUseCase:
    def __init__(self, repository: CustomerRepository) -> None:
        self._repository = repository

    def execute(self, query: GetCustomerQuery) -> CustomerResult:
        customer = self._repository.get_by_id(query.organization_id, query.customer_id)
        if customer is None:
            raise CustomerNotFoundError("Customer not found")
        return customer_to_result(customer)
