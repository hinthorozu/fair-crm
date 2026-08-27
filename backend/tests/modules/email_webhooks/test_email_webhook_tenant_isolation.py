"""Adversarial tenant-isolation tests for provider webhook ingress."""

import json
from datetime import UTC, datetime
from uuid import uuid4

from app.modules.email_accounts.infrastructure.persistence.models import (
    EmailAccountModel,
    EmailAccountProviderConfigModel,
)
from app.modules.email_webhooks.application.mailersend_signature import (
    compute_mailersend_signature,
)
from app.modules.mail_send_operations.infrastructure.persistence.models import (
    MailSendOperationModel,
)
from app.shared.secret_encryption import encrypt_secret


WEBHOOK_SECRET = "whsec_cross_org_isolation_test"


def test_mailersend_webhook_does_not_follow_foreign_organization_operation(
    client,
    db_session,
    organization_id,
    other_organization_id,
):
    """A valid ABC account signature must not mutate a cross-linked XYZ operation."""
    now = datetime.now(tz=UTC)
    account_id = uuid4()
    db_session.add(
        EmailAccountModel(
            id=account_id,
            organization_id=organization_id,
            name="ABC MailerSend",
            account_type="provider",
            provider_key="mailersend",
            from_email="abc@example.com",
            from_name="ABC",
            is_default=False,
            is_active=True,
            max_delivery_attempts=3,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.add(
        EmailAccountProviderConfigModel(
            email_account_id=account_id,
            provider_key="mailersend",
            config_json=json.dumps(
                {
                    "api_token": encrypt_secret("token"),
                    "webhook_signing_secret": encrypt_secret(WEBHOOK_SECRET),
                }
            ),
            error_policy_json="{}",
            created_at=now,
            updated_at=now,
        )
    )

    foreign_operation_id = uuid4()
    message_id = "foreign-operation-message"
    db_session.add(
        MailSendOperationModel(
            id=foreign_operation_id,
            organization_id=other_organization_id,
            source_type="fair_bulk_email",
            status="sent",
            priority=10,
            recipient_email="xyz@example.com",
            subject="XYZ message",
            email_account_id=account_id,
            retry_count=1,
            max_retry_count=3,
            operation_logs=[],
            external_message_id=message_id,
            provider_status="accepted",
            queued_at=now,
            sent_at=now,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()

    payload = {
        "type": "activity.delivered",
        "data": {
            "message_id": message_id,
            "email": "xyz@example.com",
        },
    }
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = compute_mailersend_signature(
        raw_body=body,
        signing_secret=WEBHOOK_SECRET,
    )

    response = client.post(
        f"/api/v1/webhooks/email/mailersend/{account_id}",
        content=body,
        headers={"Signature": signature},
    )
    assert response.status_code == 200

    db_session.expire_all()
    foreign_operation = db_session.get(MailSendOperationModel, foreign_operation_id)
    assert foreign_operation is not None
    assert foreign_operation.organization_id == other_organization_id
    assert foreign_operation.provider_status == "accepted"
