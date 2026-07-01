#!/usr/bin/env python3
"""Live API smoke test for multi-email normalization."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8001"
ORG = "00000000-0000-4000-8000-000000000010"
HEADERS = {
    "Authorization": "Bearer dev-bypass",
    "X-Organization-Id": ORG,
    "Content-Type": "application/json",
}


def request(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def main() -> int:
    print("== Live API verification: multi-email ==")

    status, customer = request(
        "POST",
        "/api/v1/customers",
        {
            "display_name": "Live Multi Email Customer",
            "email": "info@abc.com ; sales@abc.com, info@abc.com",
        },
    )
    if status != 201 or customer.get("email") != "info@abc.com;sales@abc.com":
        print(f"FAIL customer create {status}: {customer}")
        return 1
    print("PASS customer create/update normalize")

    status, fetched = request("GET", f"/api/v1/customers/{customer['id']}")
    if fetched.get("email") != "info@abc.com;sales@abc.com":
        print(f"FAIL customer get: {fetched}")
        return 1
    print("PASS customer get canonical email")

    status, contact = request(
        "POST",
        "/api/v1/contacts",
        {
            "customer_id": customer["id"],
            "first_name": "Ali",
            "last_name": "Veli",
            "email": "a@x.com, b@y.com ; a@x.com",
        },
    )
    if status != 201 or contact.get("email") != "a@x.com;b@y.com":
        print(f"FAIL contact create {status}: {contact}")
        return 1
    print("PASS contact create normalize")

    status, bad = request(
        "POST",
        "/api/v1/customers",
        {"display_name": "Bad Email", "email": "ok@abc.com;bad@@abc.com"},
    )
    if status != 400 or "bad@@abc.com" not in bad.get("detail", ""):
        print(f"FAIL invalid email rejection {status}: {bad}")
        return 1
    print("PASS invalid email rejected")

    print("RESULT: LIVE MULTI-EMAIL VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
