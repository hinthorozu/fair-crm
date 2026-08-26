"""TI-09 final adversarial tenant-isolation certification gaps."""

from io import BytesIO

from openpyxl import Workbook

from tests.conftest_helpers import pagination_from


def _xlsx(company_name: str) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Firma Adı"])
    sheet.append([company_name])
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _upload_import_batch(client, headers, company_name: str) -> tuple[str, str]:
    response = client.post(
        "/api/v1/imports/customers/upload",
        headers=headers,
        files={
            "file": (
                "tenant-certification.xlsx",
                _xlsx(company_name),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 201, response.text
    batch_id = response.json()["id"]
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=headers)
    assert rows.status_code == 200, rows.text
    return batch_id, rows.json()["items"][0]["id"]


def _create_customer(client, headers, name: str) -> str:
    response = client.post(
        "/api/v1/customers",
        headers=headers,
        json={"display_name": name, "status": "active"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_fair(client, headers, name: str) -> str:
    response = client.post(
        "/api/v1/fairs",
        headers=headers,
        json={"name": name, "status": "planned"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_mixed_organization_bulk_row_ids_fail_closed(
    client,
    auth_headers,
    other_organization_id,
):
    owner_batch_id, owner_row_id = _upload_import_batch(
        client,
        auth_headers,
        "Owner Bulk Row",
    )
    foreign_headers = {**auth_headers, "X-Organization-Id": str(other_organization_id)}
    foreign_batch_id, foreign_row_id = _upload_import_batch(
        client,
        foreign_headers,
        "Foreign Bulk Row",
    )

    response = client.patch(
        f"/api/v1/imports/{owner_batch_id}/rows/bulk-decision",
        headers=auth_headers,
        json={
            "row_ids": [owner_row_id, foreign_row_id],
            "decision": "create_new",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["updated_count"] == 1
    assert body["skipped_count"] == 1
    assert [item["row_id"] for item in body["errors"]] == [foreign_row_id]

    owner_rows = client.get(
        f"/api/v1/imports/{owner_batch_id}/rows",
        headers=auth_headers,
    ).json()["items"]
    foreign_rows = client.get(
        f"/api/v1/imports/{foreign_batch_id}/rows",
        headers=foreign_headers,
    ).json()["items"]
    assert owner_rows[0]["decision"] == "create_new"
    assert foreign_rows[0]["decision"] is None


def test_participation_bulk_move_rejects_foreign_target_fair(
    client,
    auth_headers,
    other_organization_id,
):
    source_fair_id = _create_fair(client, auth_headers, "Owner Source Fair")
    owner_customer_id = _create_customer(client, auth_headers, "Owner Move Customer")
    created = client.post(
        "/api/v1/fair-participations",
        headers=auth_headers,
        json={"customer_id": owner_customer_id, "fair_id": source_fair_id},
    )
    assert created.status_code == 201, created.text

    foreign_headers = {**auth_headers, "X-Organization-Id": str(other_organization_id)}
    foreign_target_id = _create_fair(client, foreign_headers, "Foreign Target Fair")

    moved = client.post(
        f"/api/v1/fairs/{source_fair_id}/participants/move-to-fair",
        headers=auth_headers,
        json={"target_fair_id": foreign_target_id},
    )
    assert moved.status_code == 404, moved.text

    owner_source = client.get(
        f"/api/v1/fairs/{source_fair_id}/participants",
        headers=auth_headers,
    )
    foreign_target = client.get(
        f"/api/v1/fairs/{foreign_target_id}/participants",
        headers=foreign_headers,
    )
    assert owner_source.status_code == 200
    assert foreign_target.status_code == 200
    assert pagination_from(owner_source.json())["totalItems"] == 1
    assert pagination_from(foreign_target.json())["totalItems"] == 0


def test_body_and_query_organization_spoof_do_not_override_trusted_context(
    client,
    auth_headers,
    organization_id,
    other_organization_id,
):
    response = client.post(
        f"/api/v1/customers?organization_id={other_organization_id}",
        headers=auth_headers,
        json={
            "display_name": "Spoof-Proof Customer",
            "organization_id": str(other_organization_id),
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["organization_id"] == str(organization_id)

    foreign_headers = {**auth_headers, "X-Organization-Id": str(other_organization_id)}
    foreign_lookup = client.get(
        f"/api/v1/customers/{body['id']}",
        headers=foreign_headers,
    )
    assert foreign_lookup.status_code == 404


def test_missing_organization_context_fails_closed(client, auth_headers):
    headers_without_organization = {
        key: value
        for key, value in auth_headers.items()
        if key.lower() != "x-organization-id"
    }
    response = client.get(
        "/api/v1/customers",
        headers=headers_without_organization,
    )
    assert response.status_code == 422
