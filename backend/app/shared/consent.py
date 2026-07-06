"""Shared consent constants for email/SMS opt-in checks."""

CONSENT_ERROR_CODE = "consent_blocked"

CUSTOMER_EMAIL_CONSENT_SKIP = "customer_email_consent"
CONTACT_EMAIL_CONSENT_SKIP = "contact_email_consent"

CONSENT_SKIP_REASONS = frozenset({CUSTOMER_EMAIL_CONSENT_SKIP, CONTACT_EMAIL_CONSENT_SKIP})

CONSENT_SKIP_MESSAGES: dict[str, str] = {
    CUSTOMER_EMAIL_CONSENT_SKIP: "Customer email consent disabled",
    CONTACT_EMAIL_CONSENT_SKIP: "Contact email consent disabled",
}
