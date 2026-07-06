from uuid import uuid4

from tests.conftest_helpers import pagination_from

from app.modules.todos.application.outcome_default_seed import DEFAULT_OUTCOME_SEEDS

OUTCOMES_BASE = "/api/v1/todo-outcomes"


def _create_outcome(client, auth_headers, **overrides):
    payload = {
        "name": "Özel sonuç",
        "code": f"ozel_{uuid4().hex[:8]}",
        "primary_worklist_status": "in_follow_up",
    }
    payload.update(overrides)
    return client.post(OUTCOMES_BASE, json=payload, headers=auth_headers)


def test_list_seeds_default_outcomes_on_first_read(client, auth_headers):
    response = client.get(OUTCOMES_BASE, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert pagination_from(body)["totalItems"] == len(DEFAULT_OUTCOME_SEEDS)
    codes = {item["code"] for item in body["items"]}
    assert codes == {spec.code for spec in DEFAULT_OUTCOME_SEEDS}


def test_list_default_seed_is_idempotent(client, auth_headers):
    first = client.get(OUTCOMES_BASE, headers=auth_headers)
    second = client.get(OUTCOMES_BASE, headers=auth_headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert pagination_from(first.json())["totalItems"] == pagination_from(second.json())["totalItems"]


def test_create_and_get_outcome(client, auth_headers, organization_id):
    create_response = _create_outcome(
        client,
        auth_headers,
        name="VIP takip",
        code="vip_takip",
        primary_worklist_status="closed",
        requires_action=True,
    )
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["name"] == "VIP takip"
    assert body["code"] == "vip_takip"
    assert body["primary_worklist_status"] == "closed"
    assert body["requires_action"] is True
    assert body["organization_id"] == str(organization_id)
    assert body["is_active"] is True

    outcome_id = body["id"]
    get_response = client.get(f"{OUTCOMES_BASE}/{outcome_id}", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()["id"] == outcome_id


def test_create_duplicate_code_returns_409(client, auth_headers):
    first = _create_outcome(client, auth_headers, code="dup_code")
    assert first.status_code == 201
    second = _create_outcome(client, auth_headers, code="dup_code")
    assert second.status_code == 409


def test_update_outcome(client, auth_headers):
    create_response = _create_outcome(client, auth_headers, code="update_me")
    outcome_id = create_response.json()["id"]

    update_response = client.patch(
        f"{OUTCOMES_BASE}/{outcome_id}",
        json={"name": "Güncellenmiş ad", "sort_order": 99},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    body = update_response.json()
    assert body["name"] == "Güncellenmiş ad"
    assert body["sort_order"] == 99
    assert body["code"] == "update_me"


def test_patch_code_is_immutable(client, auth_headers):
    create_response = _create_outcome(client, auth_headers, code="immutable_code")
    outcome_id = create_response.json()["id"]

    response = client.patch(
        f"{OUTCOMES_BASE}/{outcome_id}",
        json={"code": "new_code", "name": "Still old code"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "immutable" in response.json()["detail"].lower()


def test_deactivate_outcome(client, auth_headers):
    create_response = _create_outcome(client, auth_headers, code="deactivate_me")
    outcome_id = create_response.json()["id"]

    deactivate_response = client.post(
        f"{OUTCOMES_BASE}/{outcome_id}/deactivate",
        headers=auth_headers,
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False


def test_list_active_filter(client, auth_headers):
    create_response = _create_outcome(client, auth_headers, code="active_filter")
    outcome_id = create_response.json()["id"]
    client.post(f"{OUTCOMES_BASE}/{outcome_id}/deactivate", headers=auth_headers)

    active_only = client.get(f"{OUTCOMES_BASE}?is_active=true", headers=auth_headers)
    inactive_only = client.get(f"{OUTCOMES_BASE}?is_active=false", headers=auth_headers)
    all_items = client.get(f"{OUTCOMES_BASE}?is_active=all", headers=auth_headers)
    default_list = client.get(OUTCOMES_BASE, headers=auth_headers)

    assert active_only.status_code == 200
    assert inactive_only.status_code == 200
    assert all_items.status_code == 200
    assert default_list.status_code == 200

    active_codes = {item["code"] for item in active_only.json()["items"]}
    inactive_codes = {item["code"] for item in inactive_only.json()["items"]}
    all_codes = {item["code"] for item in all_items.json()["items"]}
    default_codes = {item["code"] for item in default_list.json()["items"]}

    assert "active_filter" not in active_codes
    assert all(item["is_active"] for item in active_only.json()["items"])
    assert "active_filter" in inactive_codes
    assert all(not item["is_active"] for item in inactive_only.json()["items"])
    assert "active_filter" in all_codes
    assert all_codes == default_codes
    assert pagination_from(all_items.json())["totalItems"] >= len(active_codes) + len(
        inactive_codes
    )


def test_get_outcome_not_found(client, auth_headers):
    response = client.get(f"{OUTCOMES_BASE}/{uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_org_isolation(client, auth_headers, other_organization_id):
    create_response = _create_outcome(client, auth_headers, code="org_a_only")
    outcome_id = create_response.json()["id"]

    other_headers = {
        **auth_headers,
        "X-Organization-Id": str(other_organization_id),
    }
    response = client.get(f"{OUTCOMES_BASE}/{outcome_id}", headers=other_headers)
    assert response.status_code == 404


def test_no_delete_endpoint(client, auth_headers):
    create_response = _create_outcome(client, auth_headers, code="no_delete")
    outcome_id = create_response.json()["id"]

    response = client.delete(f"{OUTCOMES_BASE}/{outcome_id}", headers=auth_headers)
    assert response.status_code == 405


def test_create_invalid_primary_status(client, auth_headers):
    response = _create_outcome(
        client,
        auth_headers,
        code="bad_status",
        primary_worklist_status="not_started",
    )
    assert response.status_code == 422
