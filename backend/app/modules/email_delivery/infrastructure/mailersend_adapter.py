"""MailerSend HTTP adapter — implements EmailProviderAdapter."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

import httpx

from app.modules.email_accounts.application.provider_definitions import MAILERSEND_PROVIDER_KEY
from app.modules.email_accounts.domain.entities import EmailAccount
from app.modules.email_delivery.domain.exceptions import EmailDeliveryError
from app.modules.email_delivery.domain.results import EmailDeliveryResult
from app.shared.email import is_valid_email_address

logger = logging.getLogger(__name__)

MAILERSEND_EMAIL_URL = "https://api.mailersend.com/v1/email"


def _extract_accepted_warning(response: httpx.Response) -> tuple[str, str, str] | None:
    """Return (warning type, normalized provider status, readable message)."""
    try:
        payload = response.json()
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    warnings = payload.get("warnings")
    if not isinstance(warnings, list):
        return None
    for warning in warnings:
        if not isinstance(warning, dict):
            continue
        warning_type = str(warning.get("type") or "").strip()
        if warning_type != "ALLSUPPRESSED":
            continue
        reasons: list[str] = []
        emails: list[str] = []
        recipients = warning.get("recipients")
        if isinstance(recipients, list):
            for recipient in recipients:
                if not isinstance(recipient, dict):
                    continue
                email = str(recipient.get("email") or "").strip()
                if email:
                    emails.append(email)
                raw_reasons = recipient.get("reasons")
                if isinstance(raw_reasons, list):
                    reasons.extend(str(reason).strip() for reason in raw_reasons if str(reason).strip())
        unique_reasons = sorted(set(reasons))
        normalized_status = (
            "hard_bounced" if "hardbounced" in unique_reasons else "suppressed"
        )
        reason_text = ", ".join(unique_reasons) or "suppressed"
        email_text = f" ({', '.join(sorted(set(emails)))})" if emails else ""
        return warning_type, normalized_status, f"MailerSend suppressed recipient{email_text}: {reason_text}"
    return None


def _extract_error_identifier(response: httpx.Response) -> str:
    """Prefer machine identifiers (type/name/code); fall back to HTTP status string."""
    status = str(response.status_code)
    # Cloudflare rate-limit payloads may expose a documentation URL as their
    # JSON code. The actionable identifier remains the HTTP 429 status.
    if response.status_code == 429:
        return status
    try:
        payload = response.json()
    except Exception:
        return status

    if isinstance(payload, dict):
        for key in ("type", "name", "code"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip() and " " not in value.strip():
                candidate = value.strip()
                if not candidate.lower().startswith(("http://", "https://")):
                    return candidate
    return status


def _parse_retry_after(response: httpx.Response) -> int | None:
    raw = response.headers.get("Retry-After")
    if not raw:
        return None
    try:
        return max(0, int(str(raw).strip()))
    except ValueError:
        return None


class MailerSendAdapter:
    provider_key = MAILERSEND_PROVIDER_KEY

    def __init__(
        self,
        *,
        http_client: httpx.Client | None = None,
        transport: Callable[..., httpx.Response] | None = None,
        base_url: str = MAILERSEND_EMAIL_URL,
    ) -> None:
        self._client = http_client
        self._transport = transport
        self._base_url = base_url

    def send(
        self,
        account: EmailAccount,
        *,
        recipient: str,
        subject: str,
        body_html: str | None = None,
        body_text: str | None = None,
        provider_config: dict[str, str] | None = None,
    ) -> EmailDeliveryResult:
        config = provider_config or {}
        api_token = (config.get("api_token") or "").strip()
        if not api_token:
            raise EmailDeliveryError(
                "MailerSend API token is not configured",
                error_code="MissingApiToken",
                transport=f"provider:{self.provider_key}",
                retryable=False,
            )

        from_email = (config.get("from_email") or account.from_email or "").strip()
        from_name = (config.get("from_name") or account.from_name or "").strip() or None
        if not is_valid_email_address(from_email):
            raise EmailDeliveryError(
                "MailerSend from_email is not configured",
                error_code="MissingFromEmail",
                transport=f"provider:{self.provider_key}",
                retryable=False,
            )

        payload: dict[str, Any] = {
            "from": {"email": from_email, **({"name": from_name} if from_name else {})},
            "to": [{"email": recipient}],
            "subject": subject,
        }
        if body_html:
            payload["html"] = body_html
        if body_text:
            payload["text"] = body_text
        if not body_html and not body_text:
            payload["text"] = subject

        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            response = self._post(headers=headers, payload=payload)
        except httpx.TimeoutException as exc:
            raise EmailDeliveryError(
                "MailerSend request timed out",
                error_code="TimeoutError",
                transport=f"provider:{self.provider_key}",
                retryable=True,
            ) from exc
        except httpx.HTTPError as exc:
            raise EmailDeliveryError(
                "MailerSend connection error",
                error_code="ConnectionError",
                transport=f"provider:{self.provider_key}",
                retryable=True,
            ) from exc

        if response.status_code == 202:
            accepted_warning = _extract_accepted_warning(response)
            if accepted_warning is not None:
                warning_type, provider_status, warning_message = accepted_warning
                raise EmailDeliveryError(
                    warning_message,
                    error_code=warning_type,
                    transport=f"provider:{self.provider_key}",
                    retryable=False,
                    provider_status=provider_status,
                )
            external_id = response.headers.get("x-message-id") or response.headers.get("X-Message-Id")
            if not external_id:
                raise EmailDeliveryError(
                    "MailerSend accepted the request without an x-message-id; delivery was not queued",
                    error_code="MailerSendMissingMessageId",
                    transport=f"provider:{self.provider_key}",
                    retryable=False,
                    provider_status="202",
                )
            return EmailDeliveryResult(
                success=True,
                transport=f"provider:{self.provider_key}",
                external_message_id=external_id,
                # Initial provider acceptance only — webhook updates later statuses.
                provider_status="accepted",
            )

        identifier = _extract_error_identifier(response)
        message = self._safe_error_message(response, identifier)
        retry_after = _parse_retry_after(response)
        # Adapter does not apply business policy — raw identifier only.
        raise EmailDeliveryError(
            message,
            error_code=identifier,
            transport=f"provider:{self.provider_key}",
            retryable=None,
            retry_after_seconds=retry_after,
            provider_status=str(response.status_code),
        )

    def _post(self, *, headers: dict[str, str], payload: dict[str, Any]) -> httpx.Response:
        if self._transport is not None:
            return self._transport(
                "POST",
                self._base_url,
                headers=headers,
                json=payload,
            )
        client = self._client
        owns_client = False
        if client is None:
            client = httpx.Client(timeout=30.0)
            owns_client = True
        try:
            return client.post(self._base_url, headers=headers, json=payload)
        finally:
            if owns_client:
                client.close()

    @staticmethod
    def _safe_error_message(response: httpx.Response, identifier: str) -> str:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                message = payload.get("message")
                if isinstance(message, str) and message.strip():
                    return message.strip()
        except Exception:
            pass
        text = (response.text or "").strip()
        if text and len(text) < 500 and "Bearer" not in text:
            try:
                json.loads(text)
            except Exception:
                return f"MailerSend error ({identifier})"
            return f"MailerSend error ({identifier})"
        return f"MailerSend error ({identifier})"
