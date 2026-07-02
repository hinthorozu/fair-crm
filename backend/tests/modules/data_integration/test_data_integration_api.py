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

    analyze = client.post(
        f"/api/v1/data-integration/imports/{batch_id}/analyze-job",
        headers=auth_headers,
    )
    assert analyze.status_code == 202
    job_id = analyze.json()["job_id"]
    job = client.get(f"/api/v1/data-integration/jobs/{job_id}", headers=auth_headers)
    assert job.status_code == 200
    assert job.json()["status"] == "completed"
    batch = client.get(f"/api/v1/data-integration/imports/{batch_id}", headers=auth_headers)
    assert batch.status_code == 200
    analyze_body = {"batch": batch.json(), "total_rows": batch.json()["total_rows"]}
    assert analyze_body["total_rows"] == 2
    assert analyze_body["batch"]["status"] == "decision_required"

    rows = client.get(f"/api/v1/data-integration/imports/{batch_id}/rows", headers=auth_headers)
    assert rows.status_code == 200
    rows_body = rows.json()
    assert rows_body["pagination"]["totalItems"] == 2
    assert len(rows_body["items"]) == 2
    assert rows_body["items"][0]["normalized_data_json"]["company_name"] == "Beta Corp"


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
    analyze = client.post(
        f"/api/v1/data-integration/imports/{batch_id}/analyze-job",
        headers=auth_headers,
    )
    assert analyze.status_code == 202
    analyze_job_id = analyze.json()["job_id"]
    for _ in range(60):
        analyze_status = client.get(
            f"/api/v1/data-integration/jobs/{analyze_job_id}",
            headers=auth_headers,
        )
        if analyze_status.json()["status"] == "completed":
            break

    job_res = client.post(
        f"/api/v1/data-integration/imports/{batch_id}/bulk-actions/apply",
        headers=auth_headers,
        json={"action_type": "create_all_new"},
    )
    assert job_res.status_code == 202
    job_id = job_res.json()["job_id"]

    status_res = client.get(f"/api/v1/data-integration/jobs/{job_id}", headers=auth_headers)
    for _ in range(60):
        status_res = client.get(f"/api/v1/data-integration/jobs/{job_id}", headers=auth_headers)
        if status_res.json()["status"] == "completed":
            break
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "completed"
    assert status_res.json()["result_json"]["processed_rows"] >= 1

    batch = client.get(f"/api/v1/data-integration/imports/{batch_id}", headers=auth_headers)
    assert batch.status_code == 200
    assert batch.json()["created_rows"] >= 1
    assert batch.json()["status"] == "completed"
