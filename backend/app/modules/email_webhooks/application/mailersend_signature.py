"""MailerSend webhook HMAC-SHA256 signature verification."""

from __future__ import annotations

import hashlib
import hmac

# Official MailerSend fixed secret for webhook.test endpoint validation pings.
MAILERSEND_WEBHOOK_TEST_SIGNING_SECRET = "test_Am3L1GuOIc4blLUuHqAPxxwkZaJyEk8G"


def compute_mailersend_signature(*, raw_body: bytes, signing_secret: str) -> str:
    return hmac.new(
        signing_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()


def verify_mailersend_signature(
    *,
    raw_body: bytes,
    signature_header: str | None,
    signing_secret: str,
) -> bool:
    if not signature_header or not signing_secret:
        return False
    expected = compute_mailersend_signature(raw_body=raw_body, signing_secret=signing_secret)
    received = signature_header.strip()
    if len(received) != len(expected):
        return False
    return hmac.compare_digest(received, expected)
