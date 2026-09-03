#!/usr/bin/env python3
"""Live API smoke test for the canonical import wizard flow."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from io import BytesIO

from openpyxl import Workbook

BASE = "http://127.0.0.1:8001"
API_BASE = "/api/v1"
IMPORTS_BASE = f"{API_BASE}/data-integration/imports"
JOBS_BASE = f"{API_BASE}/data-integration/jobs"
ORG = "00000000-0000-4000-8000-000000000010"
HEADERS = {
    "Authorization": "Bearer dev-bypass",
    "X-Organization-Id": ORG,
    "Content-Type": "application/json",
}


def json_request(method: str, path: str, body: dict | None = None) -> tuple[int, dict | list | str]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = raw
        return exc.code, payload


def build_xlsx() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Firma Adı", "E-posta", "Yetkili Adı", "Yetkili Soyadı"])
    sheet.append(["Live Import Co", "live@import.com", "Can", "Test"])
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def create_fair() -> tuple[int, dict | list | str]:
    return json_request(
        "POST",
        f"{API_BASE}/fairs",
        {
            "name": "Live Import Verification Fair",
            "location": "Istanbul",
            "start_date": "2026-06-01",
            "end_date": "2026-06-03",
        },
    )


def upload_xlsx(fair_id: str, content: bytes) -> tuple[int, dict | list | str]:
    boundary = "----FairCrmImportBoundary"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="fair_id"\r\n\r\n'
        f"{fair_id}\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="live_import.xlsx"\r\n'
        "Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()

    headers = {
        "Authorization": "Bearer dev-bypass",
        "X-Organization-Id": ORG,
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    req = urllib.request.Request(
        f"{BASE}{IMPORTS_BASE}/upload",
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = raw
        return exc.code, payload


def wait_for_job(job_id: str, label: str) -> dict:
    for _ in range(90):
        status, payload = json_request("GET", f"{JOBS_BASE}/{job_id}")
        if status != 200 or not isinstance(payload, dict):
            raise RuntimeError(f"{label} job lookup failed: {status} {payload}")
        if payload.get("status") == "completed":
            return payload
        if payload.get("status") == "failed":
            raise RuntimeError(f"{label} job failed: {payload}")
        time.sleep(0.5)
    raise RuntimeError(f"{label} job timeout")


def main() -> int:
    print("== Live API verification: canonical imports ==")

    status, health = json_request("GET", "/health")
    if status != 200:
        print(f"FAIL health {status}")
        return 1
    print(f"PASS health: {health}")

    status, openapi = json_request("GET", "/openapi.json")
    if status != 200 or not isinstance(openapi, dict):
        print(f"FAIL openapi {status}")
        return 1
    paths = openapi.get("paths", {})
    required = [
        f"{IMPORTS_BASE}/upload",
        f"{IMPORTS_BASE}/{{batch_id}}",
        f"{IMPORTS_BASE}/{{batch_id}}/column-mapping",
        f"{IMPORTS_BASE}/{{batch_id}}/analyze-job",
        f"{IMPORTS_BASE}/{{batch_id}}/rows",
        f"{IMPORTS_BASE}/{{batch_id}}/rows/{{row_id}}/decision",
        f"{IMPORTS_BASE}/{{batch_id}}/apply-job",
        f"{JOBS_BASE}/{{job_id}}",
    ]
    for path in required:
        if path not in paths:
            print(f"FAIL swagger missing path: {path}")
            return 1
    print("PASS canonical swagger paths present")

    status, fair = create_fair()
    if status != 201 or not isinstance(fair, dict):
        print(f"FAIL fair create {status}: {fair}")
        return 1
    fair_id = fair["id"]
    print(f"PASS fair created: {fair_id}")

    status, upload = upload_xlsx(fair_id, build_xlsx())
    if status != 201 or not isinstance(upload, dict):
        print(f"FAIL upload {status}: {upload}")
        return 1
    batch_id = upload["batch_id"]
    print(f"PASS upload batch: {batch_id}")

    status, mapping = json_request(
        "PATCH",
        f"{IMPORTS_BASE}/{batch_id}/column-mapping",
        {
            "header_mode": "first_row_header",
            "has_header_row": True,
            "mappings": {
                "company_name": {"type": "column_index", "value": 0},
                "email": {"type": "column_index", "value": 1},
                "contact_first_name": {"type": "column_index", "value": 2},
                "contact_last_name": {"type": "column_index", "value": 3},
            },
        },
    )
    if status != 200:
        print(f"FAIL mapping {status}: {mapping}")
        return 1
    print("PASS column mapping")

    status, analyze = json_request("POST", f"{IMPORTS_BASE}/{batch_id}/analyze-job")
    if status != 202 or not isinstance(analyze, dict):
        print(f"FAIL analyze-job {status}: {analyze}")
        return 1
    try:
        wait_for_job(analyze["job_id"], "Analyze")
    except RuntimeError as exc:
        print(f"FAIL {exc}")
        return 1
    print("PASS analyze-job completed")

    status, batch_detail = json_request("GET", f"{IMPORTS_BASE}/{batch_id}")
    if status != 200 or not isinstance(batch_detail, dict) or batch_detail.get("total_rows", 0) < 1:
        print(f"FAIL batch detail {status}: {batch_detail}")
        return 1
    print("PASS batch analyzed summary")

    status, rows = json_request("GET", f"{IMPORTS_BASE}/{batch_id}/rows")
    if status != 200 or not isinstance(rows, dict) or not rows.get("items"):
        print(f"FAIL rows {status}: {rows}")
        return 1
    row_id = rows["items"][0]["id"]
    print("PASS rows preview")

    status, decision = json_request(
        "PATCH",
        f"{IMPORTS_BASE}/{batch_id}/rows/{row_id}/decision",
        {"decision": "create_new"},
    )
    if status != 200:
        print(f"FAIL decision {status}: {decision}")
        return 1
    print("PASS decision set")

    status, apply_started = json_request("POST", f"{IMPORTS_BASE}/{batch_id}/apply-job")
    if status != 202 or not isinstance(apply_started, dict):
        print(f"FAIL apply-job {status}: {apply_started}")
        return 1
    try:
        wait_for_job(apply_started["job_id"], "Apply")
    except RuntimeError as exc:
        print(f"FAIL {exc}")
        return 1

    status, applied_batch = json_request("GET", f"{IMPORTS_BASE}/{batch_id}")
    if status != 200 or not isinstance(applied_batch, dict) or applied_batch.get("created_rows", 0) < 1:
        print(f"FAIL apply result {status}: {applied_batch}")
        return 1
    print(f"PASS apply-job: created={applied_batch.get('created_rows')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
