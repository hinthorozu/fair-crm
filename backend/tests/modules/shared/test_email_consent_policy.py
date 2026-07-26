"""Central EmailConsentPolicy unit + integration-oriented tests."""

from __future__ import annotations

from uuid import uuid4

from app.modules.contacts.infrastructure.persistence.models import ContactModel
from app.modules.customers.infrastructure.persistence.communication_models import CustomerEmailModel
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.mail_send_operations.application.mail_send_operation_service import (
    MailSendOperationService,
)
from app.modules.mail_send_operations.domain.value_objects import MailSendSourceType
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    CreateMailSendOperationParams,
    SqlAlchemyMailSendOperationRepository,
)
from app.shared.consent import (
    CONTACT_EMAIL_CONSENT_SKIP,
    CUSTOMER_EMAIL_CONSENT_SKIP,
    EmailConsentBlockedError,
    evaluate_candidate_email_consent,
    evaluate_email_consent_flags,
)
from app.shared.email_consent_policy import EmailConsentPolicy
from tests.conftest_customer_helpers import create_test_customer


def test_evaluate_flags_customer_blocks_even_if_contact_allows():
    decision = evaluate_email_consent_flags(
        customer_email_allowed_flags=[False],
        contact_email_allowed_flags=[True],
    )
    assert decision.allowed is False
    assert decision.skip_reason == CUSTOMER_EMAIL_CONSENT_SKIP


def test_evaluate_flags_contact_blocks_when_customer_allows():
    decision = evaluate_email_consent_flags(
        customer_email_allowed_flags=[True],
        contact_email_allowed_flags=[False],
    )
    assert decision.allowed is False
    assert decision.skip_reason == CONTACT_EMAIL_CONSENT_SKIP


def test_evaluate_candidate_contact_source():
    decision = evaluate_candidate_email_consent(
        customer_email_allowed=True,
        contact_email_allowed=False,
        is_contact_source=True,
    )
    assert decision.skip_reason == CONTACT_EMAIL_CONSENT_SKIP


def test_policy_blocks_email_matching_contact(
    db_session, organization_id
):
    customer = create_test_customer(
        db_session,
        organization_id,
        display_name="Consent Co",
        email="info@consent-match.com",
    )
    db_session.commit()
    now = customer.created_at
    contact = ContactModel(
        id=uuid4(),
        organization_id=organization_id,
        customer_id=customer.id,
        first_name="Blocked",
        last_name="Contact",
        email="blocked@consent-match.com",
        is_primary=True,
        is_active=True,
        email_allowed=False,
        sms_allowed=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(contact)
    db_session.commit()

    policy = EmailConsentPolicy(db_session)
    decision = policy.evaluate(organization_id, email="blocked@consent-match.com")
    assert decision.allowed is False
    assert decision.skip_reason == CONTACT_EMAIL_CONSENT_SKIP


def test_policy_customer_email_false_blocks_matched_address(
    db_session, organization_id
):
    customer = create_test_customer(
        db_session,
        organization_id,
        display_name="No Mail Co",
        email="info@nomail.com",
    )
    db_session.commit()
    model = db_session.query(CustomerModel).filter(CustomerModel.id == customer.id).one()
    model.email_allowed = False
    db_session.commit()

    email_row = (
        db_session.query(CustomerEmailModel)
        .filter(CustomerEmailModel.customer_id == customer.id)
        .first()
    )
    assert email_row is not None

    policy = EmailConsentPolicy(db_session)
    decision = policy.evaluate(organization_id, email=email_row.email)
    assert decision.allowed is False
    assert decision.skip_reason == CUSTOMER_EMAIL_CONSENT_SKIP


def test_create_mso_blocked_when_customer_consent_false(
    db_session, organization_id
):
    customer = create_test_customer(
        db_session,
        organization_id,
        display_name="Blocked Create",
        email="create-block@example.com",
    )
    db_session.commit()
    model = db_session.query(CustomerModel).filter(CustomerModel.id == customer.id).one()
    model.email_allowed = False
    db_session.commit()

    service = MailSendOperationService(SqlAlchemyMailSendOperationRepository(db_session))
    try:
        service.create_mail_send_operation(
            CreateMailSendOperationParams(
                organization_id=organization_id,
                source_type=MailSendSourceType.MANUAL_TASK_MAIL,
                recipient_email="anyone@example.com",
                subject="x",
                body_text="y",
                customer_id=customer.id,
            )
        )
        assert False, "expected EmailConsentBlockedError"
    except EmailConsentBlockedError as exc:
        assert exc.decision.skip_reason == CUSTOMER_EMAIL_CONSENT_SKIP
