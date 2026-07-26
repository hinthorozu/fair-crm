"""Central email delivery gateway — single account/config/secret resolve path."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.email_accounts.domain.entities import EmailAccount, EmailAccountSmtpConfig
from app.modules.email_accounts.domain.provider_config import EmailAccountProviderConfig
from app.modules.email_accounts.domain.value_objects import EmailAccountType
from app.modules.email_accounts.infrastructure.repositories.email_account_repository import (
    SqlAlchemyEmailAccountRepository,
)
from app.modules.email_delivery.application.deliver import deliver_with_dispatcher
from app.modules.email_delivery.application.dispatcher import (
    EmailDeliveryDispatcher,
    deactivate_email_account_in_session,
)
from app.modules.email_delivery.domain.results import EmailDeliveryResult
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError


class EmailDeliveryService:
    """Resolve email account + decrypted configs, then dispatch via EmailDeliveryDispatcher.

    Callers pass only account id and message fields — no SMTP/provider config loading.
    """

    def __init__(
        self,
        session: Session,
        *,
        dispatcher: EmailDeliveryDispatcher | None = None,
        account_repository: SqlAlchemyEmailAccountRepository | None = None,
    ) -> None:
        self._session = session
        self._accounts = account_repository or SqlAlchemyEmailAccountRepository(session)
        self._dispatcher = dispatcher or EmailDeliveryDispatcher(
            deactivate_account=lambda account: deactivate_email_account_in_session(
                session, account
            ),
        )

    def send(
        self,
        *,
        organization_id: UUID,
        email_account_id: UUID,
        to: str,
        subject: str,
        body_html: str | None = None,
        body_text: str | None = None,
    ) -> EmailDeliveryResult:
        account, smtp_config, provider_config = self._resolve_account(
            organization_id,
            email_account_id,
        )
        return deliver_with_dispatcher(
            account,
            recipient=to,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            smtp_config=smtp_config,
            provider_config=provider_config.config if provider_config else None,
            error_policy=provider_config.error_policy if provider_config else None,
            dispatcher=self._dispatcher,
        )

    def _resolve_account(
        self,
        organization_id: UUID,
        email_account_id: UUID,
    ) -> tuple[
        EmailAccount,
        EmailAccountSmtpConfig | None,
        EmailAccountProviderConfig | None,
    ]:
        account = self._accounts.get_by_id(organization_id, email_account_id)
        if account is None or account.deleted_at is not None:
            raise SmtpMailDeliveryError(
                "Email account not found",
                error_type="EmailAccountNotFound",
                retryable=False,
            )
        if not account.is_active:
            raise SmtpMailDeliveryError(
                "Email account is inactive",
                error_type="InactiveAccount",
                retryable=False,
            )

        smtp_config: EmailAccountSmtpConfig | None = None
        provider_config: EmailAccountProviderConfig | None = None
        if account.account_type == EmailAccountType.SMTP:
            smtp_config = self._accounts.get_smtp_config(account.id)
            if smtp_config is None:
                raise SmtpMailDeliveryError(
                    "SMTP config not found",
                    error_type="MissingSmtpConfig",
                    retryable=False,
                )
            if not smtp_config.password:
                raise SmtpMailDeliveryError(
                    "SMTP password is not configured",
                    error_type="MissingPassword",
                    retryable=False,
                )
        elif account.account_type == EmailAccountType.PROVIDER:
            provider_config = self._accounts.get_provider_config(account.id)
            if provider_config is None:
                raise SmtpMailDeliveryError(
                    "Provider config not found",
                    error_type="MissingProviderConfig",
                    retryable=False,
                )
        else:
            raise SmtpMailDeliveryError(
                f"Unsupported account type: {account.account_type}",
                error_type="UnsupportedAccountType",
                retryable=False,
            )
        return account, smtp_config, provider_config
