"""Parity checks between the deprecated synchronous analyze route and production analyze jobs.

These tests are intentionally transitional. They prove that moving callers from
``analyze-legacy`` to ``analyze-job`` preserves import-row semantics before the
legacy route is removed.
"""

from io import BytesIO

from openpyxl import Workbook

from tests.conftest_customer_helpers import create_test_customer


IMPORTS_BASE = "/api/v1/data-integration/imports"
JOBS_BASE = "/api/v1/data-integration/jobs"


def _xlsx(headers: list[str], rows: list[list[str | None]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _create_fair(client, auth_headers, name: str) -> str:
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


def _create_mapped_batch(client, auth_headers, fair_id: str, content: bytes) -> str:
    upload = client.post(
        f"{IMPORTS_BASE}/upload",
        headers=auth_headers,
        data={"fair_id": fair_id},
        files={
            "file": (
                "parity.xlsx",
                content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert upload.status_code == 201
    batch_id = upload.json()["batch_id"]

    mapping = client.patch(
        f"{IMPORTS_BASE}/{batch_id}/column-mapping",
        headers=auth_headers,
        json={
            "has_header_row": True,
            "mappings": {
                "company_name": {"type": "column_index", "value": 0},
                "email": {"type": "column_index", "value": 1},
            },
        },
    )
    assert mapping.status_code == 200
    return batch_id


def _analyze_with_job(client, auth_headers, batch_id: str) -> None:
    started = client.post(f"{IMPORTS_BASE}/{batch_id}/analyze-job", headers=auth_headers)
    assert started.status_code == 202
    job_id = started.json()["job_id"]

    job_payload = None
    for _ in range(60):
        response = client.get(f"{JOBS_BASE}/{job_id}", headers=auth_headers)
        assert response.status_code == 200
        job_payload = response.json()
        if job_payload["status"] in {"completed", "failed"}:
            break

    assert job_payload is not None
    assert job_payload["status"] == "completed", job_payload


def _analyze_with_legacy_route(client, auth_headers, batch_id: str) -> None:
    response = client.post(f"{IMPORTS_BASE}/{batch_id}/analyze-legacy", headers=auth_headers)
    assert response.status_code == 200


def _semantic_rows(client, auth_headers, batch_id: str) -> list[dict]:
    response = client.get(f"{IMPORTS_BASE}/{batch_id}/rows", headers=auth_headers)
    assert response.status_code == 200
    rows = sorted(response.json()["items"], key=lambda item: item["row_number"])
    fields = (
        "row_number",
        "raw_data_json",
        "normalized_data_json",
        "status",
        "validation_errors_json",
        "match_customer_id",
        "match_confidence",
        "match_reason",
        "decision",
    )
    return [{field: row.get(field) for field in fields} for row in rows]


def test_analyze_job_matches_legacy_row_semantics(client, auth_headers):
    fair_id = _create_fair(client, auth_headers, "Analyze Parity Fair")
    content = _xlsx(
        ["Firma Adı", "E-posta"],
        [
            ["Acme Ltd", "info@acme.com"],
            ["Acme Ltd", "sales@acme.com"],
            ["Sparse Co", "not-an-email"],
        ],
    )

    legacy_batch = _create_mapped_batch(client, auth_headers, fair_id, content)
    job_batch = _create_mapped_batch(client, auth_headers, fair_id, content)

    _analyze_with_legacy_route(client, auth_headers, legacy_batch)
    _analyze_with_job(client, auth_headers, job_batch)

    assert _semantic_rows(client, auth_headers, job_batch) == _semantic_rows(
        client, auth_headers, legacy_batch
    )


def test_analyze_job_matches_legacy_existing_customer_match(
    client,
    auth_headers,
    db_session,
    organization_id,
):
    customer = create_test_customer(
        db_session,
        organization_id,
        display_name="Sinan Elektronik A.Ş.",
        email="existing@sinan.com",
    )
    fair_id = _create_fair(client, auth_headers, "Existing Match Parity Fair")
    content = _xlsx(
        ["Firma Adı", "E-posta"],
        [["SİNAN ELEKTRONİK ANONİM ŞİRKETİ", "incoming@sinan.com"]],
    )

    legacy_batch = _create_mapped_batch(client, auth_headers, fair_id, content)
    job_batch = _create_mapped_batch(client, auth_headers, fair_id, content)

    _analyze_with_legacy_route(client, auth_headers, legacy_batch)
    _analyze_with_job(client, auth_headers, job_batch)

    legacy_rows = _semantic_rows(client, auth_headers, legacy_batch)
    job_rows = _semantic_rows(client, auth_headers, job_batch)

    assert job_rows == legacy_rows
    assert len(job_rows) == 1
    assert job_rows[0]["match_customer_id"] == str(customer.id)
    assert job_rows[0]["match_confidence"] == 100
    assert job_rows[0]["match_reason"] == "exact_normalized_match"
