"""Decision screen filter counts on import row list."""

from io import BytesIO

from openpyxl import Workbook

from tests.conftest_helpers import pagination_from


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
        json={"name": "Counts Fair", "location": "Istanbul", "start_date": "2026-06-01", "end_date": "2026-06-03"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _upload_and_analyze(client, auth_headers, fair_id: str, data_rows: list[list[str]]) -> str:
    content = _xlsx(data_rows, headers=["Firma"])
    upload = client.post(
        "/api/v1/data-integration/imports/upload",
        headers=auth_headers,
        data={"fair_id": fair_id},
        files={"file": ("counts.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert upload.status_code == 201
    batch_id = upload.json()["batch_id"]
    client.patch(
        f"/api/v1/data-integration/imports/{batch_id}/sheet",
        headers=auth_headers,
        json={"sheet_name": upload.json()["selected_sheet_name"]},
    )
    client.patch(
        f"/api/v1/data-integration/imports/{batch_id}/header-config",
        headers=auth_headers,
        json={"has_header_row": True, "header_mode": "first_row_header", "header_row_index": 0},
    )
    client.patch(
        f"/api/v1/data-integration/imports/{batch_id}/column-mapping",
        headers=auth_headers,
        json={
            "has_header_row": True,
            "header_mode": "first_row_header",
            "header_row_index": 0,
            "mappings": {"company_name": {"type": "column_index", "value": 0}},
        },
    )
    analyze = client.post(
        f"/api/v1/data-integration/imports/{batch_id}/analyze-job",
        headers=auth_headers,
    )
    assert analyze.status_code == 202
    job_id = analyze.json()["job_id"]
    for _ in range(60):
        job = client.get(f"/api/v1/data-integration/jobs/{job_id}", headers=auth_headers)
        if job.json()["status"] == "completed":
            break
    return batch_id


def test_row_list_includes_filter_counts(client, auth_headers):
    fair_id = _fair_id(client, auth_headers)
    batch_id = _upload_and_analyze(
        client,
        auth_headers,
        fair_id,
        [["New Co"], ["Dup Co"], [""]],
    )

    response = client.get(
        f"/api/v1/data-integration/imports/{batch_id}/rows",
        headers=auth_headers,
        params={"filter": "pending", "page_size": 25},
    )
    assert response.status_code == 200
    body = response.json()
    assert "counts" in body
    counts = body["counts"]
    assert counts["all"] >= 2
    assert counts["pending"] >= 1
    assert counts["pending"] == pagination_from(body)["totalItems"]
    assert counts["applied"] == 0

    new_list = client.get(
        f"/api/v1/data-integration/imports/{batch_id}/rows",
        headers=auth_headers,
        params={"filter": "new", "page_size": 100},
    )
    assert new_list.status_code == 200
    assert new_list.json()["counts"]["new"] == pagination_from(new_list.json())["totalItems"]
    assert new_list.json()["counts"]["all"] == counts["all"]


def test_filter_counts_update_after_bulk_apply(client, auth_headers):
    fair_id = _fair_id(client, auth_headers)
    batch_id = _upload_and_analyze(client, auth_headers, fair_id, [["Alpha"], ["Beta"]])

    before = client.get(
        f"/api/v1/data-integration/imports/{batch_id}/rows",
        headers=auth_headers,
        params={"filter": "pending", "page_size": 25},
    ).json()
    pending_before = before["counts"]["pending"]
    applied_before = before["counts"]["applied"]
    assert pending_before >= 1

    apply = client.post(
        f"/api/v1/data-integration/imports/{batch_id}/bulk-actions/apply",
        headers=auth_headers,
        json={"action_type": "create_all_new"},
    )
    assert apply.status_code == 202
    job_id = apply.json()["job_id"]
    for _ in range(60):
        job = client.get(f"/api/v1/data-integration/jobs/{job_id}", headers=auth_headers)
        if job.json()["status"] == "completed":
            break

    after = client.get(
        f"/api/v1/data-integration/imports/{batch_id}/rows",
        headers=auth_headers,
        params={"filter": "pending", "page_size": 25},
    ).json()
    assert after["counts"]["pending"] < pending_before
    assert after["counts"]["applied"] > applied_before
    assert after["counts"]["new"] == 0
