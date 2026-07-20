"""Manual task mail queue API tests."""

from unittest.mock import patch

import pytest

from app.modules.mail_send_operations.domain.value_objects import MailSendOperationStatus, MailSendSourceType
from app.modules.mail_send_operations.infrastructure.persistence.models import MailSendOperationModel
from app.modules.todos.application.send_manual_task_mail import parse_manual_task_mail_recipients
from app.modules.todos.domain.exceptions import InvalidManualTaskMailRecipientsError
from tests.modules.todos.test_todo_worklist_api import WORKLIST_BASE, _seed_worklist_scenario


def _create_smtp_account(client, auth_headers, **overrides):
    payload = {
        "name": "Manual Task SMTP",
        "from_email": "noreply@example.com",
        "host": "smtp.example.com",
        "port": 587,
        "username": "smtp-user",
        "password": "secret-password",
        "encryption_type": "starttls",
        "is_default": True,
        "is_active": True,
    }
    payload.update(overrides)
    return client.post("/api/v1/smtp/accounts", json=payload, headers=auth_headers)


def _create_mail_template(client, auth_headers, **overrides):
    payload = {
        "name": "Task Invite",
        "key": "task_invite",
        "subject": "Template Subject",
        "body_html": "<p>Template Body</p>",
        "body_text": "Template Body",
        "template_type": "transactional",
        "language": "tr",
        "is_active": True,
        "is_default": False,
    }
    payload.update(overrides)
    return client.post("/api/v1/mail-templates", json=payload, headers=auth_headers)


def test_parse_manual_task_mail_recipients_dedupes_and_validates():
    assert parse_manual_task_mail_recipients("abc@abc.com; def@def.com; abc@abc.com;") == [
        "abc@abc.com",
        "def@def.com",
    ]
    with pytest.raises(InvalidManualTaskMailRecipientsError, match="Geçersiz e-posta adresi: abc @\\.oxom"):
        parse_manual_task_mail_recipients("abc @.oxom")


