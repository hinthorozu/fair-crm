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
        tax_number=model.tax_number,
        tax_office=model.tax_office,
        country=model.country,
        city=model.city,
        district=model.district,
        address=model.address,
        description=model.description,
        instagram_url=model.instagram_url,
        facebook_url=model.facebook_url,
        linkedin_url=model.linkedin_url,
        youtube_url=model.youtube_url,
        source=CustomerSource(model.source),
        email_allowed=model.email_allowed,
        sms_allowed=model.sms_allowed,
        email_unsubscribed_at=model.email_unsubscribed_at,
        sms_unsubscribed_at=model.sms_unsubscribed_at,
        consent_note=model.consent_note,
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
        tax_number=customer.tax_number,
        tax_office=customer.tax_office,
        country=customer.country,
        city=customer.city,
        district=customer.district,
        address=customer.address,
        description=customer.description,
        instagram_url=customer.instagram_url,
        facebook_url=customer.facebook_url,
        linkedin_url=customer.linkedin_url,
        youtube_url=customer.youtube_url,
        source=customer.source.value,
        email_allowed=customer.email_allowed,
        sms_allowed=customer.sms_allowed,
        email_unsubscribed_at=customer.email_unsubscribed_at,
        sms_unsubscribed_at=customer.sms_unsubscribed_at,
        consent_note=customer.consent_note,
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
    model.tax_number = customer.tax_number
    model.tax_office = customer.tax_office
    model.country = customer.country
    model.city = customer.city
    model.district = customer.district
    model.address = customer.address
    model.description = customer.description
    model.instagram_url = customer.instagram_url
    model.facebook_url = customer.facebook_url
    model.linkedin_url = customer.linkedin_url
    model.youtube_url = customer.youtube_url
    model.source = customer.source.value
    model.email_allowed = customer.email_allowed
    model.sms_allowed = customer.sms_allowed
    model.email_unsubscribed_at = customer.email_unsubscribed_at
    model.sms_unsubscribed_at = customer.sms_unsubscribed_at
    model.consent_note = customer.consent_note
    model.updated_at = customer.updated_at
    model.deleted_at = customer.deleted_at
    model.archived_from_status = (
        customer.archived_from_status.value if customer.archived_from_status else None
    )
