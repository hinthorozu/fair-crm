"""Data Integration API tests (Sprint 09.1)."""

from io import BytesIO

from openpyxl import Workbook


def _xlsx(rows: list[list[str]], headers: list[str] | None = None) -> bytes:
    wb = Workbook()
    ws = wb.active
    if headers:
        ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _fair_id(client, auth_headers) -> str:
    res = client.post(
        "/api/v1/fairs",
        headers=auth_headers,
        json={"name": "DI Fair", "location": "Istanbul", "start_date": "2026-06-01", "end_date": "2026-06-03"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def test_data_integration_upload_and_list(client, auth_headers):
    fair_id = _fair_id(client, auth_headers)
    content = _xlsx([["Acme Ltd", "info@acme.com"]], headers=["Company", "Email"])
    upload = client.post(
        "/api/v1/data-integration/imports/upload",
        headers=auth_headers,
        data={"fair_id": fair_id},
        files={"file": ("test.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert upload.status_code == 201
    body = upload.json()
    assert body["available_sheets"]
    batch_id = body["batch_id"]

    listing = client.get("/api/v1/data-integration/imports", headers=auth_headers)
    assert listing.status_code == 200
    data = listing.json()
    assert data["pagination"]["totalItems"] >= 1
    assert any(item["id"] == batch_id for item in data["items"])


def test_header_mode_no_header_mapping(client, auth_headers):
    fair_id = _fair_id(client, auth_headers)
    content = _xlsx([["Beta Corp", "beta@test.com"], ["Gamma Inc", "g@test.com"]])
    upload = client.post(
        "/api/v1/data-integration/imports/upload",
        headers=auth_headers,
        data={"fair_id": fair_id},
        files={"file": ("noheader.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert upload.status_code == 201
    batch_id = upload.json()["batch_id"]

    mapping = client.patch(
        f"/api/v1/data-integration/imports/{batch_id}/column-mapping",
        headers=auth_headers,
        json={
            "header_mode": "no_header",
            "has_header_row": False,
            "mappings": {
                "company_name": {"type": "column_index", "value": 0},
                "email": {"type": "column_index", "value": 1},
            },
        },
    )
    assert mapping.status_code == 200
    assert mapping.json()["column_mapping"]["header_mode"] == "no_header"

    analyze = client.post(f"/api/v1/data-integration/imports/{batch_id}/analyze", headers=auth_headers)
    assert analyze.status_code == 200
    assert analyze.json()["total_rows"] == 2


def test_apply_job_completes(client, auth_headers):
    fair_id = _fair_id(client, auth_headers)
    content = _xlsx([["Job Test Co", "job@test.com"]], headers=["Company", "Email"])
    upload = client.post(
        "/api/v1/data-integration/imports/upload",
        headers=auth_headers,
        data={"fair_id": fair_id},
        files={"file": ("job.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert upload.status_code == 201
    batch_id = upload.json()["batch_id"]

    client.patch(
        f"/api/v1/data-integration/imports/{batch_id}/column-mapping",
        headers=auth_headers,
        json={
            "header_mode": "first_row_header",
            "has_header_row": True,
            "mappings": {
                "company_name": {"type": "column_index", "value": 0},
                "email": {"type": "column_index", "value": 1},
            },
        },
    ).raise_for_status()
    client.post(f"/api/v1/data-integration/imports/{batch_id}/analyze", headers=auth_headers).raise_for_status()

    job_res = client.post(
        f"/api/v1/data-integration/imports/{batch_id}/apply-job",
        headers=auth_headers,
    )
    assert job_res.status_code == 202
    job_id = job_res.json()["job_id"]

    status_res = client.get(f"/api/v1/data-integration/jobs/{job_id}", headers=auth_headers)
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "completed"
    assert status_res.json()["result_json"]["created_rows"] == 1
