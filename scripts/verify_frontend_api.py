#!/usr/bin/env python3
"""Verify Fair CRM frontend API integration (same calls the UI makes)."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8001"
ORG = "00000000-0000-4000-8000-000000000010"
TOKEN = "dev-bypass"
REPORT = Path(__file__).resolve().parent / "frontend_verification_report.json"


def req(method: str, path: str, body: dict | None = None) -> tuple[int, dict | list | str]:
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "X-Organization-Id": ORG,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as resp:
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
    stamp = int(time.time())
    results: list[dict] = []
    created_id: str | None = None

    def step(name: str, ok: bool, detail: str = "") -> None:
        results.append({"step": name, "ok": ok, "detail": detail})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))

    code, data = req("GET", "/api/v1/customers?page_size=5")
    step("List customers", code == 200, f"count={len(data.get('items', [])) if isinstance(data, dict) else 0}")

    code, data = req("GET", "/api/v1/customers?search=Sinan&page_size=10")
    items = data.get("items", []) if isinstance(data, dict) else []
    step("Search Sinan", code == 200 and isinstance(items, list), f"matches={len(items)}")

    create_body = {
        "display_name": f"Frontend Test {stamp}",
        "legal_name": f"Frontend Test Ltd. {stamp}",
        "trade_name": "FT",
        "customer_type": "lead",
        "status": "active",
        "country": "Türkiye",
        "city": "İstanbul",
        "district": "Kadıköy",
        "address": "Test Sokak 1",
        "website": "https://frontend-test.example.com",
        "phone": "+90 555 000 1234",
        "email": f"frontend{stamp}@example.com",
        "source": "manual",
        "description": "Frontend verification customer",
    }
    code, data = req("POST", "/api/v1/customers", create_body)
    ok_create = code == 201 and isinstance(data, dict)
    created_id = data.get("id") if ok_create else None
    step("Create customer", ok_create, str(created_id))

    if created_id:
        code, data = req(
            "PATCH",
            f"/api/v1/customers/{created_id}",
            {"phone": "905550001234", "website": "frontend-test.example.com", "description": "Updated from frontend verify"},
        )
        step("Update customer", code == 200, str(data.get("phone") if isinstance(data, dict) else ""))

        code, _ = req("DELETE", f"/api/v1/customers/{created_id}")
        step("Archive customer", code == 200)

        code, data = req("GET", f"/api/v1/customers/{created_id}")
        step("Get archived by id (404 expected)", code == 404, str(code))

    report = {"passed": sum(1 for r in results if r["ok"]), "failed": sum(1 for r in results if not r["ok"]), "steps": results}
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport: {REPORT}")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
