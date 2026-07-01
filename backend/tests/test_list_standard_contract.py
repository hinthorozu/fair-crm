"""Contract tests for ADR-015 standard list response shape."""

from tests.conftest_helpers import list_body, pagination_from


def test_customers_list_page_size_alias(client, auth_headers):
    for index in range(15):
        client.post(
            "/api/v1/customers",
            json={"display_name": f"Alias Page Customer {index:02d}"},
            headers=auth_headers,
        )

    response = client.get("/api/v1/customers?pageSize=10", headers=auth_headers)
    assert response.status_code == 200
    body = list_body(response.json())
    pagination = pagination_from(body)
    assert pagination["pageSize"] == 10
    assert len(body["items"]) == 10
    assert pagination["totalItems"] >= 15
    assert "items" in body
    assert "pagination" in body
    assert "sorting" in body
    assert "filters" in body
    assert body["sorting"]["field"]
    assert body["sorting"]["direction"] in ("asc", "desc")


def test_fairs_list_nested_pagination_shape(client, auth_headers):
    response = client.get("/api/v1/fairs", headers=auth_headers)
    assert response.status_code == 200
    body = list_body(response.json())
    pagination = pagination_from(body)
    assert pagination["page"] == 1
    assert pagination["pageSize"] == 25
    assert "totalItems" in pagination
    assert "totalPages" in pagination
    assert "hasNext" in pagination
    assert "hasPrevious" in pagination
    assert body["sorting"]["field"] == "start_date"
    assert body["sorting"]["direction"] == "desc"
