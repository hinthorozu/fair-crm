"""Test helpers for exercising the canonical import wizard lifecycle."""

from io import BytesIO
from uuid import uuid4

from openpyxl import Workbook


IMPORTS_BASE = "/api/v1/data-integration/imports"
JOBS_BASE = "/api/v1/data-integration/jobs"


def build_xlsx(headers: list[str], rows: list[list[str | None]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def create_analyzed_import(
    client,
    auth_headers,
    headers: list[str],
    rows: list[list[str | None]],
    *,
    filename: str = "import.xlsx",
):
    """Create a fair, upload an xlsx, map suggested columns, and finish analyze-job."""
    fair = client.post(
        "/api/v1/fairs",
        headers=auth_headers,
        json={
            "name": f"Canonical Import Test {uuid4()}",
            "location": "Istanbul",
            "start_date": "2026-06-05",
            "end_date": "2026-06-08",
        },
    )
    assert fair.status_code == 201, fair.text
    fair_id = fair.json()["id"]

    content = build_xlsx(headers, rows)
    upload = client.post(
        f"{IMPORTS_BASE}/upload",
        headers=auth_headers,
        data={"fair_id": fair_id},
        files={
            "file": (
                filename,
                content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert upload.status_code == 201, upload.text
    upload_payload = upload.json()
    batch_id = upload_payload["batch_id"]
    suggested = upload_payload["suggested_mapping"]

    mapping = client.patch(
        f"{IMPORTS_BASE}/{batch_id}/column-mapping",
        headers=auth_headers,
        json={
            "header_mode": suggested["header_mode"],
            "has_header_row": suggested["has_header_row"],
            "header_row_index": suggested.get("header_row_index"),
            "mappings": suggested["mappings"],
        },
    )
    assert mapping.status_code == 200, mapping.text

    analyze = client.post(f"{IMPORTS_BASE}/{batch_id}/analyze-job", headers=auth_headers)
    assert analyze.status_code == 202, analyze.text
    job_id = analyze.json()["job_id"]

    job = client.get(f"{JOBS_BASE}/{job_id}", headers=auth_headers)
    assert job.status_code == 200, job.text
    assert job.json()["status"] == "completed", job.text

    batch = client.get(f"{IMPORTS_BASE}/{batch_id}", headers=auth_headers)
    assert batch.status_code == 200, batch.text
    return batch
