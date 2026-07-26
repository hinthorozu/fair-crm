"""Process MailerSend email activity webhooks into MSO provider_status (+ consent)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.activities.domain.entities import Activity
from app.modules.activities.domain.value_objects import ActivitySource, ActivityStatus, ActivityType
from app.modules.activities.infrastructure.repositories.activity_repository import (
    SqlAlchemyActivityRepository,
)
from app.modules.contacts.infrastructure.repositories.contact_repository import (
    SqlAlchemyContactRepository,
)
from app.modules.customers.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)
from app.modules.email_accounts.application.provider_definitions import MAILERSEND_PROVIDER_KEY
from app.modules.email_accounts.infrastructure.repositories.email_account_repository import (
    SqlAlchemyEmailAccountRepository,
)
from app.modules.email_delivery.application.provider_status_policy import (
    SUPPORTED_MAILERSEND_ACTIVITY_EVENTS,
    apply_provider_status_transition,
    map_mailersend_event_to_provider_status,
)
from app.modules.email_webhooks.application.mailersend_signature import (
    MAILERSEND_WEBHOOK_TEST_SIGNING_SECRET,
    verify_mailersend_signature,
)
from app.modules.mail_send_operations.domain.entities import MailSendOperationRecord
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    SqlAlchemyMailSendOperationRepository,
)

logger = logging.getLogger(__name__)

ConsentReason = Literal["unsubscribed", "spam_complaint"]

CONSENT_EVENTS: dict[str, ConsentReason] = {
    "activity.unsubscribed": "unsubscribed",
    "activity.spam_complaint": "spam_complaint",
}


class MailerSendWebhookInvalidSignatureError(Exception):
    """Signature verification failed — map to 4xx, no side effects."""


class MailerSendWebhookMissingSigningSecretError(Exception):
    """Account has no webhook_signing_secret — map to 503 so provider retries."""


class MailerSendWebhookAccountNotFoundError(Exception):
    """Unknown or deleted email account id."""


class MailerSendWebhookNotMailerSendAccountError(Exception):
    """email_account_id is not a MailerSend provider account."""


@dataclass(frozen=True)
class MailerSendWebhookResult:
    outcome: str  # processed | ignored | test_ok
    detail: str | None = None


class MailerSendWebhookService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._accounts = SqlAlchemyEmailAccountRepository(session)
        self._operations = SqlAlchemyMailSendOperationRepository(session)
        self._customers = SqlAlchemyCustomerRepository(session)
        self._contacts = SqlAlchemyContactRepository(session)
        self._activities = SqlAlchemyActivityRepository(session)

    def handle(
        self,
        *,
        email_account_id: UUID,
        raw_body: bytes,
        signature_header: str | None,
        payload: dict[str, Any],
    ) -> MailerSendWebhookResult:
        event_type = str(payload.get("type") or "").strip()

        if event_type == "webhook.test":
            if not verify_mailersend_signature(
                raw_body=raw_body,
                signature_header=signature_header,
                signing_secret=MAILERSEND_WEBHOOK_TEST_SIGNING_SECRET,
            ):
                raise MailerSendWebhookInvalidSignatureError("invalid webhook.test signature")
            return MailerSendWebhookResult(outcome="test_ok", detail="webhook.test")

        account = self._accounts.get_by_id_unscoped(email_account_id)
        if account is None:
            raise MailerSendWebhookAccountNotFoundError(str(email_account_id))
        if (account.provider_key or "").strip().lower() != MAILERSEND_PROVIDER_KEY:
            raise MailerSendWebhookNotMailerSendAccountError(str(email_account_id))

        provider_config = self._accounts.get_provider_config(email_account_id)
        signing_secret = ""
        if provider_config is not None:
            signing_secret = (provider_config.config.get("webhook_signing_secret") or "").strip()
        if not signing_secret:
            raise MailerSendWebhookMissingSigningSecretError(str(email_account_id))

        if not verify_mailersend_signature(
            raw_body=raw_body,
            signature_header=signature_header,
            signing_secret=signing_secret,
        ):
            raise MailerSendWebhookInvalidSignatureError("invalid webhook signature")

        if event_type not in SUPPORTED_MAILERSEND_ACTIVITY_EVENTS:
            logger.info(
                "mailersend_webhook_unsupported_event account_id=%s type=%s",
                email_account_id,
                event_type,
            )
            return MailerSendWebhookResult(outcome="ignored", detail="unsupported_event")

        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        message_id = str(data.get("message_id") or "").strip()
        if not message_id:
            logger.info(
                "mailersend_webhook_missing_message_id account_id=%s type=%s",
                email_account_id,
                event_type,
            )
            return MailerSendWebhookResult(outcome="ignored", detail="missing_message_id")

        operation = self._operations.find_by_email_account_and_external_message_id(
            email_account_id=email_account_id,
            external_message_id=message_id,
        )
        if operation is None:
            logger.info(
                "mailersend_webhook_unknown_message_id account_id=%s message_id=%s type=%s",
                email_account_id,
                message_id,
                event_type,
            )
            return MailerSendWebhookResult(outcome="ignored", detail="unknown_message_id")

        incoming_status = map_mailersend_event_to_provider_status(event_type)
        assert incoming_status is not None
        pipeline_status_before = operation.status

        next_status = apply_provider_status_transition(operation.provider_status, incoming_status)
        if next_status is not None:
            operation = self._operations.update_provider_status(
                operation.organization_id,
                operation.id,
                provider_status=next_status,
            )

        # Guard: pipeline status must never be rewritten by webhook provider_status updates.
        if operation.status != pipeline_status_before:
            logger.error(
                "mailersend_webhook_pipeline_status_mutated operation_id=%s before=%s after=%s",
                operation.id,
                pipeline_status_before,
                operation.status,
            )

        consent_reason = CONSENT_EVENTS.get(event_type)
        if consent_reason is not None:
            self._apply_consent_and_activity(
                operation=operation,
                reason=consent_reason,
                recipient_email=str(data.get("email") or operation.recipient_email or ""),
            )

        return MailerSendWebhookResult(outcome="processed", detail=incoming_status)

    def _apply_consent_and_activity(
        self,
        *,
        operation: MailSendOperationRecord,
        reason: ConsentReason,
        recipient_email: str,
    ) -> None:
        if self._activities.exists_mailersend_webhook_consent_activity(
            operation.organization_id,
            mail_send_operation_id=operation.id,
            provider_event=reason,
        ):
            return

        target = self._resolve_consent_target(operation)
        if target is None:
            logger.info(
                "mailersend_webhook_consent_no_crm_link operation_id=%s reason=%s",
                operation.id,
                reason,
            )
            return

        kind, entity_id, customer_id_for_activity, contact_id_for_activity = target
        now = datetime.now(tz=UTC)
        email = (recipient_email or operation.recipient_email or "").strip()

        if kind == "contact":
            contact = self._contacts.get_by_id(operation.organization_id, entity_id)
            if contact is None:
                return
            if contact.email_allowed:
                contact.update_fields(email_allowed=False, now=now)
                self._contacts.update(contact)
        else:
            customer = self._customers.get_by_id(operation.organization_id, entity_id)
            if customer is None:
                return
            if customer.email_allowed:
                customer.update_fields(email_allowed=False, now=now)
                self._customers.update(customer)

        if self._activities.exists_mailersend_webhook_consent_activity(
            operation.organization_id,
            mail_send_operation_id=operation.id,
            provider_event=reason,
        ):
            return

        description = self._consent_activity_description(reason=reason, email=email)
        subject = (
            "E-posta iletişim izni kapatıldı (spam complaint)"
            if reason == "spam_complaint"
            else "E-posta iletişim izni kapatıldı (unsubscribe)"
        )
        activity = Activity.create(
            organization_id=operation.organization_id,
            customer_id=customer_id_for_activity,
            contact_id=contact_id_for_activity,
            activity_type=ActivityType.EMAIL,
            subject=subject,
            description=description,
            activity_date=now,
            status=ActivityStatus.COMPLETED,
            source=ActivitySource.EMAIL_AUTOMATION,
            metadata_json={
                "source": "mailersend_webhook",
                "provider_event": reason,
                "mail_send_operation_id": str(operation.id),
                "external_message_id": operation.external_message_id,
                "email_account_id": str(operation.email_account_id)
                if operation.email_account_id
                else None,
                "recipient_email": email,
                "consent_target": kind,
            },
            now=now,
        )
        self._activities.add(activity)

    def _resolve_consent_target(
        self,
        operation: MailSendOperationRecord,
    ) -> tuple[Literal["contact", "customer"], UUID, UUID | None, UUID | None] | None:
        """Return (kind, entity_id, activity_customer_id, activity_contact_id)."""
        meta = operation.metadata_json or {}
        recipient_source = str(meta.get("recipient_source") or "").strip().lower()
        contact_id: UUID | None = None
        contact_id_raw = meta.get("contact_id")
        if contact_id_raw:
            try:
                contact_id = UUID(str(contact_id_raw))
            except (TypeError, ValueError):
                contact_id = None

        def _customer_for_contact(cid: UUID) -> UUID | None:
            if operation.customer_id is not None:
                return operation.customer_id
            contact = self._contacts.get_by_id(operation.organization_id, cid)
            return contact.customer_id if contact is not None else None

        if recipient_source == "contact" and contact_id is not None:
            customer_id = _customer_for_contact(contact_id)
            if customer_id is None:
                return None
            return ("contact", contact_id, customer_id, contact_id)

        if recipient_source == "customer" and operation.customer_id is not None:
            return ("customer", operation.customer_id, operation.customer_id, None)

        if contact_id is not None:
            customer_id = _customer_for_contact(contact_id)
            if customer_id is None:
                return None
            return ("contact", contact_id, customer_id, contact_id)

        if operation.customer_id is not None:
            return ("customer", operation.customer_id, operation.customer_id, None)

        return None

    @staticmethod
    def _consent_activity_description(*, reason: ConsentReason, email: str) -> str:
        if reason == "spam_complaint":
            cause = "MailerSend spam complaint"
        else:
            cause = "MailerSend abonelikten çıkma (unsubscribe)"
        return (
            "E-posta iletişim izni otomatik kapatıldı.\n"
            f"Sebep: {cause}.\n"
            f"E-posta: {email}"
        )
