"""Tests for fair bulk email customer activity logging."""

from datetime import datetime, timezone
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

from app.modules.activities.domain.value_objects import ActivitySource, ActivityStatus, ActivityType
from app.modules.activities.infrastructure.persistence.models import ActivityModel
from app.modules.fair_emails.application.commands import ProcessBatchCommand
from app.modules.fair_emails.application.fair_bulk_email_activity import (
    FairBulkEmailActivityContext,
    FairBulkEmailActivityWriter,
    build_fair_bulk_email_activity_note,
    sanitize_error_message,
)
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
from tests.modules.fair_emails.test_process_fair_email_batch import _seed_pending_batch


def _activities_for_customer(db_session, organization_id, customer_id):
    return (
        db_session.query(ActivityModel)
        .filter(
            ActivityModel.organization_id == organization_id,
            ActivityModel.customer_id == customer_id,
            ActivityModel.deleted_at.is_(None),
        )
        .order_by(ActivityModel.created_at.asc())
        .all()
    )


@patch("app.modules.fair_emails.application.process_batch.send_smtp_message")
def test_sent_outbox_item_creates_customer_activity(
    mock_send,
    db_session,
    client,
    auth_headers,
    organization_id,
    user_id,
):
    batch_id = _seed_pending_batch(db_session, organization_id, user_id, client, auth_headers)
    customer = db_session.query(FairEmailOutboxModel).filter(FairEmailOutboxModel.batch_id == batch_id).first()
    customer_id = customer.customer_id

    ProcessFairEmailBatchUseCase(db_session).execute(
        ProcessBatchCommand(batch_id=batch_id, organization_id=organization_id)
    )

    activities = _activities_for_customer(db_session, organization_id, customer_id)
    assert len(activities) == 2
    assert all(item.activity_type == ActivityType.EMAIL for item in activities)
    assert all(item.source == ActivitySource.EMAIL_AUTOMATION for item in activities)
    assert all(item.status == ActivityStatus.COMPLETED for item in activities)
    assert all("Fuar toplu mail gönderildi" in (item.description or "") for item in activities)
    assert all(item.metadata_json and item.metadata_json.get("status") == "sent" for item in activities)


@patch("app.modules.fair_emails.application.process_batch.send_smtp_message")
def test_failed_outbox_item_creates_customer_activity(
    mock_send,
    db_session,
    client,
    auth_headers,
    organization_id,
    user_id,
):
    mock_send.side_effect = SmtpMailDeliveryError("Authentication failed")
    batch_id = _seed_pending_batch(db_session, organization_id, user_id, client, auth_headers)
    customer_id = (
        db_session.query(FairEmailOutboxModel)
        .filter(FairEmailOutboxModel.batch_id == batch_id)
        .first()
        .customer_id
    )

    ProcessFairEmailBatchUseCase(db_session).execute(
        ProcessBatchCommand(batch_id=batch_id, organization_id=organization_id)
    )

    activities = _activities_for_customer(db_session, organization_id, customer_id)
    assert len(activities) == 2
    assert all(item.status == ActivityStatus.CANCELLED for item in activities)
    assert all("başarısız oldu" in (item.description or "") for item in activities)
    assert all("Authentication failed" in (item.description or "") for item in activities)
    assert all(item.metadata_json and item.metadata_json.get("status") == "failed" for item in activities)


@patch("app.modules.fair_emails.application.process_batch.send_smtp_message")
def test_contact_recipient_activity_links_contact_id(
    mock_send,
    db_session,
    client,
    auth_headers,
    organization_id,
    user_id,
):
    batch_id = _seed_pending_batch(db_session, organization_id, user_id, client, auth_headers)
    contact_outbox = (
        db_session.query(FairEmailOutboxModel)
        .filter(FairEmailOutboxModel.batch_id == batch_id, FairEmailOutboxModel.source == "contact")
        .one()
    )

    ProcessFairEmailBatchUseCase(db_session).execute(
        ProcessBatchCommand(batch_id=batch_id, organization_id=organization_id)
    )

    activity = (
        db_session.query(ActivityModel)
        .filter(
            ActivityModel.organization_id == organization_id,
            ActivityModel.metadata_json["outbox_id"].as_string() == str(contact_outbox.id),
        )
        .one()
    )
    assert activity.customer_id == contact_outbox.customer_id
    assert activity.contact_id == contact_outbox.contact_id
    assert activity.metadata_json["recipient_source"] == "contact"
    assert activity.metadata_json["contact_id"] == str(contact_outbox.contact_id)


@patch("app.modules.fair_emails.application.process_batch.send_smtp_message")
def test_customer_recipient_activity_has_no_contact_id(
    mock_send,
    db_session,
    client,
    auth_headers,
    organization_id,
    user_id,
):
    batch_id = _seed_pending_batch(db_session, organization_id, user_id, client, auth_headers)
    customer_outbox = (
        db_session.query(FairEmailOutboxModel)
        .filter(FairEmailOutboxModel.batch_id == batch_id, FairEmailOutboxModel.source == "customer")
        .one()
    )

    ProcessFairEmailBatchUseCase(db_session).execute(
        ProcessBatchCommand(batch_id=batch_id, organization_id=organization_id)
    )

    activity = (
        db_session.query(ActivityModel)
        .filter(
            ActivityModel.organization_id == organization_id,
            ActivityModel.metadata_json["outbox_id"].as_string() == str(customer_outbox.id),
        )
        .one()
    )
    assert activity.customer_id == customer_outbox.customer_id
    assert activity.contact_id is None
    assert activity.metadata_json["recipient_source"] == "customer"
    assert "contact_id" not in activity.metadata_json


