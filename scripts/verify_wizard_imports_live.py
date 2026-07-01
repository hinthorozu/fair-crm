#!/usr/bin/env python3
"""Live API smoke test for Smart Import Wizard Phase 1."""

from __future__ import annotations

import json
import sys
import uuid
import urllib.error
import urllib.request
from io import BytesIO

from openpyxl import Workbook

BASE = "http://127.0.0.1:8001"
ORG = "00000000-0000-4000-8000-000000000010"
AUTH = {
    "Authorization": "Bearer dev-bypass",
    "X-Organization-Id": ORG,
    "Content-Type": "application/json",
}


def json_request(method: str, path: str, body: dict | None = None) -> tuple[int, dict | list | str]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=AUTH, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = raw
        return exc.code, payload


def build_xlsx(headers: list[str] | None, rows: list[list[str]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    if headers:
        sheet.append(headers)
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def upload_wizard(fair_id: str, content: bytes, filename: str = "wizard_live.xlsx") -> tuple[int, dict | list | str]:
    boundary = "----FairCrmWizardBoundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="fair_id"\r\n\r\n'
        f"{fair_id}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()

    headers = {
        "Authorization": "Bearer dev-bypass",
        "X-Organization-Id": ORG,
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    req = urllib.request.Request(
        f"{BASE}/api/v1/imports/upload",
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = raw
        return exc.code, payload


def main() -> int:
    print("== Live API verification: Smart Import Wizard ==")

    status, health = json_request("GET", "/health")
    if status != 200:
        print(f"FAIL health {status}")
        return 1
    print(f"PASS health: {health}")

    status, openapi = json_request("GET", "/openapi.json")
    if status != 200:
        print(f"FAIL openapi {status}")
        return 1
    paths = openapi.get("paths", {})
    required = [
        "/api/v1/imports/upload",
        "/api/v1/imports/{batch_id}/column-mapping",
        "/api/v1/imports/{batch_id}/analyze",
        "/api/v1/imports/{batch_id}/rows/bulk-decision",
        "/api/v1/imports/{batch_id}/apply",
    ]
    for path in required:
        if path not in paths:
            print(f"FAIL swagger missing path: {path}")
            return 1
    print("PASS swagger wizard paths present")

    status, fair = json_request(
        "POST",
        "/api/v1/fairs",
        {
            "name": "Wizard Live Fair",
            "location": "Istanbul",
            "start_date": "2026-06-05",
            "end_date": "2026-06-08",
        },
    )
    if status != 201:
        print(f"FAIL create fair {status}: {fair}")
        return 1
    fair_id = fair["id"]
    print(f"PASS fair created: {fair_id}")

    unique_co = f"Wizard Live Co {uuid.uuid4().hex[:8]}"
    content = build_xlsx(
        ["Firma Adı", "E-posta", "Salon", "Stand"],
        [[unique_co, "wizard@live.com", "A1", "12"]],
    )
    status, upload = upload_wizard(fair_id, content)
    if status != 201:
        print(f"FAIL upload {status}: {upload}")
        return 1
    batch_id = upload["batch_id"]
    assert upload["fair_id"] == fair_id
    assert upload["raw_columns"]
    assert upload["sample_rows"]
    print(f"PASS upload batch: {batch_id}, rows={upload['total_rows']}")

    status, mapping = json_request(
        "PATCH",
        f"/api/v1/imports/{batch_id}/column-mapping",
        {
            "has_header_row": True,
            "mappings": {
                "company_name": {"type": "column_index", "value": 0},
                "email": {"type": "column_index", "value": 1},
                "hall": {"type": "column_index", "value": 2},
                "stand": {"type": "column_index", "value": 3},
            },
        },
    )
    if status != 200:
        print(f"FAIL column-mapping {status}: {mapping}")
        return 1
    print("PASS column mapping")

    status, analyzed = json_request("POST", f"/api/v1/imports/{batch_id}/analyze")
    if status != 200:
        print(f"FAIL analyze {status}: {analyzed}")
        return 1
    print(f"PASS analyze: valid={analyzed.get('valid_rows')}")

    status, rows = json_request("GET", f"/api/v1/imports/{batch_id}/rows")
    if status != 200 or not rows.get("items"):
        print(f"FAIL rows {status}: {rows}")
        return 1
    row_id = rows["items"][0]["id"]
    preview = rows["items"][0].get("merge_preview")
    if not preview or not preview.get("groups"):
        print(f"FAIL merge preview missing: {preview}")
        return 1
    print("PASS merge preview on rows")

    status, decision = json_request(
        "PATCH",
        f"/api/v1/imports/{batch_id}/rows/{row_id}/decision",
        {"decision": "create_new"},
    )
    if status != 200:
        print(f"FAIL set decision {status}: {decision}")
        return 1

    status, bulk = json_request(
        "PATCH",
        f"/api/v1/imports/{batch_id}/rows/bulk-decision",
        {"action": "create_all_new"},
    )
    if status != 200:
        print(f"FAIL bulk-decision {status}: {bulk}")
        return 1
    print("PASS bulk decision")

    status, applied = json_request("POST", f"/api/v1/imports/{batch_id}/apply")
    if status != 200:
        print(f"FAIL apply {status}: {applied}")
        return 1
    created = applied.get("created_rows", 0)
    updated = applied.get("updated_rows", 0)
    if created < 1 and updated < 1:
        print(f"FAIL apply no customer changes: {applied}")
        return 1
    created_parts = applied.get("created_participations", applied.get("batch", {}).get("created_participations", 0))
    print(f"PASS apply: created={created} participations={created_parts}")

    status, customers = json_request("GET", f"/api/v1/customers?search={unique_co.replace(' ', '+')}")
    if status != 200:
        print(f"FAIL customer lookup {status}: {customers}")
        return 1
    items = customers.get("items", [])
    if not items:
        print("FAIL customer not found after apply")
        return 1
    customer_id = items[0]["id"]
    print(f"PASS customer created: {customer_id}")

    status, parts = json_request("GET", f"/api/v1/fairs/{fair_id}/participants")
    if status != 200:
        print(f"FAIL participations {status}: {parts}")
        return 1
    part_items = parts.get("items", [])
    if not part_items:
        print("FAIL participation not found after apply")
        return 1
    part = next((p for p in part_items if p.get("company_name") == unique_co), None)
    if part is None:
        print(f"FAIL participation for {unique_co} not found: {part_items}")
        return 1
    if part.get("hall") != "A1" or part.get("stand") != "12":
        print(f"FAIL hall/stand on participation: {part}")
        return 1
    print(f"PASS participation hall={part.get('hall')} stand={part.get('stand')}")

    status, activities = json_request("GET", f"/api/v1/customers/{customer_id}/activities")
    if status != 200:
        print(f"FAIL activities {status}: {activities}")
        return 1
    act_items = activities.get("items", [])
    if not any("Import applied" in (a.get("subject") or "") for a in act_items):
        print(f"FAIL import activity not found: {act_items[:2]}")
        return 1
    print("PASS import activity created")

    headerless_co = f"Headerless Co {uuid.uuid4().hex[:8]}"
    headerless = build_xlsx(None, [[headerless_co, "h@test.com", "B2", "5"]])
    status, upload2 = upload_wizard(fair_id, headerless, "headerless.xlsx")
    if status != 201:
        print(f"FAIL headerless upload {status}: {upload2}")
        return 1
    batch2 = upload2["batch_id"]
    status, _ = json_request(
        "PATCH",
        f"/api/v1/imports/{batch2}/column-mapping",
        {
            "has_header_row": False,
            "mappings": {"company_name": {"type": "column_index", "value": 0}},
        },
    )
    if status != 200:
        print(f"FAIL headerless mapping {status}")
        return 1
    status, analyzed2 = json_request("POST", f"/api/v1/imports/{batch2}/analyze")
    if status != 200:
        print(f"FAIL headerless analyze {status}: {analyzed2}")
        return 1
    print("PASS headerless excel mapping + analyze")

    # Contact apply verification
    contact_co = f"Contact Live Co {uuid.uuid4().hex[:8]}"
    contact_content = build_xlsx(
        ["Firma Adı", "Yetkili Adı", "Yetkili Soyadı", "Yetkili E-posta", "Yetkili Telefon"],
        [[contact_co, "Ayse", "Yilmaz", "ayse@live.com", "5559998877"]],
    )
    status, upload3 = upload_wizard(fair_id, contact_content, "contact_live.xlsx")
    if status != 201:
        print(f"FAIL contact upload {status}: {upload3}")
        return 1
    batch3 = upload3["batch_id"]
    status, _ = json_request(
        "PATCH",
        f"/api/v1/imports/{batch3}/column-mapping",
        {
            "has_header_row": True,
            "mappings": {
                "company_name": {"type": "column_index", "value": 0},
                "contact_first_name": {"type": "column_index", "value": 1},
                "contact_last_name": {"type": "column_index", "value": 2},
                "contact_email": {"type": "column_index", "value": 3},
                "contact_phone": {"type": "column_index", "value": 4},
            },
        },
    )
    if status != 200:
        print(f"FAIL contact mapping {status}")
        return 1
    status, _ = json_request("POST", f"/api/v1/imports/{batch3}/analyze")
    if status != 200:
        print(f"FAIL contact analyze {status}")
        return 1
    status, contact_rows = json_request("GET", f"/api/v1/imports/{batch3}/rows")
    if status != 200:
        print(f"FAIL contact rows {status}")
        return 1
    contact_row = contact_rows["items"][0]
    if not any(g.get("entity") == "contact" for g in contact_row.get("merge_preview", {}).get("groups", [])):
        print("FAIL contact merge preview group missing")
        return 1
    print("PASS contact merge preview")
    json_request(
        "PATCH",
        f"/api/v1/imports/{batch3}/rows/{contact_row['id']}/decision",
        {"decision": "create_new"},
    )
    status, contact_apply = json_request("POST", f"/api/v1/imports/{batch3}/apply")
    if status != 200 or contact_apply.get("created_contacts", 0) < 1:
        print(f"FAIL contact apply {status}: {contact_apply}")
        return 1
    status, cust = json_request("GET", f"/api/v1/customers?search={contact_co.replace(' ', '+')}")
    if status != 200 or not cust.get("items"):
        print("FAIL contact customer lookup")
        return 1
    cid = cust["items"][0]["id"]
    status, contacts = json_request("GET", f"/api/v1/customers/{cid}/contacts")
    if status != 200 or contacts.get("total", 0) < 1:
        print(f"FAIL contact created {status}: {contacts}")
        return 1
    print(f"PASS contact created: {contacts['items'][0].get('first_name', 'ok')}")
    status, parts3 = json_request("GET", f"/api/v1/fairs/{fair_id}/participants")
    if not any(p.get("company_name") == contact_co for p in parts3.get("items", [])):
        print("FAIL contact participation")
        return 1
    print("PASS contact participation")
    status, acts = json_request("GET", f"/api/v1/customers/{cid}/activities")
    if not any(a.get("source") == "import" for a in acts.get("items", [])):
        print("FAIL contact activity")
        return 1
    print("PASS contact activity")

    return 0


if __name__ == "__main__":
    sys.exit(main())
