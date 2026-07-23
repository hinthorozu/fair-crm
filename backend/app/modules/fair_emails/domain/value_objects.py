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
    fair_id: UUID | None = None
    fair_name: str | None = None


@dataclass(frozen=True)
class ResolvedRecipient:
    recipient_key: str
    recipient_name: str | None
    company_name: str
    email: str
    source: str
    customer_id: UUID | None
    contact_id: UUID | None
    participation_id: UUID | None
    status: str
    skip_reason: str | None
    fair_id: UUID | None = None
    fair_name: str | None = None


@dataclass(frozen=True)
class RecipientPreviewResult:
    total_customers: int
    total_contacts: int
    valid_email_count: int
    deduped_recipient_count: int
    skipped_count: int
    recipients: list[ResolvedRecipient]


@dataclass(frozen=True)
class ManualRecipientPreviewResult:
    total_found: int
    valid_email_count: int
    duplicate_count: int
    invalid_count: int
    deduped_recipient_count: int
    skipped_count: int
    recipients: list["WizardPreviewRecipient"]


@dataclass(frozen=True)
class WizardPreviewRecipient:
    """Preview row for operations bulk-email wizard (manual or fair)."""

    recipient_key: str
    email: str
    source: str
    status: str
    skip_reason: str | None
    recipient_name: str | None = None
    company_name: str | None = None
    fair_id: UUID | None = None
    fair_name: str | None = None
    customer_id: UUID | None = None
    contact_id: UUID | None = None
    participation_id: UUID | None = None
