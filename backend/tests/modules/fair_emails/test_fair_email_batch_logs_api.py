"""Fair bulk email batch log API tests."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.modules.fair_emails.infrastructure.persistence.models import FairEmailBatchModel, FairEmailOutboxModel
from tests.conftest_customer_helpers import create_test_customer
from tests.modules.fair_emails.test_fair_bulk_email_api import (
    _create_fair,
    _setup_fair_with_recipients,
)


def _seed_batch_with_outbox(db_session, organization_id, user_id, fair_id, template_id, smtp_id):
    now = datetime.now(timezone.utc)
    batch_id = uuid4()
    fair_uuid = UUID(str(fair_id))
    template_uuid = UUID(str(template_id))
    smtp_uuid = UUID(str(smtp_id))
    customer = create_test_customer(
        db_session,
        organization_id,
        display_name="ABC Fuarcılık",
        email="info@abc.com",
    )
    participation_id = uuid4()
    batch = FairEmailBatchModel(
        id=batch_id,
        organization_id=organization_id,
        fair_id=fair_uuid,
        template_id=template_uuid,
        smtp_account_id=smtp_uuid,
        subject_override="Fuar daveti",
        recipient_options_json={"include_customer_emails": True},
        status="completed_with_errors",
        total_count=2,
        sent_count=1,
        failed_count=1,
        skipped_count=0,
        created_by_user_id=user_id,
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    db_session.add(batch)
    db_session.add(
        FairEmailOutboxModel(
            id=uuid4(),
            batch_id=batch_id,
            organization_id=organization_id,
            customer_id=customer.id,
            contact_id=None,
            participation_id=participation_id,
            recipient_name="ABC Fuarcılık",
            company_name="ABC Fuarcılık",
            email="info@abc.com",
            source="customer",
            status="sent",
            sent_at=now,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.add(
        FairEmailOutboxModel(
            id=uuid4(),
            batch_id=batch_id,
            organization_id=organization_id,
            customer_id=customer.id,
            contact_id=uuid4(),
            participation_id=participation_id,
            recipient_name="Ahmet Yılmaz",
            company_name="ABC Fuarcılık",
            email="fail@example.com",
            source="contact",
            status="failed",
            error_message="Authentication failed",
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()
    return str(batch_id)


def test_list_email_batches_returns_items(client, auth_headers, db_session, organization_id, user_id):
    data = _setup_fair_with_recipients(client, auth_headers, db_session, organization_id)
    batch_id = _seed_batch_with_outbox(
        db_session,
        organization_id,
        user_id,
        data["fair_id"],
        data["template_id"],
        data["smtp"].json()["id"],
    )

    response = client.get(
        f"/api/v1/fairs/{data['fair_id']}/bulk-email/batches",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["id"] == batch_id
    assert item["status"] == "completed_with_errors"
    assert item["template_name"] == "Fuar Daveti"
    assert item["smtp_account_name"] == "Primary SMTP"
    assert item["subject"] == "Fuar daveti"
    assert item["total_recipients"] == 2
    assert item["sent_count"] == 1
    assert item["failed_count"] == 1
    assert item["queued_count"] == 0


def test_get_email_batch_detail_returns_outbox_items(client, auth_headers, db_session, organization_id, user_id):
    data = _setup_fair_with_recipients(client, auth_headers, db_session, organization_id)
    batch_id = _seed_batch_with_outbox(
        db_session,
        organization_id,
        user_id,
        data["fair_id"],
        data["template_id"],
        data["smtp"].json()["id"],
    )

    response = client.get(
        f"/api/v1/fairs/{data['fair_id']}/bulk-email/batches/{batch_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["batch"]["id"] == batch_id
    assert body["batch"]["total_recipients"] == 2
    assert len(body["items"]) == 2

    sent_item = next(item for item in body["items"] if item["status"] == "sent")
    failed_item = next(item for item in body["items"] if item["status"] == "failed")
    assert sent_item["recipient_email"] == "info@abc.com"
    assert sent_item["recipient_source"] == "customer"
    assert failed_item["error_message"] == "Authentication failed"
    assert failed_item["attempts"] == 1


def test_list_email_batches_denied_without_preview_permission(client, auth_headers, db_session, organization_id, user_id):
    from app.modules.fair_emails.api.dependencies import get_authorization_adapter as get_fair_emails_authorization_adapter
    from tests.modules.test_endpoint_permission_enforcement import SelectiveAuthorization

    data = _setup_fair_with_recipients(client, auth_headers, db_session, organization_id)
    _seed_batch_with_outbox(
        db_session,
        organization_id,
        user_id,
        data["fair_id"],
        data["template_id"],
        data["smtp"].json()["id"],
    )

    client.app.dependency_overrides[get_fair_emails_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={"fair_crm.fair_emails.preview"}
    )
    try:
        response = client.get(
            f"/api/v1/fairs/{data['fair_id']}/bulk-email/batches",
            headers=auth_headers,
        )
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_fair_emails_authorization_adapter, None)


def test_get_email_batch_detail_other_fair_not_found(client, auth_headers, db_session, organization_id, user_id):
    data = _setup_fair_with_recipients(client, auth_headers, db_session, organization_id)
    batch_id = _seed_batch_with_outbox(
        db_session,
        organization_id,
        user_id,
        data["fair_id"],
        data["template_id"],
        data["smtp"].json()["id"],
    )
    other_fair_id = _create_fair(client, auth_headers, name="Other Fair")

    response = client.get(
        f"/api/v1/fairs/{other_fair_id}/bulk-email/batches/{batch_id}",
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_list_email_batches_other_org_not_found(
    client,
    auth_headers,
    db_session,
    organization_id,
    other_organization_id,
    user_id,
):
    from app.integrations.kyrox_core.auth import create_test_token

    data = _setup_fair_with_recipients(client, auth_headers, db_session, organization_id)
    _seed_batch_with_outbox(
        db_session,
        organization_id,
        user_id,
        data["fair_id"],
        data["template_id"],
        data["smtp"].json()["id"],
    )
    other_headers = {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(other_organization_id),
    }

    response = client.get(
        f"/api/v1/fairs/{data['fair_id']}/bulk-email/batches",
        headers=other_headers,
    )
    assert response.status_code == 404
