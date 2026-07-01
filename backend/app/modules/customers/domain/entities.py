from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from app.modules.customers.domain.exceptions import (
    CustomerAlreadyArchivedError,
    CustomerNotArchivedError,
    InvalidCustomerEmailError,
    InvalidCustomerNameError,
)
from app.modules.customers.domain.services.normalizers import (
    compute_normalized_name,
    normalize_email_list,
    normalize_phone,
    normalize_website,
)
from app.modules.customers.domain.value_objects import CustomerSource, CustomerStatus, CustomerType


def _normalize_and_validate_email(email: Optional[str]) -> Optional[str]:
    if email is None:
        return None
    try:
        return normalize_email_list(email)
    except ValueError as exc:
        raise InvalidCustomerEmailError(str(exc)) from exc


@dataclass
class Customer:
    id: UUID
    organization_id: UUID
    display_name: str
    legal_name: Optional[str]
    trade_name: Optional[str]
    normalized_name: str
    customer_type: CustomerType
    status: CustomerStatus
    website: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    tax_number: Optional[str]
    tax_office: Optional[str]
    country: Optional[str]
    city: Optional[str]
    district: Optional[str]
    address: Optional[str]
    description: Optional[str]
    source: CustomerSource
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]
    archived_from_status: Optional[CustomerStatus] = None

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        display_name: str,
        legal_name: Optional[str] = None,
        trade_name: Optional[str] = None,
        customer_type: CustomerType = CustomerType.LEAD,
        status: CustomerStatus = CustomerStatus.LEAD,
        website: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        tax_number: Optional[str] = None,
        tax_office: Optional[str] = None,
        country: Optional[str] = None,
        city: Optional[str] = None,
        district: Optional[str] = None,
        address: Optional[str] = None,
        description: Optional[str] = None,
        source: CustomerSource = CustomerSource.MANUAL,
        now: datetime,
    ) -> "Customer":
        trimmed_display = display_name.strip()
        if not trimmed_display:
            raise InvalidCustomerNameError("display_name must not be empty")

        normalized_email = _normalize_and_validate_email(email)

        return cls(
            id=uuid4(),
            organization_id=organization_id,
            display_name=trimmed_display,
            legal_name=legal_name.strip() if legal_name else None,
            trade_name=trade_name.strip() if trade_name else None,
            normalized_name=compute_normalized_name(
                display_name=trimmed_display,
                legal_name=legal_name,
            ),
            customer_type=customer_type,
            status=status,
            website=normalize_website(website) if website else None,
            phone=normalize_phone(phone) if phone else None,
            email=normalized_email,
            tax_number=tax_number.strip() if tax_number else None,
            tax_office=tax_office.strip() if tax_office else None,
            country=country.strip() if country else None,
            city=city.strip() if city else None,
            district=district.strip() if district else None,
            address=address.strip() if address else None,
            description=description.strip() if description else None,
            source=source,
            created_at=now,
            updated_at=now,
            deleted_at=None,
            archived_from_status=None,
        )

    def ensure_mutable(self) -> None:
        if self.status == CustomerStatus.ARCHIVED or self.deleted_at is not None:
            raise CustomerAlreadyArchivedError("Customer is archived")

    def update_fields(
        self,
        *,
        display_name: Optional[str] = None,
        legal_name: Optional[str] = None,
        trade_name: Optional[str] = None,
        customer_type: Optional[CustomerType] = None,
        status: Optional[CustomerStatus] = None,
        website: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        tax_number: Optional[str] = None,
        tax_office: Optional[str] = None,
        country: Optional[str] = None,
        city: Optional[str] = None,
        district: Optional[str] = None,
        address: Optional[str] = None,
        description: Optional[str] = None,
        source: Optional[CustomerSource] = None,
        now: datetime,
    ) -> None:
        self.ensure_mutable()

        if display_name is not None:
            trimmed = display_name.strip()
            if not trimmed:
                raise InvalidCustomerNameError("display_name must not be empty")
            self.display_name = trimmed

        if legal_name is not None:
            self.legal_name = legal_name.strip() if legal_name else None
        if trade_name is not None:
            self.trade_name = trade_name.strip() if trade_name else None

        if display_name is not None or legal_name is not None:
            self.normalized_name = compute_normalized_name(
                display_name=self.display_name,
                legal_name=self.legal_name,
            )

        if customer_type is not None:
            self.customer_type = customer_type
        if status is not None and status != CustomerStatus.ARCHIVED:
            self.status = status

        if website is not None:
            self.website = normalize_website(website) if website else None
        if phone is not None:
            self.phone = normalize_phone(phone) if phone else None
        if email is not None:
            self.email = _normalize_and_validate_email(email if email else None)

        if tax_number is not None:
            self.tax_number = tax_number.strip() if tax_number else None
        if tax_office is not None:
            self.tax_office = tax_office.strip() if tax_office else None
        if country is not None:
            self.country = country.strip() if country else None
        if city is not None:
            self.city = city.strip() if city else None
        if district is not None:
            self.district = district.strip() if district else None
        if address is not None:
            self.address = address.strip() if address else None
        if description is not None:
            self.description = description.strip() if description else None
        if source is not None:
            self.source = source

        self.updated_at = now

    def is_archived(self) -> bool:
        return self.deleted_at is not None or self.status == CustomerStatus.ARCHIVED

    def archive(self, *, now: datetime) -> None:
        if self.status == CustomerStatus.ARCHIVED and self.deleted_at is not None:
            return
        if self.status != CustomerStatus.ARCHIVED:
            self.archived_from_status = self.status
        self.status = CustomerStatus.ARCHIVED
        self.deleted_at = now
        self.updated_at = now

    def restore(self, *, now: datetime) -> None:
        if not self.is_archived():
            raise CustomerNotArchivedError("Customer is not archived")

        restore_status = self.archived_from_status
        if restore_status is None or restore_status == CustomerStatus.ARCHIVED:
            restore_status = CustomerStatus.ACTIVE

        self.status = restore_status
        self.deleted_at = None
        self.archived_from_status = None
        self.updated_at = now
