"""E2E: operations bulk-email excel multipart preview + send (mocked delivery)."""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import patch
from uuid import UUID, uuid4

from openpyxl import Workbook

from app.modules.fair_emails.infrastructure.persistence.models import (
    FairEmailBatchModel,
    FairEmailOutboxModel,
)
from app.modules.mail_send_operations.infrastructure.persistence.models import MailSendOperationModel
from app.modules.operations.infrastructure.persistence.models import OperationModel
from tests.modules.fair_emails.test_fair_bulk_email_api import _create_smtp, _create_template


def _xlsx_bytes(rows: list[tuple[object, ...]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(list(row))
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _multipart(payload: dict, excel_bytes: bytes, filename: str = "recipients.xlsx"):
    return {
        "payload": (None, json.dumps(payload), "application/json"),
        "excel_file": (filename, excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    }


def test_bulk_email_excel_multipart_preview_and_send_e2e(
    client,
    auth_headers,
    db_session,
    organization_id,
):
    template_id = _create_template(client, auth_headers, key=f"excel_e2e_{uuid4().hex[:8]}")
    smtp = _create_smtp(client, auth_headers)
    email_account_id = smtp.json()["id"]

    excel_bytes = _xlsx_bytes(
        [
            ("Alıcı / Firma Adı", "E-posta"),
            ("Valid Co", "valid@example.com"),
            ("Duplicate Co", "VALID@example.com"),
            ("Bad Co", "not-an-email"),
            ("Second Valid", "other@example.com"),
        ]
    )

    preview_payload = {
        "source_type": "manual",
        "template_id": template_id,
        "email_account_id": email_account_id,
        "subject_override": "Excel E2E subject",
    }
    preview = client.post(
        "/api/v1/operations/bulk-email/preview",
        headers=auth_headers,
        files=_multipart(preview_payload, excel_bytes),
    )
    assert preview.status_code == 200, preview.text
    recipients = preview.json()["recipients"]
    assert recipients["source_type"] == "manual"
    assert recipients["deduped_recipient_count"] == 2
    assert recipients["duplicate_count"] == 1
    assert recipients["invalid_count"] >= 2  # header-like + bad email
    will_send = [item for item in recipients["recipients"] if item["status"] == "will_send"]
    assert {item["email"] for item in will_send} == {"valid@example.com", "other@example.com"}
    assert preview.json()["mail"]["email_account_id"] == email_account_id

    send_payload = {
        "source_type": "manual",
        "template_id": template_id,
        "email_account_id": email_account_id,
        "subject": "Excel E2E subject",
        "title": "Excel multipart E2E",
        "client_token": f"excel-e2e-{uuid4().hex}",
    }

    with patch(
        "app.modules.fair_emails.application.process_batch.EmailDeliveryDispatcher.send",
    ):
        send = client.post(
            "/api/v1/operations/bulk-email/send",
            headers=auth_headers,
            files=_multipart(send_payload, excel_bytes),
        )
    assert send.status_code == 201, send.text
    body = send.json()
    operation_id = UUID(body["operation_id"])
    batch_id = UUID(body["batch_id"]) if body.get("batch_id") else None
    assert batch_id is not None
    assert body["total_count"] == 2

    operation = db_session.get(OperationModel, operation_id)
    assert operation is not None
    assert operation.operation_type == "bulk_email"
    type_config = operation.type_config if isinstance(operation.type_config, dict) else {}
    assert type_config.get("email_account_id") == email_account_id

    batch = db_session.get(FairEmailBatchModel, batch_id)
    assert batch is not None
    assert str(batch.email_account_id) == email_account_id
    assert batch.organization_id == organization_id

    outbox_rows = (
        db_session.query(FairEmailOutboxModel)
        .filter(FairEmailOutboxModel.batch_id == batch_id)
        .all()
    )
    assert len(outbox_rows) == 2
    assert {row.email for row in outbox_rows} == {"valid@example.com", "other@example.com"}
    assert all(str(row.organization_id) == str(organization_id) for row in outbox_rows)

    mail_ops = (
        db_session.query(MailSendOperationModel)
        .filter(MailSendOperationModel.batch_id == batch_id)
        .all()
    )
    # MSO rows may be created at batch start or when process_batch runs; ensure shared account.
    if mail_ops:
        assert all(str(op.email_account_id) == email_account_id for op in mail_ops)
        assert len(mail_ops) == 2
