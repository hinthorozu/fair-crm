from uuid import UUID

from app.modules.customers.application.commands import (
    CustomerEmailResult,
    CustomerListResultDto,
    CustomerPhoneResult,
    CustomerResult,
    CustomerWebsiteResult,
)
from app.modules.customers.application.communication_parsing import api_scalar_fields_from_communications
from app.modules.customers.domain.communication_entities import (
    CustomerCommunicationListSummary,
    CustomerCommunications,
)
from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.ports import CustomerListResult


def _communications_to_result(
    communications: CustomerCommunications | None,
) -> tuple[
    list[CustomerPhoneResult] | None,
    list[CustomerEmailResult] | None,
    list[CustomerWebsiteResult] | None,
]:
    if communications is None:
        return None, None, None
    return (
        [
            CustomerPhoneResult(
                id=item.id,
                phone=item.phone,
                is_primary=item.is_primary,
                created_at=item.created_at,
            )
            for item in communications.phones
        ],
        [
            CustomerEmailResult(
                id=item.id,
                email=item.email,
                is_primary=item.is_primary,
                created_at=item.created_at,
            )
            for item in communications.emails
        ],
        [
            CustomerWebsiteResult(
                id=item.id,
                website=item.website,
                is_primary=item.is_primary,
                created_at=item.created_at,
            )
            for item in communications.websites
        ],
    )


def customer_to_result(
    customer: Customer,
    *,
    possible_duplicates: list | None = None,
    communications: CustomerCommunications | None = None,
) -> CustomerResult:
    phones, emails, websites = _communications_to_result(communications)
    phone, email, website, phone_extra, email_extra, website_extra = api_scalar_fields_from_communications(
        communications
    )
    return CustomerResult(
        id=customer.id,
        organization_id=customer.organization_id,
        display_name=customer.display_name,
        legal_name=customer.legal_name,
        trade_name=customer.trade_name,
        normalized_name=customer.normalized_name,
        customer_type=customer.customer_type,
        status=customer.status,
        website=website,
        phone=phone,
        email=email,
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
        source=customer.source,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
        deleted_at=customer.deleted_at,
        possible_duplicates=possible_duplicates,
        phones=phones or [],
        emails=emails or [],
        websites=websites or [],
        phone_extra_count=phone_extra,
        email_extra_count=email_extra,
        website_extra_count=website_extra,
    )


def customer_to_list_result(
    customer: Customer,
    *,
    summary: CustomerCommunicationListSummary | None = None,
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
        website=summary.website if summary else None,
        phone=summary.phone if summary else None,
        email=summary.email if summary else None,
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
        source=customer.source,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
        deleted_at=customer.deleted_at,
        possible_duplicates=None,
        phones=[],
        emails=[],
        websites=[],
        phone_extra_count=summary.phone_extra_count if summary else 0,
        email_extra_count=summary.email_extra_count if summary else 0,
        website_extra_count=summary.website_extra_count if summary else 0,
    )


def list_result_to_dto(
    result: CustomerListResult,
    *,
    communication_summaries: dict[UUID, CustomerCommunicationListSummary] | None = None,
) -> CustomerListResultDto:
    summaries = communication_summaries or {}
    return CustomerListResultDto(
        items=[
            customer_to_list_result(
                item,
                summary=summaries.get(item.id),
            )
            for item in result.items
        ],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )


def customer_results_with_communications(
    customers: list[Customer],
    communications_by_customer: dict[UUID, CustomerCommunications],
    *,
    possible_duplicates_by_customer: dict[UUID, list] | None = None,
) -> list[CustomerResult]:
    duplicates = possible_duplicates_by_customer or {}
    return [
        customer_to_result(
            customer,
            communications=communications_by_customer.get(customer.id),
            possible_duplicates=duplicates.get(customer.id),
        )
        for customer in customers
    ]
