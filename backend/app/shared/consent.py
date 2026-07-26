"""Shared email consent constants and pure evaluation helpers.

Customer/Contact CRM fields: ``email_allowed`` (boolean opt-in).
"""

from __future__ import annotations

from dataclasses import dataclass

CONSENT_ERROR_CODE = "consent_blocked"

CUSTOMER_EMAIL_CONSENT_SKIP = "customer_email_consent"
CONTACT_EMAIL_CONSENT_SKIP = "contact_email_consent"

CONSENT_SKIP_REASONS = frozenset({CUSTOMER_EMAIL_CONSENT_SKIP, CONTACT_EMAIL_CONSENT_SKIP})

CONSENT_SKIP_MESSAGES: dict[str, str] = {
    CUSTOMER_EMAIL_CONSENT_SKIP: "Customer e-posta iletişim izni kapalı",
    CONTACT_EMAIL_CONSENT_SKIP: "Contact e-posta iletişim izni kapalı",
}


@dataclass(frozen=True)
class EmailConsentDecision:
    allowed: bool
    skip_reason: str | None = None

    @property
    def message(self) -> str | None:
        if self.allowed or self.skip_reason is None:
            return None
        return CONSENT_SKIP_MESSAGES.get(self.skip_reason, self.skip_reason)


def evaluate_email_consent_flags(
    *,
    customer_email_allowed_flags: list[bool] | tuple[bool, ...] = (),
    contact_email_allowed_flags: list[bool] | tuple[bool, ...] = (),
) -> EmailConsentDecision:
    """Most-restrictive consent from matched Customer/Contact ``email_allowed`` flags.

    Customer denial always wins over contact denial.
    Empty match lists mean no CRM hit → allowed.
    """
    if any(not flag for flag in customer_email_allowed_flags):
        return EmailConsentDecision(allowed=False, skip_reason=CUSTOMER_EMAIL_CONSENT_SKIP)
    if any(not flag for flag in contact_email_allowed_flags):
        return EmailConsentDecision(allowed=False, skip_reason=CONTACT_EMAIL_CONSENT_SKIP)
    return EmailConsentDecision(allowed=True)


def evaluate_candidate_email_consent(
    *,
    customer_email_allowed: bool,
    contact_email_allowed: bool = True,
    is_contact_source: bool = False,
) -> EmailConsentDecision:
    """Evaluate consent for a CRM-backed recipient candidate (fair/list loaders)."""
    contact_flags: tuple[bool, ...] = (contact_email_allowed,) if is_contact_source else ()
    return evaluate_email_consent_flags(
        customer_email_allowed_flags=(customer_email_allowed,),
        contact_email_allowed_flags=contact_flags,
    )


class EmailConsentBlockedError(Exception):
    """Raised when outbound email is blocked by Customer/Contact email_allowed."""

    def __init__(self, decision: EmailConsentDecision) -> None:
        self.decision = decision
        super().__init__(decision.message or "Email consent blocked")
