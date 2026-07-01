from app.modules.customers.application.commands import CustomerListResultDto, CustomerResult
from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.ports import CustomerListResult


def customer_to_result(
    customer: Customer,
    *,
    possible_duplicates: list | None = None,
) -> CustomerResult:
    return CustomerResult(
        id=customer.id,
        organization_id=customer.organization_id,
        display_name=customer.display_name,
        legal_name=customer.legal_name,
        trade_name=customer.trade_name,
        normalized_name=customer.normalized_name,
        customer_type=customer.customer_type,
        status=customer.status,
        website=customer.website,
        phone=customer.phone,
        email=customer.email,
        tax_number=customer.tax_number,
        tax_office=customer.tax_office,
        country=customer.country,
        city=customer.city,
        district=customer.district,
        address=customer.address,
        description=customer.description,
        source=customer.source,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
        deleted_at=customer.deleted_at,
        possible_duplicates=possible_duplicates,
    )


def list_result_to_dto(result: CustomerListResult) -> CustomerListResultDto:
    return CustomerListResultDto(
        items=[customer_to_result(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )
