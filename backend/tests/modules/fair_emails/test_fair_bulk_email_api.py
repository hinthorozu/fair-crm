"""Fair bulk email API tests."""

from unittest.mock import patch

from tests.conftest_customer_helpers import create_test_customer


def _create_fair(client, auth_headers, **overrides):
    payload = {"name": "IFM 2026", "status": "active"}
    payload.update(overrides)
    response = client.post("/api/v1/fairs", json=payload, headers=auth_headers)
    assert response.status_code == 201
    return response.json()["id"]


def _create_contact(client, auth_headers, customer_id, **overrides):
    payload = {
        "customer_id": customer_id,
        "first_name": "Ahmet",
        "last_name": "Yılmaz",
        "email": "ahmet@abc.com",
        "is_primary": True,
        "is_active": True,
    }
    payload.update(overrides)
    response = client.post("/api/v1/contacts", json=payload, headers=auth_headers)
    assert response.status_code == 201
    return response.json()["id"]


def _create_participation(client, auth_headers, fair_id, customer_id, **overrides):
    payload = {"fair_id": fair_id, "customer_id": customer_id}
    payload.update(overrides)
    response = client.post("/api/v1/fair-participations", json=payload, headers=auth_headers)
    assert response.status_code == 201
    return response.json()


def _create_template(client, auth_headers, **overrides):
    payload = {
        "name": "Fuar Daveti",
        "key": "fair_invite",
        "subject": "Merhaba {{ contact_first_name }}",
        "body_html": "<p>{{ fair_name }} - {{ customer_name }}</p>",
        "body_text": "{{ fair_name }} - {{ customer_name }}",
        "template_type": "marketing",
    }
    payload.update(overrides)
    response = client.post("/api/v1/mail-templates", json=payload, headers=auth_headers)
    assert response.status_code == 201
    return response.json()["id"]


def _create_smtp(client, auth_headers):
    response = client.post(
        "/api/v1/smtp/accounts",
        json={
            "name": "Primary SMTP",
            "from_email": "noreply@example.com",
            "host": "smtp.example.com",
            "port": 587,
            "username": "smtp-user",
            "password": "secret-password",
            "encryption_type": "starttls",
            "is_default": True,
            "is_active": True,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response


def _setup_fair_with_recipients(client, auth_headers, db_session, organization_id):
    fair_id = _create_fair(client, auth_headers)
    customer = create_test_customer(
        db_session,
        organization_id,
        display_name="ABC Fuarcılık",
        email="info@abc.com",
    )
    db_session.commit()
    contact_id = _create_contact(client, auth_headers, str(customer.id))
    _create_participation(
        client,
        auth_headers,
        fair_id,
        str(customer.id),
        primary_contact_id=contact_id,
    )
    template_id = _create_template(client, auth_headers, key=f"fair_invite_{fair_id[:8]}")
    smtp = _create_smtp(client, auth_headers)
    return {
        "fair_id": fair_id,
        "customer_id": str(customer.id),
        "template_id": template_id,
        "smtp": smtp,
    }


def test_preview_recipients_includes_customer_email(client, auth_headers, db_session, organization_id):
    data = _setup_fair_with_recipients(client, auth_headers, db_session, organization_id)
    response = client.post(
        f"/api/v1/fairs/{data['fair_id']}/bulk-email/preview-recipients",
        json={"recipient_options": {"include_customer_emails": True, "include_contact_emails": False}},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["deduped_recipient_count"] >= 1
    assert any(item["source"] == "customer" and item["status"] == "will_send" for item in body["recipients"])


def test_preview_recipients_include_contacts_toggle(client, auth_headers, db_session, organization_id):
    data = _setup_fair_with_recipients(client, auth_headers, db_session, organization_id)
    without_contacts = client.post(
        f"/api/v1/fairs/{data['fair_id']}/bulk-email/preview-recipients",
        json={"recipient_options": {"include_customer_emails": False, "include_contact_emails": False}},
        headers=auth_headers,
    )
    with_contacts = client.post(
        f"/api/v1/fairs/{data['fair_id']}/bulk-email/preview-recipients",
        json={"recipient_options": {"include_customer_emails": False, "include_contact_emails": True}},
        headers=auth_headers,
    )
    assert without_contacts.json()["deduped_recipient_count"] == 0
    assert with_contacts.json()["deduped_recipient_count"] >= 1
    assert any(item["source"] == "contact" for item in with_contacts.json()["recipients"])


def test_preview_recipients_dedupes_duplicate_email(client, auth_headers, db_session, organization_id):
    data = _setup_fair_with_recipients(client, auth_headers, db_session, organization_id)
    client.post(
        "/api/v1/contacts",
        json={
            "customer_id": data["customer_id"],
            "first_name": "Mehmet",
            "last_name": "Demir",
            "email": "info@abc.com",
            "is_active": True,
        },
        headers=auth_headers,
    )
    response = client.post(
        f"/api/v1/fairs/{data['fair_id']}/bulk-email/preview-recipients",
        json={
            "recipient_options": {
                "include_customer_emails": True,
                "include_contact_emails": True,
                "dedupe_emails": True,
            }
        },
        headers=auth_headers,
    )
    will_send = [item for item in response.json()["recipients"] if item["status"] == "will_send"]
    emails = [item["email"] for item in will_send]
    assert len(emails) == len(set(emails))
    assert any(item["skip_reason"] == "duplicate_email" for item in response.json()["recipients"])


def test_preview_bulk_email_subject_override(client, auth_headers, db_session, organization_id):
    data = _setup_fair_with_recipients(client, auth_headers, db_session, organization_id)
    response = client.post(
        f"/api/v1/fairs/{data['fair_id']}/bulk-email/preview",
        json={
            "template_id": data["template_id"],
            "subject_override": "Özel fuar konusu",
            "recipient_options": {"include_customer_emails": True, "include_contact_emails": True},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["subject"] == "Özel fuar konusu"


def test_send_bulk_email_denied_without_permission(client, auth_headers, db_session, organization_id):
    from app.modules.fair_emails.api.dependencies import get_authorization_adapter as get_fair_emails_authorization_adapter
    from tests.modules.test_endpoint_permission_enforcement import SelectiveAuthorization

    data = _setup_fair_with_recipients(client, auth_headers, db_session, organization_id)
    client.app.dependency_overrides[get_fair_emails_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={"fair_crm.fair_emails.send"}
    )
    try:
        response = client.post(
            f"/api/v1/fairs/{data['fair_id']}/bulk-email/send",
            json={
                "template_id": data["template_id"],
                "recipient_options": {"include_customer_emails": True, "include_contact_emails": True},
            },
            headers=auth_headers,
        )
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_fair_emails_authorization_adapter, None)


@patch("app.modules.fair_emails.application.process_batch.ProcessFairEmailBatchUseCase.execute")
def test_send_bulk_email_queues_batch(mock_execute, client, auth_headers, db_session, organization_id):
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
    body = response.json()
    assert body["total_count"] >= 1
    assert body["batch_id"]
    assert body["status"] == "queued"


def test_preview_recipients_other_org_fair_not_found(client, auth_headers, db_session, organization_id, other_organization_id, user_id):
    from app.integrations.kyrox_core.auth import create_test_token

    data = _setup_fair_with_recipients(client, auth_headers, db_session, organization_id)
    other_headers = {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(other_organization_id),
    }
    response = client.post(
        f"/api/v1/fairs/{data['fair_id']}/bulk-email/preview-recipients",
        json={"recipient_options": {"include_customer_emails": True}},
        headers=other_headers,
    )
    assert response.status_code == 404
