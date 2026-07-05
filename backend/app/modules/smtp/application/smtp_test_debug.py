from __future__ import annotations

import logging
from uuid import UUID

from app.core.config import get_settings
from app.modules.smtp.application.commands import SendTestSmtpMailResult
from app.modules.smtp.domain.entities import SmtpAccount
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from app.modules.smtp.domain.smtp_config_validation import smtp_config_warnings
from app.modules.smtp.domain.value_objects import SmtpEncryptionType

logger = logging.getLogger(__name__)


def smtp_debug_response_enabled() -> bool:
    settings = get_settings()
    if settings.app_env.lower() == "production":
        return False
    return settings.smtp_debug_response


def build_test_mail_failure_result(
    account: SmtpAccount,
    *,
    recipient: str,
    exc: SmtpMailDeliveryError,
) -> SendTestSmtpMailResult:
    warnings = tuple(smtp_config_warnings(account.port, account.encryption_type))
    return SendTestSmtpMailResult(
        success=False,
        message=str(exc),
        debug_error_type=exc.error_type,
        debug_error_message=exc.raw_message,
        smtp_host=account.host,
        smtp_port=account.port,
        encryption_type=account.encryption_type,
        config_warnings=warnings,
    )


def log_smtp_test_mail_failure(
    *,
    account: SmtpAccount,
    organization_id: UUID,
    recipient: str,
    exc: SmtpMailDeliveryError | None = None,
    reason: str | None = None,
) -> None:
    warnings = smtp_config_warnings(account.port, account.encryption_type)
    payload = {
        "event": "smtp_test_mail_failed",
        "account_id": str(account.id),
        "organization_id": str(organization_id),
        "smtp_host": account.host,
        "smtp_port": account.port,
        "encryption_type": account.encryption_type.value,
        "from_email": account.from_email,
        "to_email": recipient,
        "password_set": bool(account.password),
        "config_warnings": warnings,
    }
    if exc is not None:
        payload["exception_type"] = exc.error_type or type(exc).__name__
        payload["user_message"] = str(exc)
        payload["raw_exception_message"] = exc.raw_message or str(exc)
    if reason is not None:
        payload["reason"] = reason

    logger.warning("smtp_test_mail_failed %s", " ".join(f"{key}={value}" for key, value in payload.items()))
