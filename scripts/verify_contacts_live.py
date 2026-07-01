#!/usr/bin/env python3
"""Live API smoke test for Sprint 03 contacts endpoints."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
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
    print("== Live API verification: contacts ==")

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
        "/api/v1/customers/{customer_id}/contacts",
        "/api/v1/contacts",
        "/api/v1/contacts/{contact_id}",
    ]
    for p in required:
        if p not in paths:
            print(f"FAIL swagger missing path: {p}")
            return 1
    print("PASS swagger paths present")

    status, customer = request(
        "POST",
        "/api/v1/customers",
        {"display_name": f"Live Contact Customer {uuid4().hex[:8]}", "status": "active"},
    )
    if status != 201:
        print(f"FAIL create customer {status}: {customer}")
        return 1
    customer_id = customer["id"]
    print(f"PASS create customer: {customer_id}")

    status, contact = request(
        "POST",
        "/api/v1/contacts",
        {
            "customer_id": customer_id,
            "first_name": "Can",
            "last_name": "Öztürk",
            "title": "Satış",
            "email": "can@example.com",
            "is_primary": True,
        },
    )
    if status != 201:
        print(f"FAIL create contact {status}: {contact}")
        return 1
    contact_id = contact["id"]
    assert contact["full_name"] == "Can Öztürk"
    print(f"PASS create contact: {contact_id}")

    status, listed = request("GET", f"/api/v1/customers/{customer_id}/contacts")
    if status != 200 or listed.get("total", 0) < 1:
        print(f"FAIL list contacts {status}: {listed}")
        return 1
    print("PASS list contacts")

    status, updated = request(
        "PATCH",
        f"/api/v1/contacts/{contact_id}",
        {"title": "Genel Müdür"},
    )
    if status != 200 or updated.get("title") != "Genel Müdür":
        print(f"FAIL update contact {status}: {updated}")
        return 1
    print("PASS update contact")

    status, deleted = request("DELETE", f"/api/v1/contacts/{contact_id}")
    if status != 200 or deleted.get("deleted_at") is None:
        print(f"FAIL delete contact {status}: {deleted}")
        return 1
    print("PASS delete contact")

    print("RESULT: LIVE API VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
