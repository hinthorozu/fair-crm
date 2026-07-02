"""Bulk decision preview/apply job and batch resume helpers."""

from io import BytesIO

from openpyxl import Workbook

from app.modules.imports.domain.batch_status import (
    can_resume_setup,
    resume_setup_step_id,
)


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
        json={"name": "Bulk Fair", "location": "Istanbul", "start_date": "2026-06-01", "end_date": "2026-06-03"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _upload_and_map(client, auth_headers, fair_id: str, content: bytes | None = None) -> str:
    if content is None:
        content = _xlsx(
            [["New Co", "Dup Co", ""], ["Other Co", "Dup Co", "bad"]],
            headers=["Firma", "Firma2", "Extra"],
        )
    upload = client.post(
        "/api/v1/data-integration/imports/upload",
        headers=auth_headers,
        data={"fair_id": fair_id},
        files={"file": ("bulk.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
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


def test_batch_resume_helpers():
    assert can_resume_setup("uploaded")
    assert can_resume_setup("sheet_selected")
    assert can_resume_setup("header_configured")
    assert not can_resume_setup("mapping_completed")
    assert resume_setup_step_id("uploaded") == "sheet"
    assert resume_setup_step_id("sheet_selected") == "header"
    assert resume_setup_step_id("header_configured") == "mapping"


def test_bulk_preview_does_not_mutate(client, auth_headers):
    fair_id = _fair_id(client, auth_headers)
    batch_id = _upload_and_map(client, auth_headers, fair_id)

    rows_new = client.get(
        f"/api/v1/data-integration/imports/{batch_id}/rows",
        headers=auth_headers,
        params={"filter": "new", "page_size": 100},
    )
    assert rows_new.status_code == 200
    new_filter_total = rows_new.json()["pagination"]["totalItems"]

    preview = client.post(
        f"/api/v1/data-integration/imports/{batch_id}/bulk-actions/preview",
        headers=auth_headers,
        json={"action_type": "create_all_new"},
    )
    assert preview.status_code == 200
    body = preview.json()
    assert body["affected_rows"] == new_filter_total
    assert body["affected_rows"] >= 1
    assert "summary" in body

    rows_before = client.get(f"/api/v1/data-integration/imports/{batch_id}/rows", headers=auth_headers)
    assert rows_before.status_code == 200
    undecided_before = sum(1 for r in rows_before.json()["items"] if r.get("decision") is None)

    preview2 = client.post(
        f"/api/v1/data-integration/imports/{batch_id}/bulk-actions/preview",
        headers=auth_headers,
        json={"action_type": "create_all_new"},
    )
    assert preview2.status_code == 200

    rows_after = client.get(f"/api/v1/data-integration/imports/{batch_id}/rows", headers=auth_headers)
    undecided_after = sum(1 for r in rows_after.json()["items"] if r.get("decision") is None)
    assert undecided_before == undecided_after


def test_bulk_apply_job_conflict(client, auth_headers):
    fair_id = _fair_id(client, auth_headers)
    batch_id = _upload_and_map(client, auth_headers, fair_id)

    apply = client.post(
        f"/api/v1/data-integration/imports/{batch_id}/bulk-actions/apply",
        headers=auth_headers,
        json={"action_type": "skip_invalid"},
    )
    assert apply.status_code == 202
    job_id = apply.json()["job_id"]
    running = client.get(f"/api/v1/data-integration/jobs/{job_id}", headers=auth_headers).json()
    if running["status"] in ("queued", "running"):
        conflict = client.post(
            f"/api/v1/data-integration/imports/{batch_id}/bulk-actions/apply",
            headers=auth_headers,
            json={"action_type": "skip_invalid"},
        )
        assert conflict.status_code == 409


def test_bulk_apply_job_completes(client, auth_headers):
    fair_id = _fair_id(client, auth_headers)
    batch_id = _upload_and_map(client, auth_headers, fair_id)

    apply = client.post(
        f"/api/v1/data-integration/imports/{batch_id}/bulk-actions/apply",
        headers=auth_headers,
        json={"action_type": "create_all_new"},
    )
    assert apply.status_code == 202
    job_id = apply.json()["job_id"]

    for _ in range(60):
        status = client.get(f"/api/v1/data-integration/jobs/{job_id}", headers=auth_headers)
        assert status.status_code == 200
        if status.json()["status"] == "completed":
            break
    assert status.json()["status"] == "completed"

    batch = client.get(f"/api/v1/data-integration/imports/{batch_id}", headers=auth_headers)
    assert batch.status_code == 200
    assert batch.json()["status"] == "completed"
    assert batch.json()["created_rows"] >= 1

    remaining = client.get(
        f"/api/v1/data-integration/imports/{batch_id}/rows",
        headers=auth_headers,
        params={"filter": "all", "page_size": 100},
    )
    assert remaining.status_code == 200
    assert remaining.json()["pagination"]["totalItems"] == 0

    pending = client.get(
        f"/api/v1/data-integration/imports/{batch_id}/rows",
        headers=auth_headers,
        params={"filter": "pending", "page_size": 100},
    )
    assert pending.status_code == 200
    assert pending.json()["pagination"]["totalItems"] == 0


def test_bulk_apply_excludes_applied_from_pending_filter(client, auth_headers):
    fair_id = _fair_id(client, auth_headers)
    batch_id = _upload_and_map(client, auth_headers, fair_id)

    rows_before = client.get(
        f"/api/v1/data-integration/imports/{batch_id}/rows",
        headers=auth_headers,
        params={"filter": "pending", "page_size": 100},
    )
    assert rows_before.status_code == 200
    pending_before = rows_before.json()["pagination"]["totalItems"]
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

    pending_after = client.get(
        f"/api/v1/data-integration/imports/{batch_id}/rows",
        headers=auth_headers,
        params={"filter": "pending", "page_size": 100},
    )
    assert pending_after.status_code == 200
    assert pending_after.json()["pagination"]["totalItems"] < pending_before

    batch = client.get(f"/api/v1/data-integration/imports/{batch_id}", headers=auth_headers)
    assert batch.status_code == 200
    assert batch.json()["created_rows"] >= 1


def test_bulk_skip_invalid_applies_rows(client, auth_headers):
    fair_id = _fair_id(client, auth_headers)
    batch_id = _upload_and_map(
        client,
        auth_headers,
        fair_id,
        content=_xlsx(
            [["Sinan Elektronik A.Ş."], ["SINAN ELEKTRONIK LTD"]],
            headers=["Firma"],
        ),
    )

    before = client.get(
        f"/api/v1/data-integration/imports/{batch_id}/rows",
        headers=auth_headers,
        params={"page_size": 100},
    ).json()
    assert before["counts"]["invalid"] >= 1
    pending_before = before["counts"]["pending"]

    apply = client.post(
        f"/api/v1/data-integration/imports/{batch_id}/bulk-actions/apply",
        headers=auth_headers,
        json={"action_type": "skip_invalid"},
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
        params={"page_size": 100},
    ).json()
    assert after["counts"]["invalid"] == 0
    assert after["counts"]["pending"] < pending_before
    assert after["counts"]["applied"] >= 1

    pending_rows = client.get(
        f"/api/v1/data-integration/imports/{batch_id}/rows",
        headers=auth_headers,
        params={"filter": "pending", "page_size": 100},
    ).json()
    assert all(row["status"] != "skipped" for row in pending_rows["items"])

    all_rows = client.get(
        f"/api/v1/data-integration/imports/{batch_id}/rows",
        headers=auth_headers,
        params={"filter": "all", "page_size": 100},
    ).json()
    assert not any(row["status"] == "skipped" for row in all_rows["items"])


def test_upload_redirect_status_uploaded(client, auth_headers):
    fair_id = _fair_id(client, auth_headers)
    content = _xlsx([["Acme"]], headers=["Firma"])
    upload = client.post(
        "/api/v1/data-integration/imports/upload",
        headers=auth_headers,
        data={"fair_id": fair_id},
        files={"file": ("resume.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert upload.status_code == 201
    batch_id = upload.json()["batch_id"]
    batch = client.get(f"/api/v1/data-integration/imports/{batch_id}", headers=auth_headers)
    assert batch.status_code == 200
    assert batch.json()["status"] == "uploaded"
    assert batch.json().get("available_sheets")
