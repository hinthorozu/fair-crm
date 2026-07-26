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

logger = logging.getLogger(__name__)

MAILERSEND_EMAIL_URL = "https://api.mailersend.com/v1/email"


def _extract_error_identifier(response: httpx.Response) -> str:
    """Prefer machine identifiers (type/name/code); fall back to HTTP status string."""
    status = str(response.status_code)
    try:
        payload = response.json()
    except Exception:
        return status

    if isinstance(payload, dict):
        for key in ("type", "name", "code"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip() and " " not in value.strip():
                return value.strip()
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
        if not from_email or "@" not in from_email:
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

        if response.status_code in {200, 201, 202}:
            external_id = response.headers.get("x-message-id") or response.headers.get("X-Message-Id")
            return EmailDeliveryResult(
                success=True,
                transport=f"provider:{self.provider_key}",
                external_message_id=external_id or None,
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
