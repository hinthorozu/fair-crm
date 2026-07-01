#!/usr/bin/env python3
"""Live API smoke test for Sprint 07 import engine endpoints."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from io import BytesIO

from openpyxl import Workbook

BASE = "http://127.0.0.1:8001"
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


def upload_xlsx(content: bytes) -> tuple[int, dict | list | str]:
    boundary = "----FairCrmImportBoundary"
    body = (
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
        f"{BASE}/api/v1/imports/customers/upload",
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


def main() -> int:
    print("== Live API verification: imports ==")

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
        "/api/v1/imports/customers/upload",
        "/api/v1/imports/{batch_id}",
        "/api/v1/imports/{batch_id}/rows",
        "/api/v1/imports/{batch_id}/rows/{row_id}/decision",
        "/api/v1/imports/{batch_id}/apply",
    ]
    for path in required:
        if path not in paths:
            print(f"FAIL swagger missing path: {path}")
            return 1
    print("PASS swagger paths present")

    status, batch = upload_xlsx(build_xlsx())
    if status != 201:
        print(f"FAIL upload {status}: {batch}")
        return 1
    batch_id = batch["id"]
    print(f"PASS upload batch: {batch_id}")

    status, batch_detail = json_request("GET", f"/api/v1/imports/{batch_id}")
    if status != 200 or batch_detail.get("total_rows", 0) < 1:
        print(f"FAIL batch detail {status}: {batch_detail}")
        return 1
    print("PASS batch preview summary")

    status, rows = json_request("GET", f"/api/v1/imports/{batch_id}/rows")
    if status != 200 or not rows.get("items"):
        print(f"FAIL rows {status}: {rows}")
        return 1
    row_id = rows["items"][0]["id"]
    print("PASS rows preview")

    status, decision = json_request(
        "PATCH",
        f"/api/v1/imports/{batch_id}/rows/{row_id}/decision",
        {"decision": "create_new"},
    )
    if status != 200:
        print(f"FAIL decision {status}: {decision}")
        return 1
    print("PASS decision set")

    status, applied = json_request("POST", f"/api/v1/imports/{batch_id}/apply")
    if status != 200 or applied.get("created_rows", 0) < 1:
        print(f"FAIL apply {status}: {applied}")
        return 1
    print(f"PASS apply: created={applied.get('created_rows')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
