"""Unified email-account lifecycle operations (SMTP + provider)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.email_accounts.application.response_mappers import email_account_to_response_dict
from app.modules.email_accounts.domain.entities import EmailAccount
from app.modules.email_accounts.domain.exceptions import (
    EmailAccountAlreadyDeletedError,
    EmailAccountNotDefaultEligibleError,
    EmailAccountNotFoundError,
)
from app.modules.email_accounts.domain.value_objects import EmailAccountType
from app.modules.email_accounts.infrastructure.repositories.email_account_repository import (
    SqlAlchemyEmailAccountRepository,
)
from app.modules.email_delivery.application.email_delivery_service import EmailDeliveryService
from app.modules.mail_send_operations.application.mail_send_operation_service import (
    MailSendOperationService,
)
from app.modules.mail_send_operations.domain.value_objects import MailSendSourceType
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    CreateMailSendOperationParams,
)
from app.modules.smtp.domain.exceptions import (
    InvalidSmtpTestRecipientError,
    SmtpMailDeliveryError,
)
from app.shared.email import sanitize_scraped_email

PERMISSION_READ = "fair_crm.email_accounts.read"
PERMISSION_UPDATE = "fair_crm.email_accounts.update"
PERMISSION_DELETE = "fair_crm.email_accounts.delete"


@dataclass(frozen=True)
class EmailAccountView:
    data: dict[str, Any]


class ListEmailAccountsUseCase:
    def __init__(self, repository: SqlAlchemyEmailAccountRepository) -> None:
        self._repository = repository

    def execute(self, organization_id: UUID) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for account in self._repository.list_by_organization(organization_id):
            items.append(self._to_dict(account))
        return items

    def _to_dict(self, account: EmailAccount) -> dict[str, Any]:
        if account.account_type == EmailAccountType.SMTP:
            smtp = self._repository.get_smtp_config(account.id)
            return email_account_to_response_dict(account, smtp_config=smtp)
        provider = self._repository.get_provider_config(account.id)
        return email_account_to_response_dict(account, provider_config=provider)


class GetEmailAccountUseCase:
    def __init__(self, repository: SqlAlchemyEmailAccountRepository) -> None:
        self._repository = repository

    def execute(self, organization_id: UUID, account_id: UUID) -> dict[str, Any]:
        account = self._repository.get_by_id(organization_id, account_id)
        if account is None:
            raise EmailAccountNotFoundError("Email account not found")
        if account.account_type == EmailAccountType.SMTP:
            smtp = self._repository.get_smtp_config(account.id)
            return email_account_to_response_dict(account, smtp_config=smtp)
        provider = self._repository.get_provider_config(account.id)
        return email_account_to_response_dict(account, provider_config=provider)


class SetDefaultEmailAccountUseCase:
    def __init__(
        self,
        repository: SqlAlchemyEmailAccountRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

    def execute(
        self,
        *,
        organization_id: UUID,
        account_id: UUID,
        access_token: str,
        user_id: UUID,
    ) -> dict[str, Any]:
        if not self._authorization.check_permission(
            organization_id=organization_id,
            user_id=user_id,
            permission_code=PERMISSION_UPDATE,
            access_token=access_token,
        ):
            raise ForbiddenError("Permission denied")

        account = self._repository.get_by_id(organization_id, account_id)
        if account is None:
            raise EmailAccountNotFoundError("Email account not found")
        now = datetime.now(tz=UTC)
        try:
            account.ensure_default_eligible()
        except EmailAccountAlreadyDeletedError as exc:
            raise EmailAccountAlreadyDeletedError(str(exc)) from exc
        except EmailAccountNotDefaultEligibleError as exc:
            raise EmailAccountNotDefaultEligibleError(str(exc)) from exc

        self._repository.clear_default_for_organization(
            organization_id, exclude_account_id=account.id
        )
        self._repository.flush()
        account.mark_as_default(now=now)
        saved = self._repository.update_account(account)

        self._audit.record_event(
            organization_id=organization_id,
            access_token=access_token,
            action="fair_crm.email_account.set_default",
            resource_type="email_account",
            resource_id=str(saved.id),
            metadata={"user_id": str(user_id)},
        )
        return GetEmailAccountUseCase(self._repository).execute(organization_id, saved.id)


class DeleteEmailAccountUseCase:
    def __init__(
        self,
        repository: SqlAlchemyEmailAccountRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

    def execute(
        self,
        *,
        organization_id: UUID,
        account_id: UUID,
        access_token: str,
        user_id: UUID,
    ) -> dict[str, Any]:
        if not self._authorization.check_permission(
            organization_id=organization_id,
            user_id=user_id,
            permission_code=PERMISSION_DELETE,
            access_token=access_token,
        ):
            raise ForbiddenError("Permission denied")

        account = self._repository.get_by_id(organization_id, account_id)
        if account is None:
            raise EmailAccountNotFoundError("Email account not found")

        now = datetime.now(tz=UTC)
        if account.is_default:
            self._repository.promote_next_active_default(
                organization_id,
                exclude_account_id=account.id,
                now=now,
            )

        # Snapshot response shape before soft-delete.
        response = GetEmailAccountUseCase(self._repository).execute(organization_id, account.id)
        account.soft_delete(now=now)
        self._repository.update_account(account)

        self._audit.record_event(
            organization_id=organization_id,
            access_token=access_token,
            action="fair_crm.email_account.deleted",
            resource_type="email_account",
            resource_id=str(account.id),
            metadata={"user_id": str(user_id)},
        )
        response["deleted_at"] = account.deleted_at
        response["is_active"] = False
        response["is_default"] = False
        return response


@dataclass(frozen=True)
class SendTestEmailAccountResult:
    success: bool
    message: str
    config_warnings: tuple[str, ...] = ()


class SendTestEmailAccountMailUseCase:
    """Send a test message through the central EmailDeliveryService."""

    def __init__(
        self,
        repository: SqlAlchemyEmailAccountRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
        mail_send_operations: MailSendOperationService,
        session,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit
        self._mail_send_operations = mail_send_operations
        self._session = session
        self._delivery = EmailDeliveryService(session)

    def execute(
        self,
        *,
        organization_id: UUID,
        account_id: UUID,
        access_token: str,
        user_id: UUID,
        recipient: str,
    ) -> SendTestEmailAccountResult:
        if not self._authorization.check_permission(
            organization_id=organization_id,
            user_id=user_id,
            permission_code=PERMISSION_UPDATE,
            access_token=access_token,
        ):
            raise ForbiddenError("Permission denied")

        cleaned_recipient = sanitize_scraped_email(recipient)
        if cleaned_recipient is None:
            raise InvalidSmtpTestRecipientError("Valid recipient email is required")
        recipient = cleaned_recipient

        from app.shared.consent import EmailConsentBlockedError
        from app.shared.email_consent_policy import EmailConsentPolicy

        try:
            EmailConsentPolicy(self._session).ensure_allowed(
                organization_id,
                email=recipient,
            )
        except EmailConsentBlockedError as exc:
            raise InvalidSmtpTestRecipientError(
                exc.decision.message or "E-posta iletişim izni kapalı"
            ) from exc

        account = self._repository.get_by_id(organization_id, account_id)
        if account is None:
            raise EmailAccountNotFoundError("Email account not found")
        if account.deleted_at is not None:
            raise EmailAccountAlreadyDeletedError("Email account is deleted")

        subject = "FAIR CRM Email Account Test"
        body = (
            "This is a test message from FAIR CRM email account settings.\n"
            "If you received this email, the account configuration is working."
        )

        if not account.is_active:
            self._mail_send_operations.record_immediate_failure(
                CreateMailSendOperationParams(
                    organization_id=organization_id,
                    source_type=MailSendSourceType.SMTP_TEST,
                    recipient_email=recipient,
                    subject=subject,
                    body_text=body,
                    email_account_id=account.id,
                    max_retry_count=account.max_delivery_attempts,
                    metadata_json={"email_account_name": account.name},
                ),
                error_code="InactiveAccount",
                error_message="Email account is inactive",
            )
            return SendTestEmailAccountResult(
                success=False,
                message="Email account is inactive",
            )

        operation_params = CreateMailSendOperationParams(
            organization_id=organization_id,
            source_type=MailSendSourceType.SMTP_TEST,
            recipient_email=recipient,
            subject=subject,
            body_text=body,
            email_account_id=account.id,
            max_retry_count=account.max_delivery_attempts,
            metadata_json={
                "email_account_name": account.name,
                "account_type": account.account_type.value,
                "provider_key": account.provider_key,
            },
        )

        try:
            self._mail_send_operations.execute_synchronous_send(
                operation_params,
                send_fn=lambda: self._delivery.send(
                    organization_id=organization_id,
                    email_account_id=account.id,
                    to=recipient,
                    subject=subject,
                    body_text=body,
                ),
            )
        except SmtpMailDeliveryError as exc:
            return SendTestEmailAccountResult(
                success=False,
                message=str(exc.args[0]) if exc.args else "Test mail failed",
            )

        self._audit.record_event(
            organization_id=organization_id,
            access_token=access_token,
            action="fair_crm.email_account.test_mail",
            resource_type="email_account",
            resource_id=str(account.id),
            metadata={"user_id": str(user_id), "recipient": recipient},
        )
        return SendTestEmailAccountResult(success=True, message="Test mail sent")
