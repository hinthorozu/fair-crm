from __future__ import annotations

from uuid import UUID

from app.shared.email import is_valid_email_address

from app.modules.fair_emails.domain.value_objects import (
    ManualRecipientPreviewResult,
    RawRecipientCandidate,
    RecipientOptions,
    RecipientPreviewResult,
    ResolvedRecipient,
    WizardPreviewRecipient,
)
from app.shared.consent import CONTACT_EMAIL_CONSENT_SKIP, CUSTOMER_EMAIL_CONSENT_SKIP


def recipient_key(customer_id: UUID | None, contact_id: UUID | None, email: str) -> str:
    customer_part = str(customer_id) if customer_id else "none"
    contact_part = str(contact_id) if contact_id else "none"
    return f"{customer_part}:{contact_part}:{email.lower()}"


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
                fair_id=candidate.fair_id,
                fair_name=candidate.fair_name,
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


def tokenize_email_field(value: str | None) -> list[str]:
    """Split a free-text email field into non-empty raw tokens (no validation)."""
    if not value:
        return []
    tokens: list[str] = []
    for part in value.replace(",", ";").split(";"):
        token = part.strip()
        if token:
            tokens.append(token)
    return tokens


def resolve_manual_and_excel_emails(
    *,
    manual_emails_text: str | None,
    excel_email_tokens: list[str],
) -> ManualRecipientPreviewResult:
    """Merge manual + Excel email tokens, validate, and dedupe (manual first)."""
    entries: list[tuple[str, str]] = []
    for token in tokenize_email_field(manual_emails_text):
        entries.append((token, "manual"))
    for token in excel_email_tokens:
        cleaned = token.strip()
        if cleaned:
            entries.append((cleaned, "excel"))

    resolved: list[WizardPreviewRecipient] = []
    seen_emails: set[str] = set()
    valid_email_count = 0
    duplicate_count = 0
    invalid_count = 0

    for raw, source in entries:
        email_lower = raw.lower()
        status = "will_send"
        skip_reason: str | None = None
        email_for_row = raw

        if not is_valid_email_address(raw):
            status = "skip"
            skip_reason = "invalid_email"
            invalid_count += 1
        elif email_lower in seen_emails:
            status = "skip"
            skip_reason = "duplicate_email"
            duplicate_count += 1
            email_for_row = email_lower
        else:
            email_for_row = email_lower
            seen_emails.add(email_lower)
            valid_email_count += 1

        resolved.append(
            WizardPreviewRecipient(
                recipient_key=f"{source}:none:{email_for_row.lower()}",
                email=email_for_row,
                source=source,
                status=status,
                skip_reason=skip_reason,
            )
        )

    will_send = [item for item in resolved if item.status == "will_send"]
    return ManualRecipientPreviewResult(
        total_found=len(entries),
        valid_email_count=valid_email_count,
        duplicate_count=duplicate_count,
        invalid_count=invalid_count,
        deduped_recipient_count=len(will_send),
        skipped_count=len(resolved) - len(will_send),
        recipients=resolved,
    )


def resolved_to_wizard_recipient(item: ResolvedRecipient) -> WizardPreviewRecipient:
    return WizardPreviewRecipient(
        recipient_key=item.recipient_key,
        email=item.email,
        source=item.source,
        status=item.status,
        skip_reason=item.skip_reason,
        recipient_name=item.recipient_name,
        company_name=item.company_name,
        fair_id=item.fair_id,
        fair_name=item.fair_name,
        customer_id=item.customer_id,
        contact_id=item.contact_id,
        participation_id=item.participation_id,
    )


def wizard_to_resolved_recipient(item: WizardPreviewRecipient) -> ResolvedRecipient:
    """Map wizard preview rows (incl. manual/excel) into outbox-ready recipients."""
    company_name = (item.company_name or "").strip() or item.email
    return ResolvedRecipient(
        recipient_key=item.recipient_key,
        recipient_name=item.recipient_name,
        company_name=company_name,
        email=item.email,
        source=item.source,
        customer_id=item.customer_id,
        contact_id=item.contact_id,
        participation_id=item.participation_id,
        status=item.status,
        skip_reason=item.skip_reason,
        fair_id=item.fair_id,
        fair_name=item.fair_name,
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
