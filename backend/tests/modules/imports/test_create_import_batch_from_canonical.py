"""Tests for creating import batches from canonical JSON handoff."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.customers.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)


def _create_fair(client, auth_headers, name="Canonical Fair"):
    response = client.post(
        "/api/v1/fairs",
        headers=auth_headers,
        json={
            "name": name,
            "location": "Istanbul",
            "start_date": "2026-06-05",
            "end_date": "2026-06-08",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _canonical_payload(*, fair_id: str, run_id: str | None = None, rows: list | None = None):
    run_uuid = run_id or str(uuid4())
    default_rows = [
        {
            "external_id": None,
            "company_name": "ABC LTD",
            "normalized_company_name": "abc",
            "website": "https://abc.com",
            "emails": ["info@abc.com"],
            "phones": ["+902121112233"],
            "country": "Türkiye",
            "city": "İstanbul",
            "hall": "2",
            "stand": "A-12",
            "raw": {"category": "Gıda"},
        }
    ]
    row_list = default_rows if rows is None else rows
    return {
        "source": {
            "type": "scraper",
            "adapter_key": "tuyap_new",
            "fair_id": fair_id,
            "run_id": run_uuid,
            "source_url": "https://foodist.test/brands",
        },
        "metadata": {
            "created_at": datetime(2026, 7, 4, 12, 0, tzinfo=UTC).isoformat(),
            "row_count": len(row_list),
        },
        "rows": row_list,
    }


def test_create_import_batch_from_canonical_creates_batch_and_rows(
    client, auth_headers, db_session, organization_id
):
    fair_id = _create_fair(client, auth_headers)
    payload = _canonical_payload(fair_id=fair_id)

    response = client.post("/api/v1/imports/from-canonical", headers=auth_headers, json=payload)
    assert response.status_code == 201

    data = response.json()
    batch = data["batch"]
    assert data["row_count"] == 1
    assert batch["fair_id"] == fair_id
    assert batch["source_type"] == "scraper"
    assert batch["status"] == "received"
    assert batch["total_rows"] == 1
    assert batch["valid_rows"] == 1
    assert batch["file_name"].endswith(".json")

    rows_response = client.get(f"/api/v1/imports/{batch['id']}/rows", headers=auth_headers)
    assert rows_response.status_code == 200
    rows_body = rows_response.json()
    assert len(rows_body["items"]) == 1
    row = rows_body["items"][0]
    assert row["row_number"] == 1
    assert row["status"] == "valid"
    assert row["raw_data_json"]["company_name"] == "ABC LTD"
    assert row["normalized_data_json"]["company_name"] == "ABC LTD"
    assert row["normalized_data_json"]["emails"] == ["info@abc.com"]

    customer_repo = SqlAlchemyCustomerRepository(db_session)
    assert customer_repo.list_all_active(organization_id) == []


def test_create_import_batch_from_canonical_accepts_empty_rows(client, auth_headers):
    fair_id = _create_fair(client, auth_headers)
    payload = _canonical_payload(fair_id=fair_id, rows=[])

    response = client.post("/api/v1/imports/from-canonical", headers=auth_headers, json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["row_count"] == 0
    assert data["batch"]["total_rows"] == 0
    assert data["batch"]["status"] == "received"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"source": {"type": "scraper"}, "metadata": {}, "rows": []},
        {
            "source": {"type": "unknown", "adapter_key": "x"},
            "metadata": {"created_at": "2026-07-04T12:00:00Z", "row_count": 1},
            "rows": [
                {
                    "company_name": "X",
                    "normalized_company_name": "x",
                    "emails": [],
                    "phones": [],
                    "raw": {},
                }
            ],
        },
    ],
)
def test_create_import_batch_from_canonical_rejects_invalid_payload(client, auth_headers, payload):
    response = client.post("/api/v1/imports/from-canonical", headers=auth_headers, json=payload)
    assert response.status_code == 400


def test_create_import_batch_from_canonical_requires_fair_id(client, auth_headers):
    payload = _canonical_payload(fair_id=str(uuid4()))
    payload["source"]["fair_id"] = None

    response = client.post("/api/v1/imports/from-canonical", headers=auth_headers, json=payload)
    assert response.status_code == 400
    assert "fair_id" in response.json()["detail"].lower()


def test_create_import_batch_from_canonical_rejects_unknown_fair(client, auth_headers):
    payload = _canonical_payload(fair_id=str(uuid4()))

    response = client.post("/api/v1/imports/from-canonical", headers=auth_headers, json=payload)
    assert response.status_code == 404


def test_create_import_batch_from_canonical_maps_social_urls(client, auth_headers):
    fair_id = _create_fair(client, auth_headers, name="Social Import Fair")
    rows = [
        {
            "external_id": None,
            "company_name": "Social Import Co",
            "normalized_company_name": "social import co",
            "website": None,
            "emails": [],
            "phones": [],
            "country": "Türkiye",
            "city": None,
            "hall": None,
            "stand": None,
            "instagram_url": "https://instagram.com/socialimport",
            "facebook_url": None,
            "linkedin_url": "https://linkedin.com/company/socialimport",
            "youtube_url": None,
            "raw": {},
        }
    ]
    payload = _canonical_payload(fair_id=fair_id, rows=rows)
    response = client.post("/api/v1/imports/from-canonical", headers=auth_headers, json=payload)
    assert response.status_code == 201

    batch_id = response.json()["batch"]["id"]
    rows_response = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers)
    normalized = rows_response.json()["items"][0]["normalized_data_json"]
    assert normalized["instagram_url"] == "https://instagram.com/socialimport"
    assert normalized["linkedin_url"] == "https://linkedin.com/company/socialimport"
