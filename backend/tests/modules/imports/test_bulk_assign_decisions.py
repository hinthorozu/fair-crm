"""Bulk assign import row decisions to selected rows (no CRM writes)."""

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


def _upload_previewed(client, auth_headers, rows: list[list[str]]) -> tuple[str, list[dict]]:
    content = _xlsx(rows, headers=["Firma Adı"])
    upload = client.post(
        "/api/v1/imports/customers/upload",
        headers=auth_headers,
        files={"file": ("bulk-assign.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert upload.status_code == 201
    batch_id = upload.json()["id"]
    listed = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    return batch_id, listed


def test_bulk_assign_decisions_updates_selected_rows_only(client, auth_headers):
    batch_id, rows = _upload_previewed(
        client,
        auth_headers,
        [["Alpha Co"], ["Beta Co"], ["Gamma Co"]],
    )
    selected = [rows[0]["id"], rows[1]["id"]]

    response = client.patch(
        f"/api/v1/imports/{batch_id}/rows/bulk-decision",
        headers=auth_headers,
        json={"row_ids": selected, "decision": "create_new"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["updated_count"] == 2
    assert body["skipped_count"] == 0

    refreshed = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    by_id = {row["id"]: row for row in refreshed}
    assert by_id[rows[0]["id"]]["decision"] == "create_new"
    assert by_id[rows[1]["id"]]["decision"] == "create_new"
    assert by_id[rows[2]["id"]]["decision"] is None

    customers = client.get("/api/v1/customers?search=Alpha", headers=auth_headers).json()["items"]
    assert len(customers) == 0


def test_bulk_assign_update_existing_without_match_is_skipped(client, auth_headers):
    batch_id, rows = _upload_previewed(client, auth_headers, [["No Match Co"]])

    response = client.patch(
        f"/api/v1/imports/{batch_id}/rows/bulk-decision",
        headers=auth_headers,
        json={"row_ids": [rows[0]["id"]], "decision": "update_existing"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["updated_count"] == 0
    assert body["skipped_count"] == 1
    assert len(body["errors"]) == 1

    row = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"][0]
    assert row["decision"] is None


def test_bulk_assign_does_not_require_row_ids_and_decision_together(client, auth_headers):
    batch_id, _ = _upload_previewed(client, auth_headers, [["Only Co"]])

    response = client.patch(
        f"/api/v1/imports/{batch_id}/rows/bulk-decision",
        headers=auth_headers,
        json={"row_ids": [], "decision": "skip"},
    )
    assert response.status_code == 422
