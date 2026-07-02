"""Customer list sort order tests (display name column)."""

def _create_customer(client, auth_headers, display_name: str) -> None:
    response = client.post(
        "/api/v1/customers",
        json={"display_name": display_name},
        headers=auth_headers,
    )
    assert response.status_code == 201


def test_list_customers_sort_by_company_name_asc(client, auth_headers):
    for name in ("Zulu Works", "Alpha Beta", "(10) Numbered Co", "Mike Industries"):
        _create_customer(client, auth_headers, name)

    response = client.get(
        "/api/v1/customers?sort_by=company_name&sort_order=asc&pageSize=100",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sorting"]["field"] == "name"
    assert body["sorting"]["direction"] == "asc"

    names = [item["display_name"] for item in body["items"]]
    assert names == sorted(names, key=str.casefold)


def test_list_customers_sort_by_name_desc(client, auth_headers):
    for name in ("Zulu Works", "Alpha Beta", "Mike Industries"):
        _create_customer(client, auth_headers, name)

    response = client.get(
        "/api/v1/customers?sort_by=name&sort_order=desc&pageSize=100",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sorting"]["field"] == "name"
    assert body["sorting"]["direction"] == "desc"

    names = [item["display_name"] for item in body["items"]]
    assert names == sorted(names, key=str.casefold, reverse=True)


def test_list_customers_sort_by_display_name_maps_to_name_in_response(client, auth_headers):
    _create_customer(client, auth_headers, "Sort Field Co")

    response = client.get(
        "/api/v1/customers?sort_by=display_name&sort_order=asc",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["sorting"]["field"] == "name"


def test_list_customers_sort_by_created_at_asc(client, auth_headers):
    for name in ("Created First", "Created Second", "Created Third"):
        _create_customer(client, auth_headers, name)

    response = client.get(
        "/api/v1/customers?sort_by=created_at&sort_order=asc&pageSize=100",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sorting"]["field"] == "created_at"
    assert body["sorting"]["direction"] == "asc"

    timestamps = [item["created_at"] for item in body["items"] if item["display_name"].startswith("Created ")]
    assert len(timestamps) == 3
    assert timestamps == sorted(timestamps)


def test_list_customers_sort_by_created_at_desc(client, auth_headers):
    for name in ("Date Desc A", "Date Desc B", "Date Desc C"):
        _create_customer(client, auth_headers, name)

    response = client.get(
        "/api/v1/customers?sort_by=created_at&sort_order=desc&pageSize=100",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sorting"]["field"] == "created_at"
    assert body["sorting"]["direction"] == "desc"

    timestamps = [item["created_at"] for item in body["items"] if item["display_name"].startswith("Date Desc ")]
    assert len(timestamps) == 3
    assert timestamps == sorted(timestamps, reverse=True)
