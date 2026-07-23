"""Tests for operations bulk_email send core (nullable fair/CRM + attempt activities)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.modules.activities.infrastructure.persistence.models import ActivityModel
from app.modules.fair_emails.application.commands import ProcessBatchCommand
from app.modules.fair_emails.application.fair_bulk_email_activity import (
    FairBulkEmailActivityContext,
    FairBulkEmailActivityWriter,
)
from app.modules.fair_emails.application.process_batch import ProcessFairEmailBatchUseCase
from app.modules.fair_emails.application.recipient_resolution import wizard_to_resolved_recipient
from app.modules.fair_emails.application.send_bulk_email_operation import (
    SendBulkEmailOperationCommand,
    SendBulkEmailOperationUseCase,
)
from app.modules.fair_emails.domain.value_objects import RecipientOptions, WizardPreviewRecipient
from app.modules.fair_emails.infrastructure.persistence.models import (
    FairEmailBatchModel,
    FairEmailOutboxModel,
)
from app.modules.fair_emails.infrastructure.repositories.fair_email_batch_repository import (
    FairEmailBatchRecord,
    SqlAlchemyFairEmailBatchRepository,
)
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from tests.conftest_customer_helpers import create_test_customer
from tests.modules.fair_emails.test_fair_bulk_email_api import (
    _create_contact,
    _create_fair,
    _create_participation,
    _create_smtp,
    _create_template,
)


def _auth_ok():
    auth = MagicMock()
    auth.check_permission.return_value = True
    return auth


def test_manual_send_creates_batch_with_null_fair_and_crm_ids(
    db_session,
    client,
    auth_headers,
    organization_id,
    user_id,
):
    template_id = _create_template(client, auth_headers, key=f"ops_manual_{uuid4().hex[:8]}")
    smtp = _create_smtp(client, auth_headers)
    smtp_id = UUID(smtp.json()["id"])

    from app.modules.fair_emails.application.fair_bulk_mail_operation_sync import (
        FairBulkEmailMailOperationSync,
    )
    from app.modules.fair_emails.application.recipient_service import FairBulkEmailRecipientService
    from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
    from app.modules.mail_templates.infrastructure.repositories.mail_template_repository import (
        SqlAlchemyMailTemplateRepository,
    )
    from app.modules.smtp.infrastructure.repositories.smtp_account_repository import (
        SqlAlchemySmtpAccountRepository,
    )

    use_case = SendBulkEmailOperationUseCase(
        SqlAlchemyFairRepository(db_session),
        SqlAlchemyMailTemplateRepository(db_session),
        SqlAlchemySmtpAccountRepository(db_session),
        SqlAlchemyFairEmailBatchRepository(db_session),
        FairBulkEmailRecipientService(db_session),
        FairBulkEmailMailOperationSync(db_session),
        _auth_ok(),
    )
    result = use_case.execute(
        SendBulkEmailOperationCommand(
            organization_id=organization_id,
            user_id=user_id,
            access_token="token",
            source_type="manual",
            template_id=UUID(template_id),
            smtp_account_id=smtp_id,
            subject="Merhaba",
            manual_emails="one@example.com;two@example.com",
        )
    )
    db_session.commit()

    batch = db_session.query(FairEmailBatchModel).filter(FairEmailBatchModel.id == result.batch_id).one()
    assert batch.fair_id is None
    assert batch.recipient_options_json.get("source_type") == "manual"
    outbox = (
        db_session.query(FairEmailOutboxModel)
        .filter(FairEmailOutboxModel.batch_id == batch.id)
        .order_by(FairEmailOutboxModel.email.asc())
        .all()
    )
    assert len(outbox) == 2
    assert all(row.customer_id is None for row in outbox)
    assert all(row.participation_id is None for row in outbox)
    assert all(row.send_attempt == 1 for row in outbox)
    assert {row.source for row in outbox} == {"manual"}


def test_crm_less_manual_creates_no_activity(db_session, organization_id):
    now = datetime.now(timezone.utc)
    batch_id = uuid4()
    outbox_id = uuid4()
    batch = FairEmailBatchRecord(
        id=batch_id,
        organization_id=organization_id,
        fair_id=None,
        template_id=uuid4(),
        smtp_account_id=None,
        subject_override="Konu",
        status="processing",
        total_count=1,
        sent_count=1,
        failed_count=0,
        skipped_count=0,
        operation_id=None,
    )
    outbox = FairEmailOutboxModel(
        id=outbox_id,
        batch_id=batch_id,
        organization_id=organization_id,
        customer_id=None,
        contact_id=None,
        participation_id=None,
        recipient_name=None,
        company_name="one@example.com",
        email="one@example.com",
        source="manual",
        status="sent",
        send_attempt=1,
        sent_at=now,
        created_at=now,
        updated_at=now,
    )
    FairBulkEmailActivityWriter(db_session).record_terminal_outbox(
        FairBulkEmailActivityContext(
            organization_id=organization_id,
            batch=batch,
            outbox=outbox,
            fair_name="",
            template_name="T",
            subject="Konu",
            terminal_status="sent",
        )
    )
    db_session.commit()
    assert (
        db_session.query(ActivityModel)
        .filter(ActivityModel.organization_id == organization_id)
        .count()
        == 0
    )


def test_crm_recipient_creates_activity_and_retry_creates_second_attempt(
    db_session,
    client,
    auth_headers,
    organization_id,
    user_id,
):
    fair_id = _create_fair(client, auth_headers)
    customer = create_test_customer(
        db_session,
        organization_id,
        display_name="ABC",
        email="info@abc.com",
    )
    db_session.commit()
    contact_id = _create_contact(client, auth_headers, str(customer.id))
    participation = _create_participation(
        client,
        auth_headers,
        fair_id,
        str(customer.id),
        primary_contact_id=contact_id,
    )
    template_id = _create_template(client, auth_headers, key=f"ops_retry_{uuid4().hex[:8]}")
    smtp = _create_smtp(client, auth_headers)
    now = datetime.now(timezone.utc)
    batch_id = uuid4()
    outbox_id = uuid4()
    db_session.add(
        FairEmailBatchModel(
            id=batch_id,
            organization_id=organization_id,
            fair_id=UUID(fair_id),
            template_id=UUID(template_id),
            smtp_account_id=UUID(smtp.json()["id"]),
            subject_override="Konu",
            recipient_options_json={},
            status="queued",
            total_count=1,
            sent_count=0,
            failed_count=0,
            skipped_count=0,
            created_by_user_id=user_id,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.add(
        FairEmailOutboxModel(
            id=outbox_id,
            batch_id=batch_id,
            organization_id=organization_id,
            customer_id=customer.id,
            contact_id=None,
            participation_id=UUID(participation["id"]),
            recipient_name="ABC",
            company_name="ABC",
            email="info@abc.com",
            source="customer",
            status="pending",
            send_attempt=1,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()

    with patch(
        "app.modules.fair_emails.application.process_batch.send_smtp_message",
        side_effect=SmtpMailDeliveryError("boom"),
    ):
        ProcessFairEmailBatchUseCase(db_session).execute(
            ProcessBatchCommand(batch_id=batch_id, organization_id=organization_id)
        )

    activities = (
        db_session.query(ActivityModel)
        .filter(
            ActivityModel.organization_id == organization_id,
            ActivityModel.customer_id == customer.id,
        )
        .all()
    )
    assert len(activities) == 1
    assert activities[0].metadata_json["send_attempt"] == "1"
    assert activities[0].metadata_json["status"] == "failed"

    repo = SqlAlchemyFairEmailBatchRepository(db_session)
    repo.prepare_outbox_for_retry(outbox_id)
    db_session.commit()
    outbox = db_session.query(FairEmailOutboxModel).filter(FairEmailOutboxModel.id == outbox_id).one()
    assert outbox.status == "pending"
    assert outbox.send_attempt == 2

    with patch("app.modules.fair_emails.application.process_batch.send_smtp_message"):
        ProcessFairEmailBatchUseCase(db_session).execute(
            ProcessBatchCommand(batch_id=batch_id, organization_id=organization_id)
        )

    activities = (
        db_session.query(ActivityModel)
        .filter(
            ActivityModel.organization_id == organization_id,
            ActivityModel.customer_id == customer.id,
        )
        .order_by(ActivityModel.created_at.asc())
        .all()
    )
    assert len(activities) == 2
    attempts = {item.metadata_json.get("send_attempt") for item in activities}
    assert attempts == {"1", "2"}
    assert activities[1].metadata_json["status"] == "sent"


def test_prepare_outbox_for_retry_rejects_sent(db_session, organization_id, user_id):
    now = datetime.now(timezone.utc)
    batch_id = uuid4()
    outbox_id = uuid4()
    db_session.add(
        FairEmailBatchModel(
            id=batch_id,
            organization_id=organization_id,
            fair_id=None,
            template_id=uuid4(),
            smtp_account_id=None,
            subject_override=None,
            recipient_options_json={},
            status="completed",
            total_count=1,
            sent_count=1,
            failed_count=0,
            skipped_count=0,
            created_by_user_id=user_id,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.add(
        FairEmailOutboxModel(
            id=outbox_id,
            batch_id=batch_id,
            organization_id=organization_id,
            customer_id=None,
            contact_id=None,
            participation_id=None,
            recipient_name=None,
            company_name="a@example.com",
            email="a@example.com",
            source="manual",
            status="sent",
            send_attempt=1,
            sent_at=now,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()
    repo = SqlAlchemyFairEmailBatchRepository(db_session)
    with pytest.raises(ValueError, match="Only failed"):
        repo.prepare_outbox_for_retry(outbox_id)


def test_retry_only_failed_not_sent(db_session, organization_id, user_id):
    now = datetime.now(timezone.utc)
    batch_id = uuid4()
    sent_id = uuid4()
    failed_id = uuid4()
    db_session.add(
        FairEmailBatchModel(
            id=batch_id,
            organization_id=organization_id,
            fair_id=None,
            template_id=uuid4(),
            smtp_account_id=None,
            subject_override=None,
            recipient_options_json={},
            status="completed_with_errors",
            total_count=2,
            sent_count=1,
            failed_count=1,
            skipped_count=0,
            created_by_user_id=user_id,
            created_at=now,
            updated_at=now,
        )
    )
    for oid, email, status in (
        (sent_id, "sent@example.com", "sent"),
        (failed_id, "fail@example.com", "failed"),
    ):
        db_session.add(
            FairEmailOutboxModel(
                id=oid,
                batch_id=batch_id,
                organization_id=organization_id,
                customer_id=None,
                contact_id=None,
                participation_id=None,
                recipient_name=None,
                company_name=email,
                email=email,
                source="manual",
                status=status,
                send_attempt=1,
                error_message="x" if status == "failed" else None,
                sent_at=now if status == "sent" else None,
                created_at=now,
                updated_at=now,
            )
        )
    db_session.commit()

    repo = SqlAlchemyFairEmailBatchRepository(db_session)
    failed = repo.list_failed_outbox(batch_id)
    assert len(failed) == 1
    assert failed[0].id == failed_id
    for item in failed:
        repo.prepare_outbox_for_retry(item.id)
    db_session.commit()

    sent = db_session.query(FairEmailOutboxModel).filter(FairEmailOutboxModel.id == sent_id).one()
    retried = db_session.query(FairEmailOutboxModel).filter(FairEmailOutboxModel.id == failed_id).one()
    assert sent.status == "sent"
    assert sent.send_attempt == 1
    assert retried.status == "pending"
    assert retried.send_attempt == 2


def test_wizard_to_resolved_allows_null_crm_ids():
    wizard = WizardPreviewRecipient(
        recipient_key="manual:none:a@example.com",
        email="a@example.com",
        source="manual",
        status="will_send",
        skip_reason=None,
    )
    resolved = wizard_to_resolved_recipient(wizard)
    assert resolved.customer_id is None
    assert resolved.participation_id is None
    assert resolved.company_name == "a@example.com"
    assert resolved.source == "manual"


def test_preview_still_creates_no_batch(
    db_session,
    client,
    auth_headers,
    organization_id,
):
    template_id = _create_template(client, auth_headers, key=f"ops_preview_{uuid4().hex[:8]}")
    smtp = _create_smtp(client, auth_headers)
    before = db_session.query(FairEmailBatchModel).count()
    response = client.post(
        "/api/v1/operations/bulk-email/preview",
        headers=auth_headers,
        data={
            "payload": (
                '{"source_type":"manual","template_id":"%s","smtp_account_id":"%s",'
                '"manual_emails":"preview@example.com"}'
                % (template_id, smtp.json()["id"])
            )
        },
    )
    assert response.status_code == 200, response.text
    assert db_session.query(FairEmailBatchModel).count() == before
