from tests.conftest_helpers import pagination_from


def test_create_and_get_fair(client, auth_headers, organization_id):
    create_response = client.post(
        "/api/v1/fairs",
        json={
            "name": "İstanbul Teknoloji Fuarı 2026",
            "organizer": "Teknova Fuarcılık",
            "venue": "İstanbul Fuar Merkezi",
            "city": "İstanbul",
            "country": "Türkiye",
            "start_date": "2026-03-15",
            "end_date": "2026-03-18",
            "website": "https://www.teknova-fuar.com/about",
            "status": "planned",
            "description": "Yıllık teknoloji fuarı",
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["name"] == "İstanbul Teknoloji Fuarı 2026"
    assert body["normalized_name"] == "ISTANBUL TEKNOLOJI FUARI 2026"
    assert body["website"] == "teknova-fuar.com"
    assert body["city"] == "İstanbul"
    assert body["start_date"] == "2026-03-15"
    assert body["end_date"] == "2026-03-18"
    assert body["organization_id"] == str(organization_id)

    fair_id = body["id"]
    get_response = client.get(f"/api/v1/fairs/{fair_id}", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()["id"] == fair_id


def test_list_fairs_search(client, auth_headers):
    client.post(
        "/api/v1/fairs",
        json={
            "name": "Search Target Fair",
            "venue": "Unique Venue Hall 42",
        },
        headers=auth_headers,
    )

    response = client.get("/api/v1/fairs?search=Unique+Venue", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()["items"]) >= 1


def test_update_fair(client, auth_headers):
    create_response = client.post(
        "/api/v1/fairs",
        json={"name": "Before Update Fair"},
        headers=auth_headers,
    )
    fair_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/fairs/{fair_id}",
        json={"name": "After Update Fair", "status": "active"},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "After Update Fair"
    assert update_response.json()["status"] == "active"


def test_archive_fair(client, auth_headers):
    create_response = client.post(
        "/api/v1/fairs",
        json={"name": "To Archive Fair"},
        headers=auth_headers,
    )
    fair_id = create_response.json()["id"]

    archive_response = client.delete(f"/api/v1/fairs/{fair_id}", headers=auth_headers)
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "archived"
    assert archive_response.json()["deleted_at"] is not None

    get_response = client.get(f"/api/v1/fairs/{fair_id}", headers=auth_headers)
    assert get_response.status_code == 404

    list_response = client.get("/api/v1/fairs?status=archived", headers=auth_headers)
    assert list_response.status_code == 200
    archived_items = list_response.json()["items"]
    assert any(item["id"] == fair_id for item in archived_items)
    assert archived_items[0]["status"] == "archived"


def test_archived_included_in_default_list(client, auth_headers):
    create_response = client.post(
        "/api/v1/fairs",
        json={"name": "Visible In All Fair", "status": "active"},
        headers=auth_headers,
    )
    fair_id = create_response.json()["id"]
    client.delete(f"/api/v1/fairs/{fair_id}", headers=auth_headers)

    default_list = client.get("/api/v1/fairs", headers=auth_headers)
    assert default_list.status_code == 200
    archived = [item for item in default_list.json()["items"] if item["id"] == fair_id]
    assert len(archived) == 1
    assert archived[0]["status"] == "archived"


def test_active_filter_excludes_archived(client, auth_headers):
    active_response = client.post(
        "/api/v1/fairs",
        json={"name": "Active Only Fair", "status": "active"},
        headers=auth_headers,
    )
    active_id = active_response.json()["id"]

    archived_response = client.post(
        "/api/v1/fairs",
        json={"name": "Archived Only Fair", "status": "planned"},
        headers=auth_headers,
    )
    archived_id = archived_response.json()["id"]
    client.delete(f"/api/v1/fairs/{archived_id}", headers=auth_headers)

    active_list = client.get("/api/v1/fairs?status=active", headers=auth_headers)
    ids = {item["id"] for item in active_list.json()["items"]}
    assert active_id in ids
    assert archived_id not in ids


def test_restore_visible_in_default_list_not_in_archived_filter(client, auth_headers):
    create_response = client.post(
        "/api/v1/fairs",
        json={"name": "Restore All View Fair", "status": "completed"},
        headers=auth_headers,
    )
    fair_id = create_response.json()["id"]
    client.delete(f"/api/v1/fairs/{fair_id}", headers=auth_headers)

    restore_response = client.post(
        f"/api/v1/fairs/{fair_id}/restore",
        headers=auth_headers,
    )
    assert restore_response.status_code == 200

    archived_list = client.get("/api/v1/fairs?status=archived", headers=auth_headers)
    assert not any(item["id"] == fair_id for item in archived_list.json()["items"])

    default_list = client.get("/api/v1/fairs", headers=auth_headers)
    restored = [item for item in default_list.json()["items"] if item["id"] == fair_id]
    assert len(restored) == 1
    assert restored[0]["status"] == "completed"


def test_org_isolation_api(client, auth_headers, other_organization_id, user_id):
    from app.integrations.kyrox_core.auth import create_test_token

    create_response = client.post(
        "/api/v1/fairs",
        json={"name": "Private Fair"},
        headers=auth_headers,
    )
    fair_id = create_response.json()["id"]

    other_headers = {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(other_organization_id),
    }
    get_response = client.get(f"/api/v1/fairs/{fair_id}", headers=other_headers)
    assert get_response.status_code == 404


def test_unauthenticated_returns_401(client, organization_id):
    response = client.get(
        "/api/v1/fairs",
        headers={"X-Organization-Id": str(organization_id)},
    )
    assert response.status_code == 401


def test_restore_fair(client, auth_headers):
    create_response = client.post(
        "/api/v1/fairs",
        json={"name": "Restore Me Fair", "status": "planned"},
        headers=auth_headers,
    )
    fair_id = create_response.json()["id"]

    archive_response = client.delete(f"/api/v1/fairs/{fair_id}", headers=auth_headers)
    assert archive_response.status_code == 200

    archived_list = client.get("/api/v1/fairs?status=archived", headers=auth_headers)
    assert any(item["id"] == fair_id for item in archived_list.json()["items"])

    restore_response = client.post(
        f"/api/v1/fairs/{fair_id}/restore",
        headers=auth_headers,
    )
    assert restore_response.status_code == 200
    body = restore_response.json()
    assert body["status"] == "planned"
    assert body["deleted_at"] is None

    archived_after = client.get("/api/v1/fairs?status=archived", headers=auth_headers)
    assert not any(item["id"] == fair_id for item in archived_after.json()["items"])

    default_list = client.get("/api/v1/fairs", headers=auth_headers)
    assert any(item["id"] == fair_id for item in default_list.json()["items"])

    get_response = client.get(f"/api/v1/fairs/{fair_id}", headers=auth_headers)
    assert get_response.status_code == 200


def test_restore_non_archived_fair_fails(client, auth_headers):
    create_response = client.post(
        "/api/v1/fairs",
        json={"name": "Active Fair"},
        headers=auth_headers,
    )
    fair_id = create_response.json()["id"]

    restore_response = client.post(
        f"/api/v1/fairs/{fair_id}/restore",
        headers=auth_headers,
    )
    assert restore_response.status_code == 400
    assert restore_response.json()["detail"] == "Fair is not archived"


def test_restore_fair_wrong_org_returns_404(
    client, auth_headers, other_organization_id, user_id
):
    from app.integrations.kyrox_core.auth import create_test_token

    create_response = client.post(
        "/api/v1/fairs",
        json={"name": "Org Scoped Restore Fair"},
        headers=auth_headers,
    )
    fair_id = create_response.json()["id"]
    client.delete(f"/api/v1/fairs/{fair_id}", headers=auth_headers)

    other_headers = {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(other_organization_id),
    }
    restore_response = client.post(
        f"/api/v1/fairs/{fair_id}/restore",
        headers=other_headers,
    )
    assert restore_response.status_code == 404


def test_list_fairs_default_pagination(client, auth_headers):
    response = client.get("/api/v1/fairs", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    pagination = pagination_from(body)
    assert pagination["page"] == 1
    assert pagination["pageSize"] == 25
    assert "totalItems" in pagination
    assert "totalPages" in pagination
    assert isinstance(body["items"], list)


def test_list_fairs_custom_page_size_and_page_two(client, auth_headers):
    for index in range(12):
        client.post(
            "/api/v1/fairs",
            json={"name": f"Paged Fair {index:02d}"},
            headers=auth_headers,
        )

    page_one = client.get("/api/v1/fairs?page=1&page_size=10", headers=auth_headers)
    assert page_one.status_code == 200
    body_one = page_one.json()
    pagination_one = pagination_from(body_one)
    assert len(body_one["items"]) == 10
    assert pagination_one["page"] == 1
    assert pagination_one["pageSize"] == 10
    assert pagination_one["totalItems"] >= 12
    assert pagination_one["totalPages"] >= 2

    page_two = client.get("/api/v1/fairs?page=2&page_size=10", headers=auth_headers)
    body_two = page_two.json()
    pagination_two = pagination_from(body_two)
    assert pagination_two["page"] == 2
    assert len(body_two["items"]) >= 2


def test_list_fairs_filters_with_pagination(client, auth_headers):
    client.post(
        "/api/v1/fairs",
        json={"name": "Filter Paginate Active Fair", "status": "active"},
        headers=auth_headers,
    )
    archived = client.post(
        "/api/v1/fairs",
        json={"name": "Filter Paginate Archived Fair"},
        headers=auth_headers,
    )
    client.delete(f"/api/v1/fairs/{archived.json()['id']}", headers=auth_headers)

    active_page = client.get(
        "/api/v1/fairs?status=active&page=1&page_size=10",
        headers=auth_headers,
    )
    assert active_page.status_code == 200
    active_ids = {item["id"] for item in active_page.json()["items"]}
    assert archived.json()["id"] not in active_ids

    archived_page = client.get(
        "/api/v1/fairs?status=archived&page=1&page_size=10",
        headers=auth_headers,
    )
    assert archived_page.status_code == 200
    assert pagination_from(archived_page.json())["page"] == 1
    assert any(item["status"] == "archived" for item in archived_page.json()["items"])


def test_list_fairs_invalid_page_size_validation(client, auth_headers):
    response = client.get("/api/v1/fairs?page_size=0", headers=auth_headers)
    assert response.status_code == 422

    response = client.get("/api/v1/fairs?page_size=101", headers=auth_headers)
    assert response.status_code == 422

    response = client.get("/api/v1/fairs?page=0", headers=auth_headers)
    assert response.status_code == 422


def test_list_fairs_sort_by_name(client, auth_headers):
    client.post(
        "/api/v1/fairs",
        json={"name": "Zebra Fair"},
        headers=auth_headers,
    )
    client.post(
        "/api/v1/fairs",
        json={"name": "Alpha Fair"},
        headers=auth_headers,
    )

    asc_response = client.get(
        "/api/v1/fairs?sort_by=name&sort_dir=asc&page_size=100",
        headers=auth_headers,
    )
    assert asc_response.status_code == 200
    names = [item["name"] for item in asc_response.json()["items"]]
    assert names.index("Alpha Fair") < names.index("Zebra Fair")


def test_create_fair_invalid_date_range(client, auth_headers):
    response = client.post(
        "/api/v1/fairs",
        json={
            "name": "Invalid Dates Fair",
            "start_date": "2026-06-01",
            "end_date": "2026-05-01",
        },
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "end_date" in response.json()["detail"]


def test_create_fair_empty_name_validation(client, auth_headers):
    response = client.post(
        "/api/v1/fairs",
        json={"name": "   "},
        headers=auth_headers,
    )
    assert response.status_code == 422 or response.status_code == 400


def test_create_fair_without_adapter_fields(client, auth_headers):
    response = client.post(
        "/api/v1/fairs",
        json={"name": "Plain Fair Without Adapter"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["adapter_key"] is None
    assert body["source_url"] is None
    assert body["scraper_config"] is None


def test_create_fair_with_adapter_and_source_url(client, auth_headers):
    response = client.post(
        "/api/v1/fairs",
        json={
            "name": "Foodist 2026",
            "adapter_key": "tuyap_new",
            "source_url": "https://www.foodistexpo.com/katilimci-listesi",
            "scraper_config": {"pagination": {"page_size": 50}},
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["adapter_key"] == "tuyap_new"
    assert body["source_url"] == "https://www.foodistexpo.com/katilimci-listesi"
    assert body["scraper_config"] == {"pagination": {"page_size": 50}}


def test_create_fair_adapter_without_source_url_validation(client, auth_headers):
    response = client.post(
        "/api/v1/fairs",
        json={
            "name": "Invalid Adapter Fair",
            "adapter_key": "tuyap_new",
        },
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "source_url" in response.json()["detail"]


def test_create_fair_invalid_source_url_validation(client, auth_headers):
    response = client.post(
        "/api/v1/fairs",
        json={
            "name": "Invalid Source URL Fair",
            "source_url": "not-a-valid-url",
        },
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "source_url" in response.json()["detail"]


def test_create_fair_defaults_status_to_planned(client, auth_headers):
    response = client.post(
        "/api/v1/fairs",
        json={"name": "Default Status Fair"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["status"] == "planned"


def test_update_fair_clears_optional_fields_with_null(client, auth_headers):
    create_response = client.post(
        "/api/v1/fairs",
        json={
            "name": "Clear Fields Fair",
            "organizer": "Old Org",
            "venue": "Old Venue",
            "city": "İstanbul",
            "country": "Türkiye",
            "website": "https://www.old-fair.com",
            "description": "Old description",
            "start_date": "2026-03-15",
            "end_date": "2026-03-18",
            "adapter_key": "tuyap_new",
            "source_url": "https://example.com/list",
            "scraper_config": {"pagination": {"page_size": 10}},
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    fair_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/fairs/{fair_id}",
        json={
            "organizer": None,
            "venue": None,
            "city": None,
            "country": None,
            "website": None,
            "description": None,
            "start_date": None,
            "end_date": None,
            "adapter_key": None,
            "source_url": None,
            "scraper_config": None,
        },
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    body = update_response.json()
    assert body["organizer"] is None
    assert body["venue"] is None
    assert body["city"] is None
    assert body["country"] is None
    assert body["website"] is None
    assert body["description"] is None
    assert body["start_date"] is None
    assert body["end_date"] is None
    assert body["adapter_key"] is None
    assert body["source_url"] is None
    assert body["scraper_config"] is None


def test_update_fair_omitted_fields_are_preserved(client, auth_headers):
    create_response = client.post(
        "/api/v1/fairs",
        json={
            "name": "Omit Fields Fair",
            "organizer": "Keep Me",
            "website": "https://keep.example",
            "start_date": "2026-05-01",
        },
        headers=auth_headers,
    )
    fair_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/fairs/{fair_id}",
        json={"name": "Omit Fields Fair Renamed"},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    body = update_response.json()
    assert body["name"] == "Omit Fields Fair Renamed"
    assert body["organizer"] == "Keep Me"
    assert body["website"] == "keep.example"
    assert body["start_date"] == "2026-05-01"


def test_create_fair_accepts_protocol_less_website(client, auth_headers):
    for website in ("abc.com", "www.abc.com", "http://abc.com", "https://abc.com"):
        response = client.post(
            "/api/v1/fairs",
            json={"name": f"Website Fair {website}", "website": website},
            headers=auth_headers,
        )
        assert response.status_code == 201, website
        assert response.json()["website"] == "abc.com"


def test_create_fair_rejects_invalid_website(client, auth_headers):
    response = client.post(
        "/api/v1/fairs",
        json={"name": "Bad Website Fair", "website": "not a url"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "website" in response.json()["detail"]


def test_create_fair_future_dates_force_planned_even_if_status_wrong(client, auth_headers):
    response = client.post(
        "/api/v1/fairs",
        json={
            "name": "Future Force Planned Fair",
            "status": "completed",
            "start_date": "2099-06-01",
            "end_date": "2099-06-04",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["status"] == "planned"


def test_update_fair_auto_plans_when_future_start_date_set(client, auth_headers):
    create_response = client.post(
        "/api/v1/fairs",
        json={"name": "Auto Plan Fair", "status": "completed"},
        headers=auth_headers,
    )
    fair_id = create_response.json()["id"]
    assert create_response.json()["status"] == "completed"

    update_response = client.patch(
        f"/api/v1/fairs/{fair_id}",
        json={"start_date": "2099-01-15", "end_date": "2099-01-18"},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "planned"
    assert update_response.json()["start_date"] == "2099-01-15"


def test_update_fair_auto_plan_overrides_stale_client_status(client, auth_headers):
    create_response = client.post(
        "/api/v1/fairs",
        json={"name": "Stale Status Fair", "status": "completed"},
        headers=auth_headers,
    )
    fair_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/fairs/{fair_id}",
        json={
            "start_date": "2099-02-01",
            "end_date": "2099-02-04",
            "status": "cancelled",
        },
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "planned"


def test_update_fair_past_dates_do_not_auto_plan(client, auth_headers):
    create_response = client.post(
        "/api/v1/fairs",
        json={"name": "Past Dates Fair", "status": "completed"},
        headers=auth_headers,
    )
    fair_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/fairs/{fair_id}",
        json={"start_date": "2020-01-10", "end_date": "2020-01-12"},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "completed"


def test_update_fair_website_protocol_less_and_persists(client, auth_headers):
    create_response = client.post(
        "/api/v1/fairs",
        json={"name": "Website Edit Fair", "website": "https://old.example"},
        headers=auth_headers,
    )
    fair_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/fairs/{fair_id}",
        json={"website": "abc.com"},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["website"] == "abc.com"

    get_response = client.get(f"/api/v1/fairs/{fair_id}", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()["website"] == "abc.com"


def test_fair_detail_and_list_include_adapter_fields(client, auth_headers):
    create_response = client.post(
        "/api/v1/fairs",
        json={
            "name": "Adapter Fields List Fair",
            "adapter_key": "tuyap_new",
            "source_url": "https://foodist.example/list",
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    fair_id = create_response.json()["id"]

    detail_response = client.get(f"/api/v1/fairs/{fair_id}", headers=auth_headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["adapter_key"] == "tuyap_new"
    assert detail["source_url"] == "https://foodist.example/list"

    list_response = client.get("/api/v1/fairs?search=Adapter+Fields+List", headers=auth_headers)
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    matched = next(item for item in items if item["id"] == fair_id)
    assert matched["adapter_key"] == "tuyap_new"
    assert matched["source_url"] == "https://foodist.example/list"

