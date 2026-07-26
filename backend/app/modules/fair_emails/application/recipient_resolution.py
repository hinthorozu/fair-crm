from __future__ import annotations

from uuid import UUID

from app.shared.consent import (
    CONTACT_EMAIL_CONSENT_SKIP,
    CUSTOMER_EMAIL_CONSENT_SKIP,
    evaluate_candidate_email_consent,
)
from app.shared.email import is_valid_email_address, normalize_bulk_recipient_email

from app.modules.fair_emails.domain.value_objects import (
    ManualRecipientPreviewResult,
    RawRecipientCandidate,
    RecipientOptions,
    RecipientPreviewResult,
    ResolvedRecipient,
    WizardPreviewRecipient,
)


def recipient_key(customer_id: UUID | None, contact_id: UUID | None, email: str) -> str:
    customer_part = str(customer_id) if customer_id else "none"
    contact_part = str(contact_id) if contact_id else "none"
    return f"{customer_part}:{contact_part}:{email.lower()}"


def _most_restrictive_consent_blocks(
    candidates: list[RawRecipientCandidate],
    options: RecipientOptions,
) -> dict[str, str]:
    """Map normalized email → consent skip_reason (customer denial wins)."""
    blocks: dict[str, str] = {}
    for candidate in candidates:
        if options.exclude_inactive and not candidate.is_active:
            continue
        normalized = normalize_bulk_recipient_email(candidate.email)
        if not normalized:
            continue
        consent = evaluate_candidate_email_consent(
            customer_email_allowed=candidate.customer_email_allowed,
            contact_email_allowed=candidate.contact_email_allowed,
            is_contact_source=candidate.source == "contact",
        )
        if consent.allowed or not consent.skip_reason:
            continue
        previous = blocks.get(normalized)
        if previous == CUSTOMER_EMAIL_CONSENT_SKIP:
            continue
        if consent.skip_reason == CUSTOMER_EMAIL_CONSENT_SKIP or previous is None:
            blocks[normalized] = consent.skip_reason
    return blocks


def resolve_recipients(
    candidates: list[RawRecipientCandidate],
    options: RecipientOptions,
) -> RecipientPreviewResult:
    customer_ids: set[UUID] = set()
    contact_ids: set[UUID] = set()
    valid_email_count = 0
    invalid_count = 0
    duplicate_count = 0
    customer_consent_skipped_count = 0
    contact_consent_skipped_count = 0
    resolved: list[ResolvedRecipient] = []
    seen_emails: set[str] = set()
    consent_blocks = _most_restrictive_consent_blocks(candidates, options)

    for candidate in candidates:
        if candidate.source == "customer":
            customer_ids.add(candidate.customer_id)
        if candidate.source == "contact" and candidate.contact_id is not None:
            contact_ids.add(candidate.contact_id)

        # raw → normalize → inactive → consent → validate → dedupe → final
        normalized_email = normalize_bulk_recipient_email(candidate.email)
        status = "will_send"
        skip_reason: str | None = None
        email_for_row = normalized_email

        if options.exclude_inactive and not candidate.is_active:
            status = "skip"
            skip_reason = "inactive_record"
            email_for_row = normalized_email or (candidate.email or "")
        elif normalized_email and normalized_email in consent_blocks:
            email_for_row = normalized_email
            if options.dedupe_emails and normalized_email in seen_emails:
                status = "skip"
                skip_reason = "duplicate_email"
                duplicate_count += 1
            else:
                status = "skip"
                skip_reason = consent_blocks[normalized_email]
                if skip_reason == CUSTOMER_EMAIL_CONSENT_SKIP:
                    customer_consent_skipped_count += 1
                elif skip_reason == CONTACT_EMAIL_CONSENT_SKIP:
                    contact_consent_skipped_count += 1
                if options.dedupe_emails:
                    seen_emails.add(normalized_email)
        elif not normalized_email:
            if options.skip_no_email:
                status = "skip"
                skip_reason = "no_email"
            email_for_row = candidate.email or ""
        elif not is_valid_email_address(normalized_email):
            status = "skip"
            skip_reason = "invalid_email"
            invalid_count += 1
            email_for_row = normalized_email or (candidate.email or "").strip()
        elif options.dedupe_emails and normalized_email in seen_emails:
            status = "skip"
            skip_reason = "duplicate_email"
            duplicate_count += 1
            email_for_row = normalized_email
        else:
            valid_email_count += 1
            email_for_row = normalized_email
            if options.dedupe_emails:
                seen_emails.add(normalized_email)

        resolved.append(
            ResolvedRecipient(
                recipient_key=recipient_key(
                    candidate.customer_id, candidate.contact_id, email_for_row or "none"
                ),
                recipient_name=candidate.recipient_name,
                company_name=candidate.company_name,
                email=email_for_row,
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
        invalid_count=invalid_count,
        duplicate_count=duplicate_count,
        customer_consent_skipped_count=customer_consent_skipped_count,
        contact_consent_skipped_count=contact_consent_skipped_count,
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
    manual_emails_text: str | None = None,
    excel_email_tokens: list[str] | None = None,
    excel_recipient_rows: list[tuple[str, str]] | None = None,
) -> ManualRecipientPreviewResult:
    """Merge manual + Excel recipients: validate, normalize, and dedupe only.

    Manual/Excel addresses are treated as external recipients — no CRM
    Customer/Contact lookup and no EmailConsentPolicy evaluation.
    ``customer_id`` / ``contact_id`` remain unset (NULL downstream).
    """
    entries: list[tuple[str, str, str | None]] = []
    for token in tokenize_email_field(manual_emails_text):
        entries.append((token, "manual", None))
    for display_name, raw_email in excel_recipient_rows or []:
        email = (raw_email or "").strip()
        if not email and not (display_name or "").strip():
            continue
        entries.append((email, "excel", (display_name or "").strip() or None))
    for token in excel_email_tokens or []:
        cleaned = token.strip()
        if cleaned:
            entries.append((cleaned, "excel", None))

    resolved: list[WizardPreviewRecipient] = []
    seen_emails: set[str] = set()
    valid_email_count = 0
    duplicate_count = 0
    invalid_count = 0

    for raw, source, display_name in entries:
        # raw → normalize → validate → (invalid skip) → dedupe → final
        # No CRM lookup / consent for manual|excel sources.
        normalized = normalize_bulk_recipient_email(raw)
        status = "will_send"
        skip_reason: str | None = None
        email_for_row = raw.strip() if raw else ""

        if not normalized or not is_valid_email_address(normalized):
            status = "skip"
            skip_reason = "invalid_email"
            invalid_count += 1
            email_for_row = normalized or raw.strip() or raw or ""
        elif normalized in seen_emails:
            status = "skip"
            skip_reason = "duplicate_email"
            duplicate_count += 1
            email_for_row = normalized
        else:
            email_for_row = normalized
            seen_emails.add(normalized)
            valid_email_count += 1

        # Excel col1 is a free-form display name (person or company) — not CRM.
        name_for_row = display_name if source == "excel" else None
        company_for_row = display_name if source == "excel" else None

        resolved.append(
            WizardPreviewRecipient(
                recipient_key=f"{source}:none:{email_for_row.lower()}",
                email=email_for_row,
                source=source,
                status=status,
                skip_reason=skip_reason,
                recipient_name=name_for_row,
                company_name=company_for_row,
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
        customer_consent_skipped_count=0,
        contact_consent_skipped_count=0,
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
        email = normalize_bulk_recipient_email(part)
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
