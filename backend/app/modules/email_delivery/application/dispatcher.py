from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from app.modules.email_accounts.domain.entities import EmailAccount, EmailAccountSmtpConfig
from app.modules.email_accounts.domain.error_policy import (
    ProviderErrorPolicy,
    evaluate_error_policy,
)
from app.modules.email_accounts.domain.value_objects import EmailAccountType
from app.modules.email_delivery.application.provider_registry import (
    EmailProviderRegistry,
    create_default_provider_registry,
)
from app.modules.email_delivery.domain.exceptions import (
    EmailDeliveryError,
    ProviderMessageSkippedError,
    UnsupportedProviderError,
)
from app.modules.email_delivery.domain.results import EmailDeliveryResult
from app.modules.email_delivery.infrastructure.smtp_sender import SmtpEmailSender


class EmailDeliveryDispatcher:
    def __init__(
        self,
        provider_registry: EmailProviderRegistry | None = None,
        smtp_sender: SmtpEmailSender | None = None,
        *,
        deactivate_account: Callable[[EmailAccount], None] | None = None,
    ):
        self._registry = provider_registry or create_default_provider_registry()
        self._smtp_sender = smtp_sender or SmtpEmailSender()
        self._deactivate_account = deactivate_account

    def send(
        self,
        account: EmailAccount,
        *,
        recipient: str,
        subject: str,
        body_html: str | None = None,
        body_text: str | None = None,
        smtp_config: EmailAccountSmtpConfig | None = None,
        provider_config: dict[str, str] | None = None,
        error_policy: ProviderErrorPolicy | None = None,
    ) -> EmailDeliveryResult:
        if account.account_type == EmailAccountType.SMTP:
            if smtp_config is None:
                raise EmailDeliveryError(
                    "SMTP config required",
                    error_code="MissingSmtpConfig",
                    transport="smtp",
                    retryable=False,
                )
            return self._smtp_sender.send(
                account,
                recipient=recipient,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
                smtp_config=smtp_config,
            )

        if account.account_type == EmailAccountType.PROVIDER:
            if not account.provider_key:
                raise UnsupportedProviderError(
                    "provider_key is required",
                    error_code="MissingProviderKey",
                    transport="provider",
                    retryable=False,
                )
            adapter = self._registry.require(account.provider_key)
            try:
                return adapter.send(
                    account,
                    recipient=recipient,
                    subject=subject,
                    body_html=body_html,
                    body_text=body_text,
                    provider_config=provider_config or {},
                )
            except EmailDeliveryError as exc:
                return self._apply_provider_policy(account, exc, error_policy=error_policy)

        raise EmailDeliveryError(
            f"Unsupported account type: {account.account_type}",
            error_code="UnsupportedAccountType",
            retryable=False,
        )

    def _apply_provider_policy(
        self,
        account: EmailAccount,
        exc: EmailDeliveryError,
        *,
        error_policy: ProviderErrorPolicy | None,
    ) -> EmailDeliveryResult:
        decision = evaluate_error_policy(error_policy, exc.error_code)
        if decision.deactivate_account and self._deactivate_account is not None:
            self._deactivate_account(account)

        message = str(exc.args[0]) if exc.args else "Provider delivery failed"
        if decision.skip_message:
            raise ProviderMessageSkippedError(
                message,
                error_code=exc.error_code or "ProviderMessageSkipped",
                transport=exc.transport or f"provider:{account.provider_key}",
                retryable=False,
                retry_after_seconds=exc.retry_after_seconds,
                provider_status=exc.provider_status,
                policy_category=decision.category.value if decision.category else None,
                policy_action=decision.action,
            )

        # Unknown identifiers fail closed. Retry behavior is controlled by the
        # error groups configured on the provider account.
        retryable = bool(decision.retryable) if decision.category is not None else False

        raise EmailDeliveryError(
            message,
            error_code=exc.error_code,
            transport=exc.transport or f"provider:{account.provider_key}",
            retryable=retryable,
            retry_after_seconds=exc.retry_after_seconds,
            provider_status=exc.provider_status,
            policy_category=decision.category.value if decision.category else None,
            policy_action=decision.action,
        )


def deactivate_email_account_in_session(session, account: EmailAccount) -> None:
    """Helper for wiring dispatcher account deactivation into a SQLAlchemy session."""
    from app.modules.email_accounts.infrastructure.repositories.email_account_repository import (
        SqlAlchemyEmailAccountRepository,
    )

    repo = SqlAlchemyEmailAccountRepository(session)
    fresh = repo.get_by_id(account.organization_id, account.id)
    if fresh is None:
        return
    now = datetime.now(tz=UTC)
    was_default = fresh.is_default
    fresh.update_common_fields(is_active=False, is_default=False, now=now)
    repo.update_account(fresh)
    if was_default:
        repo.promote_next_active_default(
            account.organization_id,
            exclude_account_id=account.id,
            now=now,
        )
