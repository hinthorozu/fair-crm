from __future__ import annotations

from dataclasses import dataclass

import httpx

OUTCOME_INVALID = "invalid"
OUTCOME_NOT_PROVEN_INVALID = "not_proven_invalid"
OUTCOME_UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class MailerSendTokenVerificationResult:
    outcome: str
    evidence_code: str


class MailerSendExactSecretVerifier:
    """Verify whether one exact stored MailerSend API token remains usable.

    The request is deliberately non-mutating. Response bodies and credentials are
    neither returned nor logged; callers receive only a bounded classification.
    """

    def __init__(self, *, base_url: str = "https://api.mailersend.com") -> None:
        self._base_url = base_url.rstrip("/")

    def verify(self, api_token: str) -> MailerSendTokenVerificationResult:
        token = api_token.strip()
        if not token:
            raise ValueError("MailerSend API token is required for exact-secret verification")

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self._base_url}/v1/token",
                    headers=headers,
                    params={"limit": 10},
                )
        except httpx.RequestError:
            return MailerSendTokenVerificationResult(
                outcome=OUTCOME_UNKNOWN,
                evidence_code="mailersend_exact_secret_transport_error",
            )

        status_code = response.status_code
        if status_code == 401:
            return MailerSendTokenVerificationResult(
                outcome=OUTCOME_INVALID,
                evidence_code="mailersend_exact_secret_http_401",
            )
        if status_code == 200:
            return MailerSendTokenVerificationResult(
                outcome=OUTCOME_NOT_PROVEN_INVALID,
                evidence_code="mailersend_exact_secret_http_200",
            )
        if status_code == 403:
            return MailerSendTokenVerificationResult(
                outcome=OUTCOME_NOT_PROVEN_INVALID,
                evidence_code="mailersend_exact_secret_http_403",
            )
        if status_code == 429:
            return MailerSendTokenVerificationResult(
                outcome=OUTCOME_UNKNOWN,
                evidence_code="mailersend_exact_secret_http_429",
            )
        if 500 <= status_code <= 599:
            return MailerSendTokenVerificationResult(
                outcome=OUTCOME_UNKNOWN,
                evidence_code="mailersend_exact_secret_http_5xx",
            )
        return MailerSendTokenVerificationResult(
            outcome=OUTCOME_UNKNOWN,
            evidence_code="mailersend_exact_secret_unexpected_status",
        )