@patch("app.modules.todos.api.worklist_routes.process_mail_send_operations_background")
def test_send_manual_task_mail_queues_one_operation_per_recipient(
    mock_worker, client, auth_headers, db_session, organization_id, user_id
):
    scenario = _seed_worklist_scenario(db_session, organization_id, user_id)
    todo_id = scenario["todo_id"]
    customer_id = str(scenario["customers"]["alpha"].id)

    smtp = _create_smtp_account(client, auth_headers)
    assert smtp.status_code == 201
    smtp_id = smtp.json()["id"]

    template = _create_mail_template(client, auth_headers, key="manual_task_tpl")
    assert template.status_code == 201
    template_id = template.json()["id"]

    response = client.post(
        f"{WORKLIST_BASE.format(todo_id=todo_id)}/customers/{customer_id}/manual-mail",
        headers=auth_headers,
        json={
            "todo_id": todo_id,
            "customer_id": customer_id,
            "smtp_account_id": smtp_id,
            "template_id": template_id,
            "recipients": "one@example.com; two@example.com; one@example.com;",
            "subject": "Final Subject From UI",
            "body": "<p>Final Body From UI</p>",
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert body["queued_count"] == 2
    assert body["message"] == "Mail gönderimleri kuyruğa alındı."
    assert len(body["operation_ids"]) == 2
    mock_worker.assert_called_once()

    operations = (
        db_session.query(MailSendOperationModel)
        .filter(MailSendOperationModel.source_type == MailSendSourceType.MANUAL_TASK_MAIL)
        .order_by(MailSendOperationModel.recipient_email.asc())
        .all()
    )
    assert len(operations) == 2
    assert {op.recipient_email for op in operations} == {"one@example.com", "two@example.com"}
    for op in operations:
        assert op.status == MailSendOperationStatus.QUEUED
        assert op.subject == "Final Subject From UI"
        assert op.body_html == "<p>Final Body From UI</p>"
        assert op.body_text == "<p>Final Body From UI</p>"
        assert op.smtp_account_id is not None
        assert str(op.smtp_account_id) == smtp_id
        assert str(op.template_id) == template_id
        assert str(op.customer_id) == customer_id
        assert op.metadata_json["source"] == "manual_task_mail"
        assert op.metadata_json["todo_id"] == todo_id
        assert op.metadata_json["customer_id"] == customer_id
        assert op.metadata_json["recipient"] == op.recipient_email
        assert op.metadata_json["smtp_account_id"] == smtp_id
        assert op.metadata_json["template_id"] == template_id
        events = [entry["event"] for entry in (op.operation_logs or [])]
        assert events == ["queued"]


@patch("app.modules.todos.api.worklist_routes.process_mail_send_operations_background")
def test_send_manual_task_mail_does_not_require_template(
    mock_worker, client, auth_headers, db_session, organization_id, user_id
):
    scenario = _seed_worklist_scenario(db_session, organization_id, user_id)
    todo_id = scenario["todo_id"]
    customer_id = str(scenario["customers"]["alpha"].id)
    smtp = _create_smtp_account(client, auth_headers, name="No Template SMTP")
    assert smtp.status_code == 201

    response = client.post(
        f"{WORKLIST_BASE.format(todo_id=todo_id)}/customers/{customer_id}/manual-mail",
        headers=auth_headers,
        json={
            "smtp_account_id": smtp.json()["id"],
            "recipients": "solo@example.com",
            "subject": "Plain subject",
            "body": "Plain body text",
        },
    )
    assert response.status_code == 202
    assert response.json()["queued_count"] == 1
    mock_worker.assert_called_once()

    operation = (
        db_session.query(MailSendOperationModel)
        .filter(MailSendOperationModel.recipient_email == "solo@example.com")
        .one()
    )
    assert operation.template_id is None
    assert operation.body_html is None
    assert operation.body_text == "Plain body text"
    assert "template_id" not in (operation.metadata_json or {})


@patch("app.modules.mail_send_operations.application.mail_send_operation_dispatcher.send_smtp_message")
def test_send_manual_task_mail_background_worker_moves_to_sent(
    mock_send, client, auth_headers, db_session, organization_id, user_id
):
    scenario = _seed_worklist_scenario(db_session, organization_id, user_id)
    todo_id = scenario["todo_id"]
    customer_id = str(scenario["customers"]["alpha"].id)
    smtp = _create_smtp_account(client, auth_headers, name="Background SMTP")
    assert smtp.status_code == 201

    response = client.post(
        f"{WORKLIST_BASE.format(todo_id=todo_id)}/customers/{customer_id}/manual-mail",
        headers=auth_headers,
        json={
            "smtp_account_id": smtp.json()["id"],
            "recipients": "worker-seen@example.com; worker-seen-2@example.com",
            "subject": "Worker subject",
            "body": "Worker body",
        },
    )
    assert response.status_code == 202
    assert len(response.json()["operation_ids"]) == 2

    operations = (
        db_session.query(MailSendOperationModel)
        .filter(MailSendOperationModel.source_type == MailSendSourceType.MANUAL_TASK_MAIL)
        .order_by(MailSendOperationModel.recipient_email.asc())
        .all()
    )
    assert len(operations) == 2
    for op in operations:
        assert op.status == MailSendOperationStatus.SENT
        events = [entry["event"] for entry in (op.operation_logs or [])]
        assert "picked_by_worker" in events
        assert "sending_started" in events
        assert events[-1] == "sent"
        assert op.error_code is None
    assert mock_send.call_count == 2


def test_send_manual_task_mail_rejects_invalid_recipients(
    client, auth_headers, db_session, organization_id, user_id
):
    scenario = _seed_worklist_scenario(db_session, organization_id, user_id)
    todo_id = scenario["todo_id"]
    customer_id = str(scenario["customers"]["alpha"].id)
    smtp = _create_smtp_account(client, auth_headers, name="Invalid Recipients SMTP")
    assert smtp.status_code == 201
    smtp_id = smtp.json()["id"]

    invalid_cases = [
        "abc @.oxom",
        "abc@.com",
        "abc@domain",
    ]
    for recipients in invalid_cases:
        before = db_session.query(MailSendOperationModel).count()
        response = client.post(
            f"{WORKLIST_BASE.format(todo_id=todo_id)}/customers/{customer_id}/manual-mail",
            headers=auth_headers,
            json={
                "smtp_account_id": smtp_id,
                "recipients": recipients,
                "subject": "Subject",
                "body": "Body",
            },
        )
        assert response.status_code == 422, recipients
        detail = response.json()["detail"]
        assert "Geçersiz e-posta adresi:" in detail
        assert recipients in detail
        assert db_session.query(MailSendOperationModel).count() == before

    mixed = client.post(
        f"{WORKLIST_BASE.format(todo_id=todo_id)}/customers/{customer_id}/manual-mail",
        headers=auth_headers,
        json={
            "smtp_account_id": smtp_id,
            "recipients": "abc@example.com; abc @.oxom",
            "subject": "Subject",
            "body": "Body",
        },
    )
    assert mixed.status_code == 422
    assert "abc @.oxom" in mixed.json()["detail"]
    assert (
        db_session.query(MailSendOperationModel)
        .filter(MailSendOperationModel.source_type == MailSendSourceType.MANUAL_TASK_MAIL)
        .count()
        == 0
    )


@patch("app.modules.todos.api.worklist_routes.process_mail_send_operations_background")
def test_send_manual_task_mail_accepts_valid_recipient(
    mock_worker, client, auth_headers, db_session, organization_id, user_id
):
    scenario = _seed_worklist_scenario(db_session, organization_id, user_id)
    todo_id = scenario["todo_id"]
    customer_id = str(scenario["customers"]["alpha"].id)
    smtp = _create_smtp_account(client, auth_headers, name="Valid Recipient SMTP")
    assert smtp.status_code == 201

    response = client.post(
        f"{WORKLIST_BASE.format(todo_id=todo_id)}/customers/{customer_id}/manual-mail",
        headers=auth_headers,
        json={
            "smtp_account_id": smtp.json()["id"],
            "recipients": "abc@example.com",
            "subject": "Subject",
            "body": "Body",
        },
    )
    assert response.status_code == 202
    assert response.json()["queued_count"] == 1
    operation = (
        db_session.query(MailSendOperationModel)
        .filter(MailSendOperationModel.recipient_email == "abc@example.com")
        .one()
    )
    assert operation.source_type == MailSendSourceType.MANUAL_TASK_MAIL


def test_send_manual_task_mail_requires_smtp(
    client, auth_headers, db_session, organization_id, user_id
):
    scenario = _seed_worklist_scenario(db_session, organization_id, user_id)
    todo_id = scenario["todo_id"]
    customer_id = str(scenario["customers"]["alpha"].id)

    response = client.post(
        f"{WORKLIST_BASE.format(todo_id=todo_id)}/customers/{customer_id}/manual-mail",
        headers=auth_headers,
        json={
            "recipients": "a@example.com",
            "subject": "Subject",
            "body": "Body",
        },
    )
    assert response.status_code == 422
