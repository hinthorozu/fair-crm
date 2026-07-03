"""Apply saved import row decisions (selection or filter scope)."""

from io import BytesIO

from openpyxl import Workbook

from tests.modules.imports.import_decision_helpers import apply_import_decisions


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
        json={"name": "Apply Fair", "location": "Istanbul", "start_date": "2026-06-01", "end_date": "2026-06-03"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _upload_and_analyze(client, auth_headers, fair_id: str, rows: list[list[str]]) -> str:
    content = _xlsx(rows, headers=["Firma"])
    upload = client.post(
        "/api/v1/data-integration/imports/upload",
        headers=auth_headers,
        data={"fair_id": fair_id},
        files={"file": ("apply.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
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


def test_apply_selected_rows_with_decisions(client, auth_headers):
    fair_id = _fair_id(client, auth_headers)
    batch_id = _upload_and_analyze(client, auth_headers, fair_id, [["Alpha Co"], ["Beta Co"]])

    rows = client.get(
        f"/api/v1/data-integration/imports/{batch_id}/rows",
        headers=auth_headers,
        params={"page_size": 100},
    ).json()["items"]
    assert len(rows) == 2

    row_a = rows[0]["id"]
    decision = client.patch(
        f"/api/v1/imports/{batch_id}/rows/{row_a}/decision",
        headers=auth_headers,
        json={"decision": "create_new"},
    )
    assert decision.status_code == 200
    assert decision.json()["decision"] == "create_new"
    assert decision.json()["status"] != "applied"

    apply = apply_import_decisions(client, auth_headers, batch_id, row_ids=[row_a])
    assert apply.status_code == 200
    body = apply.json()
    assert body["processed_count"] == 1
    assert body["failed_count"] == 0

    remaining = client.get(
        f"/api/v1/data-integration/imports/{batch_id}/rows",
        headers=auth_headers,
        params={"page_size": 100},
    ).json()["items"]
    assert len(remaining) == 1
    assert remaining[0]["id"] != row_a


def test_apply_selected_without_decision_reports_not_processed(client, auth_headers):
    fair_id = _fair_id(client, auth_headers)
    batch_id = _upload_and_analyze(client, auth_headers, fair_id, [["No Decision Co"]])
    row_id = client.get(
        f"/api/v1/data-integration/imports/{batch_id}/rows",
        headers=auth_headers,
    ).json()["items"][0]["id"]

    apply = apply_import_decisions(client, auth_headers, batch_id, row_ids=[row_id])
    assert apply.status_code == 200
    body = apply.json()
    assert body["processed_count"] == 0
    assert body["not_processed_count"] == 1
    assert body["failed_count"] == 0
    assert body["errors"] == []


def test_apply_filter_scope_processes_all_decided_rows(client, auth_headers):
    fair_id = _fair_id(client, auth_headers)
    batch_id = _upload_and_analyze(client, auth_headers, fair_id, [["Scope A"], ["Scope B"]])
    rows = client.get(
        f"/api/v1/data-integration/imports/{batch_id}/rows",
        headers=auth_headers,
        params={"page_size": 100},
    ).json()["items"]

    for row in rows:
        resp = client.patch(
            f"/api/v1/imports/{batch_id}/rows/{row['id']}/decision",
            headers=auth_headers,
            json={"decision": "skip"},
        )
        assert resp.status_code == 200

    apply = apply_import_decisions(client, auth_headers, batch_id, filter="pending")
    assert apply.status_code == 200
    assert apply.json()["processed_count"] == 2

    remaining = client.get(
        f"/api/v1/data-integration/imports/{batch_id}/rows",
        headers=auth_headers,
        params={"page_size": 100},
    ).json()["items"]
    assert len(remaining) == 0

    batch = client.get(f"/api/v1/data-integration/imports/{batch_id}", headers=auth_headers).json()
    assert batch["status"] == "completed"
