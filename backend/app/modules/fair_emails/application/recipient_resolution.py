from __future__ import annotations

from uuid import UUID

from app.shared.email import is_valid_email_address

from app.modules.fair_emails.domain.value_objects import (
    RawRecipientCandidate,
    RecipientOptions,
    RecipientPreviewResult,
    ResolvedRecipient,
)
from app.shared.consent import CONTACT_EMAIL_CONSENT_SKIP, CUSTOMER_EMAIL_CONSENT_SKIP


def recipient_key(customer_id: UUID, contact_id: UUID | None, email: str) -> str:
    contact_part = str(contact_id) if contact_id else "none"
    return f"{customer_id}:{contact_part}:{email.lower()}"


def resolve_recipients(
    candidates: list[RawRecipientCandidate],
    options: RecipientOptions,
) -> RecipientPreviewResult:
    customer_ids: set[UUID] = set()
    contact_ids: set[UUID] = set()
    valid_email_count = 0
    resolved: list[ResolvedRecipient] = []
    seen_emails: set[str] = set()

    for candidate in candidates:
        if candidate.source == "customer":
            customer_ids.add(candidate.customer_id)
        if candidate.source == "contact" and candidate.contact_id is not None:
            contact_ids.add(candidate.contact_id)

        status = "will_send"
        skip_reason: str | None = None

        if options.exclude_inactive and not candidate.is_active:
            status = "skip"
            skip_reason = "inactive_record"
        elif not candidate.customer_email_allowed:
            status = "skip"
            skip_reason = CUSTOMER_EMAIL_CONSENT_SKIP
        elif candidate.source == "contact" and not candidate.contact_email_allowed:
            status = "skip"
            skip_reason = CONTACT_EMAIL_CONSENT_SKIP
        elif not candidate.email:
            if options.skip_no_email:
                status = "skip"
                skip_reason = "no_email"
        elif not candidate.email_valid:
            status = "skip"
            skip_reason = "invalid_email"
        elif options.dedupe_emails and candidate.email.lower() in seen_emails:
            status = "skip"
            skip_reason = "duplicate_email"
        else:
            valid_email_count += 1
            if options.dedupe_emails:
                seen_emails.add(candidate.email.lower())

        resolved.append(
            ResolvedRecipient(
                recipient_key=recipient_key(candidate.customer_id, candidate.contact_id, candidate.email),
                recipient_name=candidate.recipient_name,
                company_name=candidate.company_name,
                email=candidate.email,
                source=candidate.source,
                customer_id=candidate.customer_id,
                contact_id=candidate.contact_id,
                participation_id=candidate.participation_id,
                status=status,
                skip_reason=skip_reason,
            )
        )

    will_send = [item for item in resolved if item.status == "will_send"]
    skipped_count = len(resolved) - len(will_send)

    return RecipientPreviewResult(
        total_customers=len(customer_ids),
        total_contacts=len(contact_ids),
        valid_email_count=valid_email_count,
        deduped_recipient_count=len(will_send),
        skipped_count=skipped_count,
        recipients=resolved,
    )


def iter_valid_emails(value: str | None) -> list[str]:
    if not value:
        return []
    emails: list[str] = []
    seen: set[str] = set()
    for part in value.replace(",", ";").split(";"):
        email = part.strip().lower()
        if not email:
            continue
        if not is_valid_email_address(email):
            continue
        if email in seen:
            continue
        seen.add(email)
        emails.append(email)
    return emails


def build_render_variables(
    *,
    fair_name: str,
    customer_name: str,
    contact_first_name: str = "",
    contact_last_name: str = "",
    contact_title: str = "",
    hall: str = "",
    stand: str = "",
    sender_name: str = "KYROX",
) -> dict[str, str]:
    return {
        "fair_name": fair_name,
        "customer_name": customer_name,
        "contact_first_name": contact_first_name,
        "contact_last_name": contact_last_name,
        "contact_title": contact_title,
        "hall": hall,
        "stand": stand,
        "sender_name": sender_name,
    }
