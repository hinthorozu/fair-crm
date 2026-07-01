from tests.conftest_helpers import pagination_from


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "fair-crm"


def test_create_and_get_customer(client, auth_headers, organization_id):
    create_response = client.post(
        "/api/v1/customers",
        json={
            "display_name": "Teknova Elektrik A.Ş.",
            "city": "Ankara",
            "district": "Cankaya",
            "address": "100 Main Street",
            "description": "Key account",
            "phone": "0212 555 0101",
            "email": "Info@Example.com",
            "website": "https://www.teknova.com/about",
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["display_name"] == "Teknova Elektrik A.Ş."
    assert body["normalized_name"] == "TEKNOVA ELEKTRIK"
    assert body["phone"] == "902125550101"
    assert body["email"] == "info@example.com"
    assert body["website"] == "teknova.com"
    assert body["district"] == "Cankaya"
    assert body["organization_id"] == str(organization_id)

    customer_id = body["id"]
    get_response = client.get(f"/api/v1/customers/{customer_id}", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()["id"] == customer_id


def test_list_customers_search(client, auth_headers):
    client.post(
        "/api/v1/customers",
        json={"display_name": "Search Target Ltd.", "address": "Unique Address 42"},
        headers=auth_headers,
    )

    response = client.get("/api/v1/customers?search=Unique+Address", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()["items"]) >= 1


def test_update_customer(client, auth_headers):
    create_response = client.post(
        "/api/v1/customers",
        json={"display_name": "Before Update"},
        headers=auth_headers,
    )
    customer_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/customers/{customer_id}",
        json={"display_name": "After Update", "status": "active"},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["display_name"] == "After Update"
    assert update_response.json()["status"] == "active"


def test_archive_customer(client, auth_headers):
    create_response = client.post(
        "/api/v1/customers",
        json={"display_name": "To Archive"},
        headers=auth_headers,
    )
    customer_id = create_response.json()["id"]

    archive_response = client.delete(f"/api/v1/customers/{customer_id}", headers=auth_headers)
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "archived"
    assert archive_response.json()["deleted_at"] is not None

    get_response = client.get(f"/api/v1/customers/{customer_id}", headers=auth_headers)
    assert get_response.status_code == 404

    list_response = client.get("/api/v1/customers?status=archived", headers=auth_headers)
    assert list_response.status_code == 200
    archived_items = list_response.json()["items"]
    assert any(item["id"] == customer_id for item in archived_items)
    assert archived_items[0]["status"] == "archived"


def test_archived_included_in_default_list(client, auth_headers):
    create_response = client.post(
        "/api/v1/customers",
        json={"display_name": "Visible In All", "status": "active"},
        headers=auth_headers,
    )
    customer_id = create_response.json()["id"]
    client.delete(f"/api/v1/customers/{customer_id}", headers=auth_headers)

    default_list = client.get("/api/v1/customers", headers=auth_headers)
    assert default_list.status_code == 200
    archived = [item for item in default_list.json()["items"] if item["id"] == customer_id]
    assert len(archived) == 1
    assert archived[0]["status"] == "archived"


def test_active_filter_excludes_archived(client, auth_headers):
    active_response = client.post(
        "/api/v1/customers",
        json={"display_name": "Active Only", "status": "active"},
        headers=auth_headers,
    )
    active_id = active_response.json()["id"]

    archived_response = client.post(
        "/api/v1/customers",
        json={"display_name": "Archived Only", "status": "lead"},
        headers=auth_headers,
    )
    archived_id = archived_response.json()["id"]
    client.delete(f"/api/v1/customers/{archived_id}", headers=auth_headers)

    active_list = client.get("/api/v1/customers?status=active", headers=auth_headers)
    ids = {item["id"] for item in active_list.json()["items"]}
    assert active_id in ids
    assert archived_id not in ids


def test_restore_visible_in_default_list_not_in_archived_filter(client, auth_headers):
    create_response = client.post(
        "/api/v1/customers",
        json={"display_name": "Restore All View", "status": "inactive"},
        headers=auth_headers,
    )
    customer_id = create_response.json()["id"]
    client.delete(f"/api/v1/customers/{customer_id}", headers=auth_headers)

    restore_response = client.post(
        f"/api/v1/customers/{customer_id}/restore",
        headers=auth_headers,
    )
    assert restore_response.status_code == 200

    archived_list = client.get("/api/v1/customers?status=archived", headers=auth_headers)
    assert not any(item["id"] == customer_id for item in archived_list.json()["items"])

    default_list = client.get("/api/v1/customers", headers=auth_headers)
    restored = [item for item in default_list.json()["items"] if item["id"] == customer_id]
    assert len(restored) == 1
    assert restored[0]["status"] == "inactive"


def test_org_isolation_api(client, auth_headers, other_organization_id, user_id):
    from app.integrations.kyrox_core.auth import create_test_token

    create_response = client.post(
        "/api/v1/customers",
        json={"display_name": "Private Customer"},
        headers=auth_headers,
    )
    customer_id = create_response.json()["id"]

    other_headers = {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(other_organization_id),
    }
    get_response = client.get(f"/api/v1/customers/{customer_id}", headers=other_headers)
    assert get_response.status_code == 404


def test_unauthenticated_returns_401(client, organization_id):
    response = client.get(
        "/api/v1/customers",
        headers={"X-Organization-Id": str(organization_id)},
    )
    assert response.status_code == 401


def test_restore_customer(client, auth_headers):
    create_response = client.post(
        "/api/v1/customers",
        json={"display_name": "Restore Me", "status": "lead"},
        headers=auth_headers,
    )
    customer_id = create_response.json()["id"]

    archive_response = client.delete(f"/api/v1/customers/{customer_id}", headers=auth_headers)
    assert archive_response.status_code == 200

    archived_list = client.get("/api/v1/customers?status=archived", headers=auth_headers)
    assert any(item["id"] == customer_id for item in archived_list.json()["items"])

    restore_response = client.post(
        f"/api/v1/customers/{customer_id}/restore",
        headers=auth_headers,
    )
    assert restore_response.status_code == 200
    body = restore_response.json()
    assert body["status"] == "lead"
    assert body["deleted_at"] is None

    archived_after = client.get("/api/v1/customers?status=archived", headers=auth_headers)
    assert not any(item["id"] == customer_id for item in archived_after.json()["items"])

    default_list = client.get("/api/v1/customers", headers=auth_headers)
    assert any(item["id"] == customer_id for item in default_list.json()["items"])

    get_response = client.get(f"/api/v1/customers/{customer_id}", headers=auth_headers)
    assert get_response.status_code == 200


def test_restore_non_archived_customer_fails(client, auth_headers):
    create_response = client.post(
        "/api/v1/customers",
        json={"display_name": "Active Customer"},
        headers=auth_headers,
    )
    customer_id = create_response.json()["id"]

    restore_response = client.post(
        f"/api/v1/customers/{customer_id}/restore",
        headers=auth_headers,
    )
    assert restore_response.status_code == 400
    assert restore_response.json()["detail"] == "Customer is not archived"


def test_restore_customer_wrong_org_returns_404(
    client, auth_headers, other_organization_id, user_id
):
    from app.integrations.kyrox_core.auth import create_test_token

    create_response = client.post(
        "/api/v1/customers",
        json={"display_name": "Org Scoped Restore"},
        headers=auth_headers,
    )
    customer_id = create_response.json()["id"]
    client.delete(f"/api/v1/customers/{customer_id}", headers=auth_headers)

    other_headers = {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(other_organization_id),
    }
    restore_response = client.post(
        f"/api/v1/customers/{customer_id}/restore",
        headers=other_headers,
    )
    assert restore_response.status_code == 404


def test_list_customers_default_pagination(client, auth_headers):
    response = client.get("/api/v1/customers", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    pagination = pagination_from(body)
    assert pagination["page"] == 1
    assert pagination["pageSize"] == 25
    assert "totalItems" in pagination
    assert "totalPages" in pagination
    assert isinstance(body["items"], list)


def test_list_customers_custom_page_size_and_page_two(client, auth_headers):
    for index in range(12):
        client.post(
            "/api/v1/customers",
            json={"display_name": f"Paged Customer {index:02d}"},
            headers=auth_headers,
        )

    page_one = client.get("/api/v1/customers?page=1&page_size=10", headers=auth_headers)
    assert page_one.status_code == 200
    body_one = page_one.json()
    pagination_one = pagination_from(body_one)
    assert len(body_one["items"]) == 10
    assert pagination_one["page"] == 1
    assert pagination_one["pageSize"] == 10
    assert pagination_one["totalItems"] >= 12
    assert pagination_one["totalPages"] >= 2

    page_two = client.get("/api/v1/customers?page=2&page_size=10", headers=auth_headers)
    body_two = page_two.json()
    pagination_two = pagination_from(body_two)
    assert pagination_two["page"] == 2
    assert len(body_two["items"]) >= 2


def test_list_customers_filters_with_pagination(client, auth_headers):
    client.post(
        "/api/v1/customers",
        json={"display_name": "Filter Paginate Active", "status": "active"},
        headers=auth_headers,
    )
    archived = client.post(
        "/api/v1/customers",
        json={"display_name": "Filter Paginate Archived"},
        headers=auth_headers,
    )
    client.delete(f"/api/v1/customers/{archived.json()['id']}", headers=auth_headers)

    active_page = client.get(
        "/api/v1/customers?status=active&page=1&page_size=10",
        headers=auth_headers,
    )
    assert active_page.status_code == 200
    active_ids = {item["id"] for item in active_page.json()["items"]}
    assert archived.json()["id"] not in active_ids

    archived_page = client.get(
        "/api/v1/customers?status=archived&page=1&page_size=10",
        headers=auth_headers,
    )
    assert archived_page.status_code == 200
    assert pagination_from(archived_page.json())["page"] == 1
    assert any(item["status"] == "archived" for item in archived_page.json()["items"])


def test_list_customers_invalid_page_size_validation(client, auth_headers):
    response = client.get("/api/v1/customers?page_size=0", headers=auth_headers)
    assert response.status_code == 422

    response = client.get("/api/v1/customers?page_size=101", headers=auth_headers)
    assert response.status_code == 422

    response = client.get("/api/v1/customers?page=0", headers=auth_headers)
    assert response.status_code == 422


def test_customer_multi_email_normalized(client, auth_headers):
    create_response = client.post(
        "/api/v1/customers",
        json={
            "display_name": "Multi Email Co",
            "email": "info@abc.com ; sales@abc.com, info@abc.com , export@abc.com",
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    assert create_response.json()["email"] == "info@abc.com;sales@abc.com;export@abc.com"

    customer_id = create_response.json()["id"]
    get_response = client.get(f"/api/v1/customers/{customer_id}", headers=auth_headers)
    assert get_response.json()["email"] == "info@abc.com;sales@abc.com;export@abc.com"


def test_customer_invalid_multi_email_rejected(client, auth_headers):
    response = client.post(
        "/api/v1/customers",
        json={"display_name": "Bad Email Co", "email": "info@abc.com;sales@@abc.com"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "Invalid email address: sales@@abc.com" in response.json()["detail"]
