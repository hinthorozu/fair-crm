from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.value_objects import CustomerSource, CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.models import CustomerModel


def model_to_entity(model: CustomerModel) -> Customer:
    return Customer(
        id=model.id,
        organization_id=model.organization_id,
        display_name=model.display_name,
        legal_name=model.legal_name,
        trade_name=model.trade_name,
        normalized_name=model.normalized_name,
        customer_type=CustomerType(model.customer_type),
        status=CustomerStatus(model.status),
        website=model.website,
        phone=model.phone,
        email=model.email,
        tax_number=model.tax_number,
        tax_office=model.tax_office,
        country=model.country,
        city=model.city,
        district=model.district,
        address=model.address,
        description=model.description,
        source=CustomerSource(model.source),
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        archived_from_status=(
            CustomerStatus(model.archived_from_status) if model.archived_from_status else None
        ),
    )


def entity_to_model(customer: Customer) -> CustomerModel:
    return CustomerModel(
        id=customer.id,
        organization_id=customer.organization_id,
        display_name=customer.display_name,
        legal_name=customer.legal_name,
        trade_name=customer.trade_name,
        normalized_name=customer.normalized_name,
        customer_type=customer.customer_type.value,
        status=customer.status.value,
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
        source=customer.source.value,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
        deleted_at=customer.deleted_at,
        archived_from_status=(
            customer.archived_from_status.value if customer.archived_from_status else None
        ),
    )


def update_model_from_entity(model: CustomerModel, customer: Customer) -> None:
    model.display_name = customer.display_name
    model.legal_name = customer.legal_name
    model.trade_name = customer.trade_name
    model.normalized_name = customer.normalized_name
    model.customer_type = customer.customer_type.value
    model.status = customer.status.value
    model.website = customer.website
    model.phone = customer.phone
    model.email = customer.email
    model.tax_number = customer.tax_number
    model.tax_office = customer.tax_office
    model.country = customer.country
    model.city = customer.city
    model.district = customer.district
    model.address = customer.address
    model.description = customer.description
    model.source = customer.source.value
    model.updated_at = customer.updated_at
    model.deleted_at = customer.deleted_at
    model.archived_from_status = (
        customer.archived_from_status.value if customer.archived_from_status else None
    )
