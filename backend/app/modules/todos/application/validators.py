from uuid import UUID

from app.modules.customers.domain.ports import CustomerRepository
from app.modules.fairs.domain.exceptions import FairNotFoundError
from app.modules.fairs.domain.ports import FairRepository
from app.modules.todos.domain.exceptions import InvalidTodoCustomerError


def ensure_source_fair_exists(
    fair_repository: FairRepository,
    organization_id: UUID,
    source_fair_id: UUID,
) -> None:
    fair = fair_repository.get_by_id(organization_id, source_fair_id)
    if fair is None:
        raise FairNotFoundError("Fair not found")


def ensure_customer_exists(
    customer_repository: CustomerRepository,
    organization_id: UUID,
    customer_id: UUID,
) -> None:
    customer = customer_repository.get_by_id(organization_id, customer_id)
    if customer is None:
        raise InvalidTodoCustomerError("Customer not found")
