"""Process fair email batch background worker tests."""

from datetime import datetime, timezone
from unittest.mock import patch
from uuid import UUID, uuid4

from app.modules.fair_emails.application.commands import ProcessBatchCommand
from app.modules.fair_emails.application.process_batch import ProcessFairEmailBatchUseCase
from app.modules.fair_emails.infrastructure.persistence.models import FairEmailBatchModel, FairEmailOutboxModel
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from tests.conftest_customer_helpers import create_test_customer
from tests.modules.fair_emails.test_fair_bulk_email_api import (
    _create_contact,
    _create_fair,
    _create_participation,
    _create_smtp,
    _create_template,
)


def _seed_pending_batch(db_session, organization_id, user_id, client, auth_headers):
    fair_id = _create_fair(client, auth_headers)
    customer = create_test_customer(
        db_session,
        organization_id,
        display_name="ABC Fuarcılık",
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
    template_id = _create_template(client, auth_headers, key=f"process_batch_{fair_id[:8]}")
    smtp = _create_smtp(client, auth_headers)
    now = datetime.now(timezone.utc)
    batch_id = uuid4()
    batch = FairEmailBatchModel(
        id=batch_id,
        organization_id=organization_id,
        fair_id=UUID(fair_id),
        template_id=UUID(template_id),
        smtp_account_id=UUID(smtp.json()["id"]),
        subject_override="Fuar daveti",
        recipient_options_json={"include_customer_emails": True},
        status="queued",
        total_count=2,
        sent_count=0,
        failed_count=0,
        skipped_count=0,
        created_by_user_id=user_id,
        created_at=now,
        updated_at=now,
    )
    db_session.add(batch)
    for email, source, contact in (
        ("info@abc.com", "customer", None),
        ("ahmet@abc.com", "contact", UUID(contact_id)),
    ):
        db_session.add(
            FairEmailOutboxModel(
                id=uuid4(),
                batch_id=batch_id,
                organization_id=organization_id,
                customer_id=customer.id,
                contact_id=contact,
                participation_id=UUID(participation["id"]),
                recipient_name="Test Recipient",
                company_name="ABC Fuarcılık",
                email=email,
                source=source,
                status="pending",
                created_at=now,
                updated_at=now,
            )
        )
    db_session.commit()
    return batch_id


@patch("app.modules.fair_emails.application.process_batch.send_smtp_message")
def test_process_batch_inactive_smtp_fails_all_items(
    mock_send,
    db_session,
    client,
    auth_headers,
    organization_id,
    user_id,
):
    from app.modules.smtp.infrastructure.persistence.models import SmtpAccountModel

    batch_id = _seed_pending_batch(db_session, organization_id, user_id, client, auth_headers)
    batch = db_session.query(FairEmailBatchModel).filter(FairEmailBatchModel.id == batch_id).one()
    smtp = db_session.query(SmtpAccountModel).filter(SmtpAccountModel.id == batch.smtp_account_id).one()
    smtp.is_active = False
    db_session.commit()

    ProcessFairEmailBatchUseCase(db_session).execute(
        ProcessBatchCommand(batch_id=batch_id, organization_id=organization_id)
    )

    db_session.expire_all()
    batch = db_session.query(FairEmailBatchModel).filter(FairEmailBatchModel.id == batch_id).one()
    outbox = db_session.query(FairEmailOutboxModel).filter(FairEmailOutboxModel.batch_id == batch_id).all()
    assert batch.status == "failed"
    assert batch.failed_count == 2
    assert all(item.status == "failed" for item in outbox)
    assert all(item.status != "pending" for item in outbox)
    mock_send.assert_not_called()


@patch("app.modules.fair_emails.application.process_batch.send_smtp_message")
def test_process_batch_marks_items_sent(mock_send, db_session, client, auth_headers, organization_id, user_id):
    batch_id = _seed_pending_batch(db_session, organization_id, user_id, client, auth_headers)

    ProcessFairEmailBatchUseCase(db_session).execute(
        ProcessBatchCommand(batch_id=batch_id, organization_id=organization_id)
    )

    batch = db_session.query(FairEmailBatchModel).filter(FairEmailBatchModel.id == batch_id).one()
    outbox = db_session.query(FairEmailOutboxModel).filter(FairEmailOutboxModel.batch_id == batch_id).all()
    assert batch.status == "completed"
    assert batch.sent_count == 2
    assert batch.failed_count == 0
    assert all(item.status == "sent" for item in outbox)
    assert all(item.sent_at is not None for item in outbox)
    assert mock_send.call_count == 2


@patch("app.modules.fair_emails.application.process_batch.send_smtp_message")
def test_process_batch_marks_smtp_failure(mock_send, db_session, client, auth_headers, organization_id, user_id):
    mock_send.side_effect = SmtpMailDeliveryError("Authentication failed")
    batch_id = _seed_pending_batch(db_session, organization_id, user_id, client, auth_headers)

    ProcessFairEmailBatchUseCase(db_session).execute(
        ProcessBatchCommand(batch_id=batch_id, organization_id=organization_id)
    )

    batch = db_session.query(FairEmailBatchModel).filter(FairEmailBatchModel.id == batch_id).one()
    outbox = db_session.query(FairEmailOutboxModel).filter(FairEmailOutboxModel.batch_id == batch_id).all()
    assert batch.status == "completed_with_errors"
    assert batch.sent_count == 0
    assert batch.failed_count == 2
    assert all(item.status == "failed" for item in outbox)
    assert all(item.error_message == "Authentication failed" for item in outbox)


@patch("app.modules.fair_emails.application.process_batch.send_smtp_message")
def test_process_batch_exception_does_not_leave_items_queued(
    mock_send,
    db_session,
    client,
    auth_headers,
    organization_id,
    user_id,
):
    mock_send.side_effect = RuntimeError("unexpected processor failure")
    batch_id = _seed_pending_batch(db_session, organization_id, user_id, client, auth_headers)

    ProcessFairEmailBatchUseCase(db_session).execute(
        ProcessBatchCommand(batch_id=batch_id, organization_id=organization_id)
    )

    db_session.expire_all()
    batch = db_session.query(FairEmailBatchModel).filter(FairEmailBatchModel.id == batch_id).one()
    outbox = db_session.query(FairEmailOutboxModel).filter(FairEmailOutboxModel.batch_id == batch_id).all()
    assert batch.status == "completed_with_errors"
    assert batch.failed_count == 2
    assert all(item.status == "failed" for item in outbox)
    assert all(item.status != "pending" for item in outbox)


@patch("app.modules.fair_emails.application.process_batch.send_smtp_message")
def test_send_then_background_processor_updates_outbox(
    mock_send,
    client,
    auth_headers,
    db_session,
    organization_id,
):
    from tests.modules.fair_emails.test_fair_bulk_email_api import _setup_fair_with_recipients

    data = _setup_fair_with_recipients(client, auth_headers, db_session, organization_id)
    response = client.post(
        f"/api/v1/fairs/{data['fair_id']}/bulk-email/send",
        json={
            "template_id": data["template_id"],
            "subject_override": "Fuar daveti",
            "recipient_options": {"include_customer_emails": True, "include_contact_emails": True},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    batch_id = response.json()["batch_id"]

    batch = db_session.query(FairEmailBatchModel).filter(FairEmailBatchModel.id == UUID(batch_id)).one()
    outbox = db_session.query(FairEmailOutboxModel).filter(FairEmailOutboxModel.batch_id == UUID(batch_id)).all()
    assert batch.status == "completed"
    assert batch.sent_count >= 1
    assert all(item.status == "sent" for item in outbox)
    assert mock_send.call_count >= 1