@patch("app.modules.fair_emails.application.process_batch.send_smtp_message")
def test_pending_outbox_does_not_create_activity(
    mock_send,
    db_session,
    client,
    auth_headers,
    organization_id,
    user_id,
):
    batch_id = _seed_pending_batch(db_session, organization_id, user_id, client, auth_headers)
    customer_id = (
        db_session.query(FairEmailOutboxModel)
        .filter(FairEmailOutboxModel.batch_id == batch_id)
        .first()
        .customer_id
    )

    assert _activities_for_customer(db_session, organization_id, customer_id) == []


@patch("app.modules.fair_emails.application.process_batch.send_smtp_message")
def test_processor_rerun_does_not_duplicate_activities(
    mock_send,
    db_session,
    client,
    auth_headers,
    organization_id,
    user_id,
):
    batch_id = _seed_pending_batch(db_session, organization_id, user_id, client, auth_headers)
    customer_id = (
        db_session.query(FairEmailOutboxModel)
        .filter(FairEmailOutboxModel.batch_id == batch_id)
        .first()
        .customer_id
    )
    command = ProcessBatchCommand(batch_id=batch_id, organization_id=organization_id)

    ProcessFairEmailBatchUseCase(db_session).execute(command)
    ProcessFairEmailBatchUseCase(db_session).execute(command)

    activities = _activities_for_customer(db_session, organization_id, customer_id)
    assert len(activities) == 2


@patch("app.modules.fair_emails.application.process_batch.send_smtp_message")
def test_activity_note_contains_fair_template_subject_recipient(
    mock_send,
    db_session,
    client,
    auth_headers,
    organization_id,
    user_id,
):
    batch_id = _seed_pending_batch(db_session, organization_id, user_id, client, auth_headers)

    ProcessFairEmailBatchUseCase(db_session).execute(
        ProcessBatchCommand(batch_id=batch_id, organization_id=organization_id)
    )

    activity = _activities_for_customer(
        db_session,
        organization_id,
        db_session.query(FairEmailOutboxModel).filter(FairEmailOutboxModel.batch_id == batch_id).first().customer_id,
    )[0]
    description = activity.description or ""
    assert "Fuar:" in description
    assert "Şablon:" in description
    assert "Konu:" in description
    assert "Alıcı:" in description
    assert "info@abc.com" in description


def test_sanitize_error_message_redacts_secrets():
    assert sanitize_error_message("SMTP password decrypt failed") == "Mail gönderimi sırasında bir hata oluştu."
    assert sanitize_error_message("Authentication failed") == "Authentication failed"


def test_activity_writer_is_idempotent(db_session, organization_id, user_id, client, auth_headers):
    batch_id = _seed_pending_batch(db_session, organization_id, user_id, client, auth_headers)
    batch = db_session.query(FairEmailBatchModel).filter(FairEmailBatchModel.id == batch_id).one()
    outbox = (
        db_session.query(FairEmailOutboxModel)
        .filter(FairEmailOutboxModel.batch_id == batch_id)
        .first()
    )
    outbox.status = "sent"
    db_session.commit()

    writer = FairBulkEmailActivityWriter(db_session)
    context = FairBulkEmailActivityContext(
        organization_id=organization_id,
        batch=batch,
        outbox=outbox,
        fair_name="Test Fuar",
        template_name="Davet",
        subject="Fuar daveti",
        terminal_status="sent",
    )
    writer.record_terminal_outbox(context)
    writer.record_terminal_outbox(context)
    db_session.commit()

    count = (
        db_session.query(ActivityModel)
        .filter(
            ActivityModel.organization_id == organization_id,
            ActivityModel.metadata_json["outbox_id"].as_string() == str(outbox.id),
        )
        .count()
    )
    assert count == 1


def test_activity_writer_respects_tenant_isolation(db_session, organization_id, other_organization_id, user_id, client, auth_headers):
    batch_id = _seed_pending_batch(db_session, organization_id, user_id, client, auth_headers)
    batch = db_session.query(FairEmailBatchModel).filter(FairEmailBatchModel.id == batch_id).one()
    outbox = (
        db_session.query(FairEmailOutboxModel)
        .filter(FairEmailOutboxModel.batch_id == batch_id)
        .first()
    )
    outbox.status = "failed"
    outbox.error_message = "SMTP error"
    db_session.commit()

    writer = FairBulkEmailActivityWriter(db_session)
    writer.record_terminal_outbox(
        FairBulkEmailActivityContext(
            organization_id=other_organization_id,
            batch=batch,
            outbox=outbox,
            fair_name="Test Fuar",
            template_name="Davet",
            subject="Fuar daveti",
            terminal_status="failed",
            error_message="SMTP error",
        )
    )
    db_session.commit()

    assert (
        db_session.query(ActivityModel)
        .filter(ActivityModel.organization_id == other_organization_id)
        .count()
        == 0
    )


def test_build_failed_note_includes_error_message():
    note = build_fair_bulk_email_activity_note(
        terminal_status="failed",
        fair_name="Fuar A",
        template_name="Şablon B",
        subject="Konu C",
        recipient_email="a@example.com",
        recipient_source="customer",
        error_message="Authentication failed",
    )
    assert "Hata: Authentication failed" in note
