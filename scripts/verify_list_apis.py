#!/usr/bin/env python3
"""Quick list API contract check after restore."""

import json
import urllib.request

BASE = "http://127.0.0.1:8001"
ORG = "00000000-0000-4000-8000-000000000010"
HEADERS = {
    "Authorization": "Bearer dev-bypass",
    "X-Organization-Id": ORG,
}


def get(path: str) -> tuple[int, dict]:
    req = urllib.request.Request(f"{BASE}{path}", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status, json.loads(resp.read().decode())


for path in [
    "/api/v1/fairs?pageSize=5",
    "/api/v1/customers?pageSize=5",
    "/api/v1/admin/backups?pageSize=5",
    "/api/v1/data-integration/imports?pageSize=5",
]:
    try:
        status, data = get(path)
        pag = data.get("pagination", {})
        print(
            path,
            "status=",
            status,
            "items=",
            len(data.get("items", [])),
            "totalItems=",
            pag.get("totalItems", data.get("total")),
            "keys=",
            list(pag.keys()) if pag else "no-pagination",
        )
    except Exception as exc:
        print(path, "FAIL", exc)
