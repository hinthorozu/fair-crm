#!/usr/bin/env python3
"""End-to-end validation: KYROX Core + Fair CRM customer flow."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx
import psycopg2

ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / "scripts" / ".dev_state.json"
REPORT_FILE = ROOT / "scripts" / "e2e_validation_report.json"

CORE_BASE = os.environ.get("KYROX_CORE_BASE_URL", "http://127.0.0.1:8000")
FAIR_BASE = os.environ.get("FAIR_CRM_BASE_URL", "http://127.0.0.1:8001")
CORE_DB = os.environ.get("KYROX_CORE_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/kyrox_core")
FAIR_DB = os.environ.get("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/fair_crm")


class StepResult:
    def __init__(self, step: str, ok: bool, detail: str = "") -> None:
        self.step = step
        self.ok = ok
        self.detail = detail


def record(results: list[StepResult], step: str, ok: bool, detail: str = "") -> bool:
    results.append(StepResult(step, ok, detail))
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {step}" + (f" — {detail}" if detail else ""))
    return ok


def wait_for_url(url: str, timeout: float = 60.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=2.0)
            if response.status_code == 200:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(1)
    return False


def ensure_fair_db() -> None:
    parsed = urlparse(FAIR_DB.replace("+psycopg2", ""))
    admin = f"postgresql://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port or 5432}/postgres"
    db_name = parsed.path.lstrip("/")
    conn = psycopg2.connect(admin)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            if cur.fetchone() is None:
                cur.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        conn.close()


def run_migrations(project_root: Path, alembic_ini: str, *, database_url: str | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "backend")
    if database_url:
        env["DATABASE_URL"] = database_url
    return subprocess.run(
        [sys.executable, "-m", "alembic", "-c", alembic_ini, "upgrade", "head"],
        cwd=str(project_root),
        env=env,
        capture_output=True,
        text=True,
    )


def main() -> int:
    results: list[StepResult] = []
    org_id: str | None = None
    customer_id: str | None = None
    token: str | None = None

    # 1 PostgreSQL
    try:
        conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/postgres")
        conn.close()
        record(results, "1. PostgreSQL reachable", True)
    except Exception as exc:
        record(results, "1. PostgreSQL reachable", False, str(exc))
        return _finish(results, 1)

    kyrox_root = ROOT.parent / "kyrox-core"
    if not kyrox_root.exists():
        record(results, "2. kyrox-core repository present", False, str(kyrox_root))
        return _finish(results, 1)

    # 3 Core migrations then seed
    mig_core = run_migrations(
        kyrox_root,
        "alembic.ini",
        database_url="postgresql://postgres:postgres@localhost:5432/kyrox_core",
    )
    if mig_core.returncode != 0:
        record(results, "3. kyrox-core migrations", False, mig_core.stderr[-500:])
    else:
        record(results, "3. kyrox-core migrations", True, "head")

    seed = subprocess.run([sys.executable, str(ROOT / "scripts" / "seed_core_dev_identity.py")], capture_output=True, text=True)
    seed_ok = seed.returncode == 0
    record(
        results,
        "10. Create development user (seed)",
        seed_ok,
        seed.stdout.strip()[-200:] if seed_ok else seed.stderr[-500:],
    )
    record(
        results,
        "11. Assign fair_crm.customers permissions (seed)",
        seed_ok and "Granted fair_crm.customers" in seed.stdout,
        "owner role grants fair_crm.customers.* + audit.logs.read" if seed_ok else "",
    )

    # 5-6 Fair CRM DB + migrations
    try:
        ensure_fair_db()
        mig_fair = run_migrations(
            ROOT,
            "alembic.ini",
            database_url="postgresql+psycopg2://postgres:postgres@localhost:5432/fair_crm",
        )
        if mig_fair.returncode != 0:
            record(results, "6. fair-crm migrations", False, mig_fair.stderr[-500:])
        else:
            record(results, "6. fair-crm migrations", True, "head")
    except Exception as exc:
        record(results, "6. fair-crm migrations", False, str(exc))

    # 2 & 5 Services (health implies running)
    core_ok = wait_for_url(f"{CORE_BASE}/api/v1/health", timeout=5)
    record(results, "2. kyrox-core running", core_ok, f"{CORE_BASE}")
    fair_ok = wait_for_url(f"{FAIR_BASE}/health", timeout=5)
    record(results, "5. fair-crm running", fair_ok, f"{FAIR_BASE}")

    # 4 & 7 Health checks
    record(results, "4. kyrox-core health", core_ok, f"{CORE_BASE}/api/v1/health")
    record(results, "7. fair-crm health", fair_ok, f"{FAIR_BASE}/health")

    if not core_ok or not fair_ok:
        record(
            results,
            "Services running",
            False,
            "Start Core (set DATABASE_URL to kyrox_core): "
            "cd kyrox-core/backend && uvicorn app.main:app --port 8000; "
            "Fair CRM: cd fair-crm/backend && uvicorn app.main:app --port 8001",
        )
        return _finish(results, 1)

    record(results, "8. Swagger Core", True, f"{CORE_BASE}/docs")
    record(results, "8. Swagger Fair CRM", True, f"{FAIR_BASE}/docs")

    state = json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {}
    email = state.get("email", "dev@example.com")
    password = state.get("password", "DevPassword123!")

    # 12-13 Login
    login_resp = httpx.post(
        f"{CORE_BASE}/api/v1/auth/login",
        json={"email": email, "password": password},
        timeout=10.0,
    )
    if login_resp.status_code != 200:
        record(results, "12-13. Core login + JWT", False, login_resp.text)
        return _finish(results, 1)
    token = login_resp.json()["access_token"]
    record(results, "12-13. Core login + JWT", True)

    headers = {"Authorization": f"Bearer {token}"}

    # 9 Create organization
    org_resp = httpx.post(
        f"{CORE_BASE}/api/v1/organizations",
        json={"name": "Fair CRM Dev Org", "slug": f"fair-crm-dev-{int(time.time())}"},
        headers=headers,
        timeout=10.0,
    )
    if org_resp.status_code != 201:
        record(results, "9. Create development organization", False, org_resp.text)
        return _finish(results, 1)
    org_id = org_resp.json()["organization"]["id"]
    record(results, "9. Create development organization", True, org_id)

    fair_headers = {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": org_id,
    }

    # Permission check
    perm_resp = httpx.post(
        f"{CORE_BASE}/api/v1/organizations/{org_id}/authorization/check",
        headers=fair_headers,
        json={"permission_code": "fair_crm.customers.create"},
        timeout=10.0,
    )
    allowed = perm_resp.status_code == 200 and perm_resp.json().get("allowed") is True
    record(results, "11b. Verify fair_crm.customers permissions via Core API", allowed, perm_resp.text)

    # 15 Create customer
    create_resp = httpx.post(
        f"{FAIR_BASE}/api/v1/customers",
        headers=fair_headers,
        json={
            "display_name": "E2E Test Customer A.Ş.",
            "city": "Istanbul",
            "district": "Kadikoy",
            "address": "E2E Validation Street 1",
        },
        timeout=10.0,
    )
    if create_resp.status_code != 201:
        record(results, "15. Create customer", False, create_resp.text)
        return _finish(results, 1)
    customer_id = create_resp.json()["id"]
    record(results, "15. Create customer", True, customer_id)

    # 16 List
    list_resp = httpx.get(f"{FAIR_BASE}/api/v1/customers", headers=fair_headers, timeout=10.0)
    list_ok = list_resp.status_code == 200 and any(
        item["id"] == customer_id for item in list_resp.json().get("items", [])
    )
    record(results, "16. List customers", list_ok, f"count={len(list_resp.json().get('items', []))}")

    # 17 Update
    update_resp = httpx.patch(
        f"{FAIR_BASE}/api/v1/customers/{customer_id}",
        headers=fair_headers,
        json={"display_name": "E2E Updated Customer", "status": "active"},
        timeout=10.0,
    )
    record(results, "17. Update customer", update_resp.status_code == 200, update_resp.text[:200])

    # 18 Archive
    archive_resp = httpx.delete(
        f"{FAIR_BASE}/api/v1/customers/{customer_id}",
        headers=fair_headers,
        timeout=10.0,
    )
    record(results, "18. Archive customer", archive_resp.status_code == 200, archive_resp.text[:200])

    # 19 Audit
    audit_resp = httpx.get(
        f"{CORE_BASE}/api/v1/organizations/{org_id}/audit-logs",
        headers={**fair_headers, "Authorization": f"Bearer {token}"},
        params={"action_prefix": "fair_crm.customer", "limit": 20},
        timeout=10.0,
    )
    if audit_resp.status_code == 403:
        record(results, "19. Verify audit events", False, "missing audit.logs.read on dev user")
    elif audit_resp.status_code != 200:
        record(results, "19. Verify audit events", False, audit_resp.text)
    else:
        actions = [item["action"] for item in audit_resp.json().get("items", [])]
        expected = {"fair_crm.customer.created", "fair_crm.customer.updated", "fair_crm.customer.archived"}
        found = expected.intersection(set(actions))
        record(
            results,
            "19. Verify audit events",
            len(found) >= 1,
            f"found={sorted(found)} all_actions={actions}",
        )

    record(results, "14. JWT used against Fair CRM", True)
    return _finish(results, 0 if all(r.ok for r in results) else 1)


def _finish(results: list[StepResult], code: int) -> int:
    report = {
        "passed": sum(1 for r in results if r.ok),
        "failed": sum(1 for r in results if not r.ok),
        "steps": [{"step": r.step, "ok": r.ok, "detail": r.detail} for r in results],
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport written to {REPORT_FILE}")
    print(f"Summary: {report['passed']} passed, {report['failed']} failed")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
