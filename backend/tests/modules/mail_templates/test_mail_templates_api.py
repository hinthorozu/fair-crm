
def _mail_template_payload(**overrides):
    payload = {
        "name": "Welcome Email",
        "key": "welcome_email",
        "subject": "Hello {{ name }}",
        "body_html": "<p>Hello {{ name }}</p>",
        "body_text": "Hello {{ name }}",
    }
    payload.update(overrides)
    return payload


def _create_mail_template(client, auth_headers, **overrides):
    return client.post(
        "/api/v1/mail-templates",
        json=_mail_template_payload(**overrides),
        headers=auth_headers,
    )


def test_create_mail_template(client, auth_headers, organization_id):
    response = _create_mail_template(client, auth_headers, name="Welcome")
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Welcome"
    assert body["key"] == "welcome_email"
    assert body["organization_id"] == str(organization_id)
    assert body["is_active"] is True


def test_list_mail_templates(client, auth_headers):
    _create_mail_template(client, auth_headers, key="list_one")
    _create_mail_template(client, auth_headers, key="list_two", name="Second")
    response = client.get("/api/v1/mail-templates", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2


def test_get_mail_template_detail(client, auth_headers):
    create_response = _create_mail_template(client, auth_headers)
    template_id = create_response.json()["id"]
    response = client.get(f"/api/v1/mail-templates/{template_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == template_id


def test_cannot_access_mail_template_from_other_organization(
    client,
    auth_headers,
    other_organization_id,
    user_id,
):
    from app.integrations.kyrox_core.auth import create_test_token

    create_response = _create_mail_template(client, auth_headers)
    template_id = create_response.json()["id"]
    other_headers = {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(other_organization_id),
    }
    response = client.get(f"/api/v1/mail-templates/{template_id}", headers=other_headers)
    assert response.status_code == 404


def test_duplicate_key_rejected(client, auth_headers):
    first = _create_mail_template(client, auth_headers, key="duplicate_key")
    assert first.status_code == 201
    second = _create_mail_template(client, auth_headers, key="duplicate_key", name="Another")
    assert second.status_code == 409


def test_update_mail_template(client, auth_headers):
    create_response = _create_mail_template(client, auth_headers)
    template_id = create_response.json()["id"]
    response = client.patch(
        f"/api/v1/mail-templates/{template_id}",
        json={"name": "Updated Welcome", "subject": "Updated {{ name }}"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Welcome"
    assert response.json()["subject"] == "Updated {{ name }}"


def test_soft_delete_mail_template(client, auth_headers):
    create_response = _create_mail_template(client, auth_headers, key="delete_me")
    template_id = create_response.json()["id"]
    delete_response = client.delete(f"/api/v1/mail-templates/{template_id}", headers=auth_headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted_at"] is not None

    get_response = client.get(f"/api/v1/mail-templates/{template_id}", headers=auth_headers)
    assert get_response.status_code == 404

    list_response = client.get("/api/v1/mail-templates", headers=auth_headers)
    assert list_response.status_code == 200
    assert list_response.json()["items"] == []


def test_only_one_default_mail_template_per_type_and_language(client, auth_headers):
    first = _create_mail_template(client, auth_headers, key="default_one", is_default=True)
    second = _create_mail_template(
        client,
        auth_headers,
        key="default_two",
        name="Second Default",
        is_default=True,
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["is_default"] is True

    first_after = client.get(f"/api/v1/mail-templates/{first.json()['id']}", headers=auth_headers)
    assert first_after.json()["is_default"] is False


def test_render_mail_template(client, auth_headers):
    create_response = _create_mail_template(client, auth_headers, key="render_me")
    template_id = create_response.json()["id"]
    response = client.post(
        f"/api/v1/mail-templates/{template_id}/render",
        json={"variables": {"name": "Ada"}},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["subject"] == "Hello Ada"
    assert body["body_html"] == "<p>Hello Ada</p>"
    assert body["body_text"] == "Hello Ada"


def test_render_mail_template_missing_variable_returns_400(client, auth_headers):
    create_response = _create_mail_template(client, auth_headers, key="render_missing")
    template_id = create_response.json()["id"]
    response = client.post(
        f"/api/v1/mail-templates/{template_id}/render",
        json={"variables": {}},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_invalid_template_key_rejected(client, auth_headers):
    response = _create_mail_template(client, auth_headers, key="Invalid Key")
    assert response.status_code == 400


def test_update_makes_template_default_clears_previous(client, auth_headers):
    first = _create_mail_template(client, auth_headers, key="default_one", is_default=True)
    second = _create_mail_template(client, auth_headers, key="default_two", name="Second")
    assert first.status_code == 201
    assert second.status_code == 201

    response = client.patch(
        f"/api/v1/mail-templates/{second.json()['id']}",
        json={"is_default": True},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["is_default"] is True

    first_after = client.get(f"/api/v1/mail-templates/{first.json()['id']}", headers=auth_headers)
    assert first_after.status_code == 200
    assert first_after.json()["is_default"] is False


def test_update_same_default_template_is_idempotent(client, auth_headers):
    create_response = _create_mail_template(client, auth_headers, key="default_self", is_default=True)
    template_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/mail-templates/{template_id}",
        json={"is_default": True, "name": "Still Default"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["is_default"] is True
    assert response.json()["name"] == "Still Default"


def test_update_default_does_not_affect_different_language(client, auth_headers):
    tr_default = _create_mail_template(
        client,
        auth_headers,
        key="default_tr",
        language="tr",
        is_default=True,
    )
    en_template = _create_mail_template(
        client,
        auth_headers,
        key="template_en",
        language="en",
        name="English Template",
    )
    assert tr_default.status_code == 201
    assert en_template.status_code == 201

    response = client.patch(
        f"/api/v1/mail-templates/{en_template.json()['id']}",
        json={"is_default": True},
        headers=auth_headers,
    )
    assert response.status_code == 200

    tr_after = client.get(f"/api/v1/mail-templates/{tr_default.json()['id']}", headers=auth_headers)
    assert tr_after.json()["is_default"] is True


def test_update_default_does_not_affect_different_template_type(client, auth_headers):
    transactional = _create_mail_template(
        client,
        auth_headers,
        key="default_transactional",
        template_type="transactional",
        is_default=True,
    )
    marketing = _create_mail_template(
        client,
        auth_headers,
        key="marketing_template",
        template_type="marketing",
        name="Marketing Template",
    )
    assert transactional.status_code == 201
    assert marketing.status_code == 201

    response = client.patch(
        f"/api/v1/mail-templates/{marketing.json()['id']}",
        json={"is_default": True},
        headers=auth_headers,
    )
    assert response.status_code == 200

    transactional_after = client.get(
        f"/api/v1/mail-templates/{transactional.json()['id']}",
        headers=auth_headers,
    )
    assert transactional_after.json()["is_default"] is True


def test_update_default_does_not_affect_other_organization(
    client,
    auth_headers,
    other_organization_id,
    user_id,
):
    from app.integrations.kyrox_core.auth import create_test_token

    org_one_default = _create_mail_template(client, auth_headers, key="org_one_default", is_default=True)
    assert org_one_default.status_code == 201

    other_headers = {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(other_organization_id),
    }
    org_two_template = _create_mail_template(
        client,
        other_headers,
        key="org_two_template",
        name="Other Org Template",
    )
    assert org_two_template.status_code == 201

    response = client.patch(
        f"/api/v1/mail-templates/{org_two_template.json()['id']}",
        json={"is_default": True},
        headers=other_headers,
    )
    assert response.status_code == 200

    org_one_after = client.get(
        f"/api/v1/mail-templates/{org_one_default.json()['id']}",
        headers=auth_headers,
    )
    assert org_one_after.json()["is_default"] is True


def test_soft_deleted_default_does_not_block_new_default(client, auth_headers):
    deleted_default = _create_mail_template(
        client,
        auth_headers,
        key="deleted_default",
        is_default=True,
    )
    assert deleted_default.status_code == 201
    template_id = deleted_default.json()["id"]

    delete_response = client.delete(f"/api/v1/mail-templates/{template_id}", headers=auth_headers)
    assert delete_response.status_code == 200

    replacement = _create_mail_template(client, auth_headers, key="replacement_default")
    assert replacement.status_code == 201

    response = client.patch(
        f"/api/v1/mail-templates/{replacement.json()['id']}",
        json={"is_default": True},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["is_default"] is True


def test_invalid_template_key_rejected(client, auth_headers):
    response = _create_mail_template(client, auth_headers, key="Invalid Key")
    assert response.status_code == 400
