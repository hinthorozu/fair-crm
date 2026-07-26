"""Manual/Excel bulk recipients must not CRM-lookup or apply EmailConsentPolicy."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

from sqlalchemy import event

from app.modules.contacts.infrastructure.persistence.models import ContactModel
from app.modules.customers.infrastructure.persistence.communication_models import CustomerEmailModel
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fair_emails.application.fair_bulk_mail_operation_sync import (
    FairBulkEmailMailOperationSync,
)
from app.modules.fair_emails.application.recipient_resolution import resolve_manual_and_excel_emails
from app.modules.fair_emails.application.recipient_service import FairBulkEmailRecipientService
from app.modules.fair_emails.application.send_bulk_email_operation import (
    SendBulkEmailOperationCommand,
    SendBulkEmailOperationUseCase,
)
from app.modules.fair_emails.infrastructure.persistence.models import FairEmailOutboxModel
from app.modules.fair_emails.infrastructure.repositories.fair_email_batch_repository import (
    SqlAlchemyFairEmailBatchRepository,
)
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
from app.modules.mail_templates.infrastructure.repositories.mail_template_repository import (
    SqlAlchemyMailTemplateRepository,
)
from app.modules.smtp.infrastructure.repositories.smtp_account_repository import (
    SqlAlchemySmtpAccountRepository,
)
from app.shared.email_consent_policy import EmailConsentPolicy
from tests.conftest_customer_helpers import create_test_customer
from tests.modules.fair_emails.test_fair_bulk_email_api import _create_smtp, _create_template


def _auth_ok():
    auth = MagicMock()
    auth.check_permission.return_value = True
    return auth


def _send_uc(db_session) -> SendBulkEmailOperationUseCase:
    return SendBulkEmailOperationUseCase(
        SqlAlchemyFairRepository(db_session),
        SqlAlchemyMailTemplateRepository(db_session),
        SqlAlchemySmtpAccountRepository(db_session),
        SqlAlchemyFairEmailBatchRepository(db_session),
        FairBulkEmailRecipientService(db_session),
        FairBulkEmailMailOperationSync(db_session),
        _auth_ok(),
        session=db_session,
    )


def test_manual_resolution_ignores_crm_customer_consent_false():
    result = resolve_manual_and_excel_emails(
        manual_emails_text="blocked-customer@example.com",
    )
    assert result.deduped_recipient_count == 1
    assert result.customer_consent_skipped_count == 0
    row = result.recipients[0]
    assert row.status == "will_send"
    assert row.customer_id is None
    assert row.contact_id is None
    assert row.source == "manual"


def test_excel_resolution_ignores_crm_contact_consent_false():
    result = resolve_manual_and_excel_emails(
        excel_recipient_rows=[("Blocked", "blocked-contact@example.com")],
    )
    assert result.deduped_recipient_count == 1
    assert result.contact_consent_skipped_count == 0
    row = result.recipients[0]
    assert row.status == "will_send"
    assert row.source == "excel"
    assert row.customer_id is None
    assert row.contact_id is None


def test_manual_duplicate_cleanup_still_works():
    result = resolve_manual_and_excel_emails(
        manual_emails_text="a@example.com;b@example.com;a@example.com",
    )
    assert result.total_found == 3
    assert result.duplicate_count == 1
    assert result.deduped_recipient_count == 2


def test_excel_duplicate_cleanup_still_works():
    result = resolve_manual_and_excel_emails(
        excel_recipient_rows=[
            ("A", "a@example.com"),
            ("B", "b@example.com"),
            ("A2", "a@example.com"),
        ],
    )
    assert result.total_found == 3
    assert result.duplicate_count == 1
    assert result.deduped_recipient_count == 2


def test_manual_send_with_crm_customer_email_allowed_false_still_queues(
    db_session,
    client,
    auth_headers,
    organization_id,
    user_id,
):
    customer = create_test_customer(
        db_session,
        organization_id,
        display_name="Blocked Cust",
        email="manual-blocked-cust@example.com",
    )
    db_session.commit()
    model = db_session.query(CustomerModel).filter(CustomerModel.id == customer.id).one()
    model.email_allowed = False
    db_session.commit()

    template_id = _create_template(client, auth_headers, key=f"man_consent_{uuid4().hex[:8]}")
    smtp = _create_smtp(client, auth_headers)

    with patch.object(EmailConsentPolicy, "evaluate") as spy:
        result = _send_uc(db_session).execute(
            SendBulkEmailOperationCommand(
                organization_id=organization_id,
                user_id=user_id,
                access_token="token",
                source_type="manual",
                template_id=UUID(template_id),
                email_account_id=UUID(smtp.json()["id"]),
                subject="Manual no CRM consent",
                manual_emails="manual-blocked-cust@example.com",
            )
        )
        db_session.commit()
        spy.assert_not_called()

    outbox = (
        db_session.query(FairEmailOutboxModel)
        .filter(FairEmailOutboxModel.batch_id == result.batch_id)
        .all()
    )
    assert len(outbox) == 1
    assert outbox[0].email == "manual-blocked-cust@example.com"
    assert outbox[0].customer_id is None
    assert outbox[0].contact_id is None
    assert outbox[0].source == "manual"


def test_manual_send_with_crm_contact_email_allowed_false_still_queues(
    db_session,
    client,
    auth_headers,
    organization_id,
    user_id,
):
    customer = create_test_customer(
        db_session,
        organization_id,
        display_name="Parent Co",
        email="parent@example.com",
    )
    db_session.commit()
    now = datetime.now(tz=UTC)
    contact = ContactModel(
        id=uuid4(),
        organization_id=organization_id,
        customer_id=customer.id,
        first_name="Blocked",
        last_name="Contact",
        email="manual-blocked-contact@example.com",
        is_primary=True,
        is_active=True,
        email_allowed=False,
        sms_allowed=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(contact)
    db_session.commit()

    template_id = _create_template(client, auth_headers, key=f"man_ct_{uuid4().hex[:8]}")
    smtp = _create_smtp(client, auth_headers)

    result = _send_uc(db_session).execute(
        SendBulkEmailOperationCommand(
            organization_id=organization_id,
            user_id=user_id,
            access_token="token",
            source_type="manual",
            template_id=UUID(template_id),
            email_account_id=UUID(smtp.json()["id"]),
            subject="Manual contact no consent",
            manual_emails="manual-blocked-contact@example.com",
        )
    )
    db_session.commit()

    outbox = (
        db_session.query(FairEmailOutboxModel)
        .filter(FairEmailOutboxModel.batch_id == result.batch_id)
        .one()
    )
    assert outbox.customer_id is None
    assert outbox.contact_id is None
    assert outbox.source == "manual"


def test_excel_send_with_crm_match_does_not_apply_consent(
    db_session,
    client,
    auth_headers,
    organization_id,
    user_id,
):
    customer = create_test_customer(
        db_session,
        organization_id,
        display_name="Excel Block",
        email="excel-blocked@example.com",
    )
    db_session.commit()
    model = db_session.query(CustomerModel).filter(CustomerModel.id == customer.id).one()
    model.email_allowed = False
    db_session.commit()

    template_id = _create_template(client, auth_headers, key=f"xl_consent_{uuid4().hex[:8]}")
    smtp = _create_smtp(client, auth_headers)

    with patch.object(EmailConsentPolicy, "evaluate") as spy:
        result = _send_uc(db_session).execute(
            SendBulkEmailOperationCommand(
                organization_id=organization_id,
                user_id=user_id,
                access_token="token",
                source_type="manual",
                template_id=UUID(template_id),
                email_account_id=UUID(smtp.json()["id"]),
                subject="Excel no CRM consent",
                excel_recipient_rows=[
                    {"display_name": "X", "email": "excel-blocked@example.com"},
                ],
            )
        )
        db_session.commit()
        spy.assert_not_called()

    outbox = (
        db_session.query(FairEmailOutboxModel)
        .filter(FairEmailOutboxModel.batch_id == result.batch_id)
        .one()
    )
    assert outbox.email == "excel-blocked@example.com"
    assert outbox.source == "excel"
    assert outbox.customer_id is None
    assert outbox.contact_id is None


def test_manual_excel_resolution_does_not_issue_crm_email_lookup_queries(db_session):
    """Resolution path must not hit CustomerEmail / Contact tables (no CRM lookup)."""
    statements: list[str] = []

    def _before_cursor(conn, cursor, statement, parameters, context, executemany):
        statements.append(str(statement).lower())

    bind = db_session.get_bind()
    event.listen(bind, "before_cursor_execute", _before_cursor)
    try:
        result = resolve_manual_and_excel_emails(
            manual_emails_text=";".join([f"user{i}@example.com" for i in range(50)]),
            excel_recipient_rows=[("P", "probe@example.com"), ("P2", "probe@example.com")],
        )
    finally:
        event.remove(bind, "before_cursor_execute", _before_cursor)

    assert result.deduped_recipient_count == 51
    assert result.duplicate_count == 1
    joined = "\n".join(statements)
    assert CustomerEmailModel.__tablename__ not in joined
    assert ContactModel.__tablename__ not in joined
    assert len(statements) == 0
