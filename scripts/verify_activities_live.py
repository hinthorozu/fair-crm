#!/usr/bin/env python3
"""Live API smoke test for Sprint 04 activities endpoints."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from uuid import uuid4

BASE = "http://127.0.0.1:8001"
ORG = "00000000-0000-4000-8000-000000000010"
HEADERS = {
    "Authorization": "Bearer dev-bypass",
    "X-Organization-Id": ORG,
    "Content-Type": "application/json",
}


def request(method: str, path: str, body: dict | None = None) -> tuple[int, dict | list | str]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
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
    print("== Live API verification: activities ==")

    status, health = request("GET", "/health")
    if status != 200:
        print(f"FAIL health {status}")
        return 1
    print(f"PASS health: {health}")

    status, openapi = request("GET", "/openapi.json")
    if status != 200:
        print(f"FAIL openapi {status}")
        return 1
    paths = openapi.get("paths", {})
    required = [
        "/api/v1/customers/{customer_id}/activities",
        "/api/v1/activities",
        "/api/v1/activities/{activity_id}",
    ]
    for p in required:
        if p not in paths:
            print(f"FAIL swagger missing path: {p}")
            return 1
    print("PASS swagger paths present")

    status, customer = request(
        "POST",
        "/api/v1/customers",
        {"display_name": f"Live Activity Customer {uuid4().hex[:8]}", "status": "active"},
    )
    if status != 201:
        print(f"FAIL create customer {status}: {customer}")
        return 1
    customer_id = customer["id"]
    print(f"PASS create customer: {customer_id}")

    now = datetime.now(tz=UTC).isoformat()
    status, activity = request(
        "POST",
        "/api/v1/activities",
        {
            "customer_id": customer_id,
            "type": "call",
            "subject": "Live test call",
            "activity_date": now,
            "status": "open",
        },
    )
    if status != 201:
        print(f"FAIL create activity {status}: {activity}")
        return 1
    activity_id = activity["id"]
    assert activity["source"] == "manual"
    print(f"PASS create activity: {activity_id}")

    status, listed = request("GET", f"/api/v1/customers/{customer_id}/activities")
    if status != 200 or listed.get("total", 0) < 1:
        print(f"FAIL list activities {status}: {listed}")
        return 1
    print(f"PASS list activities: total={listed['total']}")

    status, updated = request(
        "PATCH",
        f"/api/v1/activities/{activity_id}",
        {"subject": "Updated live subject", "status": "completed"},
    )
    if status != 200 or updated.get("subject") != "Updated live subject":
        print(f"FAIL update activity {status}: {updated}")
        return 1
    print("PASS update activity")

    status, deleted = request("DELETE", f"/api/v1/activities/{activity_id}")
    if status != 200 or deleted.get("deleted_at") is None:
        print(f"FAIL delete activity {status}: {deleted}")
        return 1
    print("PASS delete activity (soft delete)")

    status, get_after = request("GET", f"/api/v1/activities/{activity_id}")
    if status != 404:
        print(f"FAIL get after delete expected 404 got {status}: {get_after}")
        return 1
    print("PASS get after delete returns 404")

    print("== All activity live checks passed ==")
    return 0


if __name__ == "__main__":
    sys.exit(main())
