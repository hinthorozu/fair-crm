from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class RecipientOptions:
    include_customer_emails: bool = True
    include_contact_emails: bool = True
    skip_no_email: bool = True
    exclude_inactive: bool = True
    dedupe_emails: bool = True


@dataclass(frozen=True)
class RawRecipientCandidate:
    recipient_name: str | None
    company_name: str
    email: str
    source: str
    customer_id: UUID
    contact_id: UUID | None
    participation_id: UUID
    is_active: bool
    email_valid: bool
    customer_email_allowed: bool = True
    contact_email_allowed: bool = True


@dataclass(frozen=True)
class ResolvedRecipient:
    recipient_key: str
    recipient_name: str | None
    company_name: str
    email: str
    source: str
    customer_id: UUID
    contact_id: UUID | None
    participation_id: UUID
    status: str
    skip_reason: str | None


@dataclass(frozen=True)
class RecipientPreviewResult:
    total_customers: int
    total_contacts: int
    valid_email_count: int
    deduped_recipient_count: int
    skipped_count: int
    recipients: list[ResolvedRecipient]
