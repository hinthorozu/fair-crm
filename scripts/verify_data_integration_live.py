"""Live API verification for Sprint 09.1 Data Integration (run against dev server on 8001)."""

from __future__ import annotations

import sys
import time
from io import BytesIO
from uuid import UUID

import httpx
from openpyxl import Workbook

BASE = "http://127.0.0.1:8001/api/v1"
ORG = "00000000-0000-4000-8000-000000000010"
HEADERS = {
    "Authorization": "Bearer dev-bypass",
    "X-Organization-Id": ORG,
}


def xlsx(headers: list[str] | None, rows: list[list[str]], *, extra_sheet: list[list[str]] | None = None) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    if headers:
        ws.append(headers)
    for row in rows:
        ws.append(row)
    if extra_sheet is not None:
        ws2 = wb.create_sheet("Sheet2")
        for row in extra_sheet:
            ws2.append(row)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def create_fair(client: httpx.Client, name: str) -> UUID:
    r = client.post(
        f"{BASE}/fairs",
        headers=HEADERS,
        json={"name": name, "location": "Istanbul", "start_date": "2026-06-01", "end_date": "2026-06-03"},
    )
    r.raise_for_status()
    return UUID(r.json()["id"])


def upload(client: httpx.Client, fair_id: UUID, content: bytes, filename: str) -> dict:
    r = client.post(
        f"{BASE}/data-integration/imports/upload",
        headers={k: v for k, v in HEADERS.items()},
        data={"fair_id": str(fair_id)},
        files={"file": (filename, content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    r.raise_for_status()
    return r.json()


def scenario_header_yes(client: httpx.Client) -> None:
    print("Scenario 1: Excel (header yes)...")
    fair_id = create_fair(client, "DI Verify Fair 1")
    body = upload(
        client,
        fair_id,
        xlsx(["Company", "Email"], [["Acme Verify Co", "acme@verify.test"]]),
        "header_yes.xlsx",
    )
    batch_id = body["batch_id"]
    assert body.get("available_sheets")

    r = client.patch(
        f"{BASE}/data-integration/imports/{batch_id}/column-mapping",
        headers=HEADERS,
        json={
            "header_mode": "first_row_header",
            "has_header_row": True,
            "mappings": {
                "company_name": {"type": "column_index", "value": 0},
                "email": {"type": "column_index", "value": 1},
            },
        },
    )
    r.raise_for_status()

    r = client.post(f"{BASE}/data-integration/imports/{batch_id}/analyze", headers=HEADERS)
    r.raise_for_status()
    assert r.json()["total_rows"] == 1

    r = client.post(f"{BASE}/data-integration/imports/{batch_id}/apply-job", headers=HEADERS)
    r.raise_for_status()
    job_id = r.json()["job_id"]

    for _ in range(30):
        jr = client.get(f"{BASE}/data-integration/jobs/{job_id}", headers=HEADERS)
        jr.raise_for_status()
        status = jr.json()["status"]
        if status in ("completed", "failed"):
            assert status == "completed", jr.json()
            print("  PASS apply-job completed")
            return
        time.sleep(0.5)
    raise RuntimeError("Job timeout")


def scenario_header_no(client: httpx.Client) -> None:
    print("Scenario 2: Excel (header no)...")
    fair_id = create_fair(client, "DI Verify Fair 2")
    body = upload(
        client,
        fair_id,
        xlsx(None, [["Beta NoHeader", "beta@verify.test"], ["Gamma NoHeader", "g@verify.test"]]),
        "header_no.xlsx",
    )
    batch_id = body["batch_id"]

    r = client.patch(
        f"{BASE}/data-integration/imports/{batch_id}/column-mapping",
        headers=HEADERS,
        json={
            "header_mode": "no_header",
            "has_header_row": False,
            "mappings": {
                "company_name": {"type": "column_index", "value": 0},
                "email": {"type": "column_index", "value": 1},
            },
        },
    )
    r.raise_for_status()
    assert r.json()["column_mapping"]["header_mode"] == "no_header"

    r = client.post(f"{BASE}/data-integration/imports/{batch_id}/analyze", headers=HEADERS)
    r.raise_for_status()
    assert r.json()["total_rows"] == 2
    print("  PASS no-header analyze 2 rows")


def scenario_multi_sheet(client: httpx.Client) -> None:
    print("Scenario 3: Multi sheet...")
    fair_id = create_fair(client, "DI Verify Fair 3")
    body = upload(
        client,
        fair_id,
        xlsx(
            ["Company", "Email"],
            [["Sheet1 Co", "s1@test.com"]],
            extra_sheet=[["Sheet2 Co", "s2@test.com"]],
        ),
        "multi_sheet.xlsx",
    )
    batch_id = body["batch_id"]
    sheets = body.get("available_sheets") or []
    assert len(sheets) >= 2, sheets

    r = client.patch(
        f"{BASE}/data-integration/imports/{batch_id}/sheet",
        headers=HEADERS,
        json={"sheet_name": "Sheet2"},
    )
    r.raise_for_status()
    assert r.json()["selected_sheet_name"] == "Sheet2"
    print("  PASS sheet switch")


def scenario_duplicate(client: httpx.Client) -> None:
    print("Scenario 4: Duplicate detection...")
    fair_id = create_fair(client, "DI Verify Fair 4")
    # Seed customer
    cr = client.post(
        f"{BASE}/customers",
        headers=HEADERS,
        json={"display_name": "Duplicate Target AS", "email": "dup@verify.test"},
    )
    cr.raise_for_status()

    body = upload(
        client,
        fair_id,
        xlsx(["Company", "Email"], [["Duplicate Target AS", "new@verify.test"]]),
        "dup.xlsx",
    )
    batch_id = body["batch_id"]
    client.patch(
        f"{BASE}/data-integration/imports/{batch_id}/column-mapping",
        headers=HEADERS,
        json={
            "header_mode": "first_row_header",
            "has_header_row": True,
            "mappings": {
                "company_name": {"type": "column_index", "value": 0},
                "email": {"type": "column_index", "value": 1},
            },
        },
    ).raise_for_status()
    client.post(f"{BASE}/data-integration/imports/{batch_id}/analyze", headers=HEADERS).raise_for_status()

    rows = client.get(f"{BASE}/data-integration/imports/{batch_id}/rows", headers=HEADERS).json()
    assert rows["items"], "expected rows"
    row = rows["items"][0]
    assert row.get("match_customer_id") or row.get("status") in (
        "possible_duplicate",
        "ready_to_update",
    ), row
    print("  PASS duplicate match detected")


def main() -> int:
    with httpx.Client(timeout=60.0) as client:
        hr = client.get("http://127.0.0.1:8001/health")
        hr.raise_for_status()
        listing = client.get(f"{BASE}/data-integration/imports", headers=HEADERS)
        listing.raise_for_status()
        print(f"Import batches list: total={listing.json().get('total')}")

        scenario_header_yes(client)
        scenario_header_no(client)
        scenario_multi_sheet(client)
        scenario_duplicate(client)

    print("\nAll live API scenarios PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
