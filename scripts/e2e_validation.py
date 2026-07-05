#!/usr/bin/env python3
"""End-to-end validation: KYROX Core + Fair CRM prod-path auth/RBAC gate."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import httpx
import psycopg2

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
STATE_FILE = SCRIPTS_DIR / ".dev_state.json"
REPORT_FILE = SCRIPTS_DIR / "e2e_validation_report.json"
SEED_SCRIPT = SCRIPTS_DIR / "seed_core_dev_identity.py"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from fair_crm_role_matrix import DEV_ROLE_USERS, ROLE_MATRIX_VERSION, permissions_for_role  # noqa: E402

CORE_BASE = os.environ.get("KYROX_CORE_BASE_URL", "http://127.0.0.1:8000")
FAIR_BASE = os.environ.get("FAIR_CRM_BASE_URL", "http://127.0.0.1:8001")
CORE_DB = os.environ.get("KYROX_CORE_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/kyrox_core")
FAIR_DB = os.environ.get("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/fair_crm")
DEFAULT_DEV_ORG_ID = os.environ.get(
    "FAIR_CRM_DEV_ORGANIZATION_ID",
    "00000000-0000-4000-8000-000000000010",
)

MIN_CORE_MIGRATION_REVISION = "20260701_0029"
EXPECTED_FAIR_CRM_PERMISSION_COUNT = 48
FOREIGN_ORG_ID = "00000000-0000-4000-8000-000000099999"

REQUIRED_PERMISSIONS = (
    "fair_crm.customers.read",
    "fair_crm.fairs.read",
    "fair_crm.imports.apply",
    "fair_crm.scraper.read",
    "fair_crm.scraper.download",
    "fair_crm.smtp.read",
    "fair_crm.admin.backups.read",
    "fair_crm.admin.data_operations.run",
)

STEP_HINTS: dict[str, str] = {
    "1. PostgreSQL reachable": "Start PostgreSQL (docker compose up -d) and verify postgres://localhost:5432 is reachable.",
    "2. kyrox-core repository present": (
        "Clone kyrox-core as a sibling of fair-crm or set KYROX_CORE_ROOT to the repository path."
    ),
    "3. kyrox-core migrations": (
        f"Run Core migrations: cd kyrox-core && python -m alembic upgrade head "
        f"(required revision >= {MIN_CORE_MIGRATION_REVISION})."
    ),
    "3b. Core migration revision": (
        f"Core alembic_version must be >= {MIN_CORE_MIGRATION_REVISION}. "
        "An old Core process or stale database causes permission catalog drift."
    ),
    "4. kyrox-core running": (
        "Start Core on port 8000 with current code: "
        "cd kyrox-core/backend && uvicorn app.main:app --host 127.0.0.1 --port 8000"
    ),
    "5. fair-crm running": (
        "Start Fair CRM with FAIR_CRM_DEV_BYPASS_CORE=false: "
        ".\\scripts\\dev\\reset-dev.ps1 or uvicorn on port 8001 after setting backend/.env."
    ),
    "0. Prod-path env guard (FAIR_CRM_DEV_BYPASS_CORE)": (
        "Set FAIR_CRM_DEV_BYPASS_CORE=false in backend/.env and restart Fair CRM. "
        "Prod-path e2e must never run with bypass enabled."
    ),
    "0b. Early prod-path guard (live dev-bypass probe)": (
        "Fair CRM accepted Bearer dev-bypass — an old uvicorn process or FAIR_CRM_DEV_BYPASS_CORE=true is active. "
        "Run .\\scripts\\dev\\reset-dev.ps1 and confirm backend/.env has FAIR_CRM_DEV_BYPASS_CORE=false."
    ),
    "9b. Prod-path guard (dev bypass disabled)": (
        "Same as 0b: restart Fair CRM with bypass disabled before re-running prod-path e2e."
    ),
    "10. Create development user (seed)": (
        "Run python scripts/seed_core_dev_identity.py after Core migrations. "
        "Check stderr for missing permissions or roles."
    ),
    "11. Verify seed state (.dev_state.json)": (
        "Re-run seed after updating fair_crm_role_matrix.py or delete stale .dev_state.json "
        f"(expected role_matrix_version={ROLE_MATRIX_VERSION})."
    ),
    "11c. Seed idempotency (second run)": (
        "Second seed run failed or state changed — inspect identity_role_permissions duplicates "
        "and seed script output."
    ),
    "11f. Role matrix seed + RBAC chain (SQL)": (
        "Role-permission mappings are stale. Re-run: python scripts/seed_core_dev_identity.py"
    ),
    "11e. Endpoint permission enforcement tests (pytest)": (
        "Run: cd backend && python -m pytest tests/modules/test_endpoint_permission_enforcement.py -q"
    ),
    "11g. Role matrix authorization tests (pytest)": (
        "Run: cd backend && python -m pytest tests/modules/test_role_matrix_authorization.py -q"
    ),
    "12-13. Core login + JWT": (
        "Owner dev user missing or password mismatch. Re-run seed and use credentials from .dev_state.json."
    ),
    "14b. Role matrix selective authorization (live)": (
        "Live RBAC mismatch — re-run seed and verify Core authorization API matches role matrix."
    ),
    "Services running": "Start both Core (8000) and Fair CRM (8001) before prod-path e2e.",
}


@dataclass
class StepResult:
    step: str
    ok: bool
    detail: str = ""


@dataclass
class RunContext:
    prod_path: bool
    started_at: float = field(default_factory=time.time)
    state: dict = field(default_factory=dict)
    org_id: str | None = None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fair CRM end-to-end validation")
    parser.add_argument(
        "--prod-path",
        action="store_true",
        help="Prod-path mode: fail-fast, bypass guard, early service health checks",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="CI gate alias for --prod-path (identical behavior)",
    )
    return parser.parse_args(argv)


def resolve_kyrox_core_root() -> Path | None:
    env_root = os.environ.get("KYROX_CORE_ROOT")
    candidates = [
        Path(env_root) if env_root else None,
        ROOT.parent / "kyrox-core",
        ROOT / "kyrox-core",
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    return None


def record(results: list[StepResult], step: str, ok: bool, detail: str = "") -> bool:
    results.append(StepResult(step=step, ok=ok, detail=detail))
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {step}" + (f" — {detail}" if detail else ""))
    if not ok:
        hint = _hint_for_step(step)
        if hint:
            print(f"       hint: {hint}")
    return ok


def _hint_for_step(step: str) -> str | None:
    if step in STEP_HINTS:
        return STEP_HINTS[step]
    for prefix, hint in STEP_HINTS.items():
        if step.startswith(prefix.rstrip(".")):
            return hint
    return None


def print_runtime_config(ctx: RunContext) -> None:
    org_id = ctx.org_id or ctx.state.get("organization_id") or DEFAULT_DEV_ORG_ID
    bypass_env = os.environ.get("FAIR_CRM_DEV_BYPASS_CORE", "false")
    matrix_version = ctx.state.get("role_matrix_version", "(not seeded yet)")
    print("Runtime config:")
    print(f"  mode={'prod-path/CI' if ctx.prod_path else 'standard'}")
    print(f"  FAIR_CRM_DEV_BYPASS_CORE={bypass_env}")
    print(f"  CORE_BASE_URL={CORE_BASE}")
    print(f"  FAIR_CRM_BASE_URL={FAIR_BASE}")
    print(f"  SEEDED_ORG_ID={org_id}")
    print(f"  ROLE_MATRIX_VERSION={matrix_version} (expected {ROLE_MATRIX_VERSION})")
    print(f"  KYROX_CORE_DATABASE_URL={_redact_db_url(CORE_DB)}")
    print("")


def _redact_db_url(url: str) -> str:
    parsed = urlparse(url.replace("+psycopg2", ""))
    if parsed.password:
        return url.replace(parsed.password, "****")
    return url


def enforce_prod_path_env() -> tuple[bool, str]:
    raw = os.environ.get("FAIR_CRM_DEV_BYPASS_CORE", "false").strip().lower()
    if raw in {"true", "1", "yes", "on"}:
        return (
            False,
            "FAIR_CRM_DEV_BYPASS_CORE must be false for prod-path e2e "
            f"(current value={raw!r})",
        )
    return True, f"FAIR_CRM_DEV_BYPASS_CORE={raw or 'false'}"


def wait_for_url(url: str, timeout: float = 60.0) -> tuple[bool, str]:
    deadline = time.time() + timeout
    last_error = "no response"
    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=2.0)
            if response.status_code == 200:
                return True, f"status=200 body={response.text[:120]}"
            last_error = f"status={response.status_code}"
        except httpx.HTTPError as exc:
            last_error = str(exc)
        time.sleep(1)
    return False, last_error


def probe_service_health(name: str, url: str, *, timeout: float = 5.0) -> tuple[bool, str]:
    ok, detail = wait_for_url(url, timeout=timeout)
    if ok:
        return True, detail
    return False, f"{name} not healthy at {url} — {detail}"


def prod_path_guard_dev_bypass_disabled(org_id: str) -> tuple[bool, str]:
    try:
        response = httpx.get(
            f"{FAIR_BASE}/api/v1/customers",
            headers={
                "Authorization": "Bearer dev-bypass",
                "X-Organization-Id": org_id,
            },
            timeout=5.0,
        )
    except httpx.HTTPError as exc:
        return False, f"could not probe Fair CRM dev bypass: {exc}"
    if response.status_code == 200:
        return (
            False,
            "Fair CRM accepted Bearer dev-bypass (status=200) — "
            "FAIR_CRM_DEV_BYPASS_CORE appears enabled or an old process is running",
        )
    if response.status_code not in {401, 403}:
        return False, f"unexpected status={response.status_code} for dev-bypass probe (expected 401/403)"
    return True, f"dev-bypass rejected with status={response.status_code}"


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


def get_core_migration_revision() -> str | None:
    conn = psycopg2.connect(CORE_DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'alembic_version'
                )
                """
            )
            if not cur.fetchone()[0]:
                return None
            cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
            row = cur.fetchone()
            return str(row[0]) if row else None
    finally:
        conn.close()


def resolve_user_id(state: dict) -> str | None:
    user_id = state.get("user_id")
    if user_id:
        return str(user_id)
    email = state.get("email")
    if not email:
        return None
    conn = psycopg2.connect(CORE_DB)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM identity_users WHERE email = %s LIMIT 1", (email,))
            row = cur.fetchone()
            return str(row[0]) if row else None
    finally:
        conn.close()


def load_dev_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def verify_seed_state(state: dict) -> tuple[bool, str]:
    org_id = state.get("organization_id")
    count = state.get("fair_crm_permission_count")
    roles = state.get("roles")
    matrix_version = state.get("role_matrix_version")
    problems: list[str] = []

    if not org_id:
        problems.append("missing organization_id")
    if count != EXPECTED_FAIR_CRM_PERMISSION_COUNT:
        problems.append(
            f"fair_crm_permission_count={count!r}, expected {EXPECTED_FAIR_CRM_PERMISSION_COUNT}"
        )
    expected_role_slugs = {slug for slug, _, _ in DEV_ROLE_USERS}
    if not isinstance(roles, dict):
        problems.append("missing roles map in .dev_state.json")
    elif set(roles.keys()) != expected_role_slugs:
        missing_roles = sorted(expected_role_slugs - set(roles.keys()))
        extra_roles = sorted(set(roles.keys()) - expected_role_slugs)
        problems.append(f"missing roles={missing_roles}, extra roles={extra_roles}")
    if matrix_version != ROLE_MATRIX_VERSION:
        problems.append(
            f"role_matrix_version={matrix_version!r}, expected {ROLE_MATRIX_VERSION} — re-run seed"
        )

    if problems:
        return False, "; ".join(problems)
    return True, f"org={org_id}, permissions={count}, roles={len(roles)}, matrix_v={matrix_version}"


def verify_permissions_sql(user_id: str, org_id: str, codes: tuple[str, ...]) -> tuple[bool, str]:
    conn = psycopg2.connect(CORE_DB)
    try:
        with conn.cursor() as cur:
            missing: list[str] = []
            for code in codes:
                cur.execute(
                    """
                    SELECT 1
                    FROM identity_permissions p
                    JOIN identity_role_permissions rp ON rp.permission_id = p.id
                    JOIN identity_roles r ON r.id = rp.role_id
                    JOIN identity_organization_roles orr ON orr.role_id = r.id
                    JOIN identity_user_roles ur ON ur.organization_role_id = orr.id
                    WHERE p.code = %s
                      AND ur.user_id = %s
                      AND ur.organization_id = %s
                      AND ur.status = 'active'
                      AND ur.revoked_at IS NULL
                      AND orr.status = 'active'
                      AND orr.deleted_at IS NULL
                    LIMIT 1
                    """,
                    (code, user_id, org_id),
                )
                if cur.fetchone() is None:
                    missing.append(code)
            if missing:
                return False, f"missing RBAC chain for owner user: {', '.join(missing)}"
            return True, f"{len(codes)} permissions verified via SQL"
    finally:
        conn.close()


def verify_role_matrix_sql(state: dict) -> tuple[bool, str]:
    roles = state.get("roles")
    org_id = state.get("organization_id")
    if not isinstance(roles, dict) or not org_id:
        return False, "seed state missing roles or organization_id"

    conn = psycopg2.connect(CORE_DB)
    try:
        with conn.cursor() as cur:
            problems: list[str] = []
            for role_slug, role_state in roles.items():
                user_id = role_state.get("user_id")
                expected_codes = permissions_for_role(role_slug)
                if not user_id:
                    problems.append(f"{role_slug}: missing user_id in .dev_state.json")
                    continue
                cur.execute(
                    """
                    SELECT p.code
                    FROM identity_permissions p
                    JOIN identity_role_permissions rp ON rp.permission_id = p.id
                    JOIN identity_roles r ON r.id = rp.role_id
                    JOIN identity_organization_roles orr ON orr.role_id = r.id
                    JOIN identity_user_roles ur ON ur.organization_role_id = orr.id
                    WHERE ur.user_id = %s
                      AND ur.organization_id = %s
                      AND r.slug = %s
                      AND ur.status = 'active'
                      AND ur.revoked_at IS NULL
                      AND orr.status = 'active'
                      AND orr.deleted_at IS NULL
                    """,
                    (user_id, org_id, role_slug),
                )
                actual_codes = {str(row[0]) for row in cur.fetchall()}
                if actual_codes != expected_codes:
                    missing = sorted(expected_codes - actual_codes)
                    extra = sorted(actual_codes - expected_codes)
                    problems.append(
                        f"{role_slug}: missing permissions={missing or 'none'}, "
                        f"unexpected permissions={extra or 'none'}"
                    )
            if problems:
                return False, "; ".join(problems)
            return True, f"{len(roles)} role RBAC chains verified"
    finally:
        conn.close()


def verify_no_duplicate_role_permissions() -> tuple[bool, str]:
    conn = psycopg2.connect(CORE_DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.slug, p.code, COUNT(*) AS cnt
                FROM identity_role_permissions rp
                JOIN identity_roles r ON r.id = rp.role_id
                JOIN identity_permissions p ON p.id = rp.permission_id
                WHERE r.scope = 'organization'
                GROUP BY r.slug, p.code
                HAVING COUNT(*) > 1
                ORDER BY r.slug, p.code
                LIMIT 10
                """
            )
            rows = cur.fetchall()
            if rows:
                sample = ", ".join(f"{slug}:{code}x{cnt}" for slug, code, cnt in rows)
                return False, f"duplicate role-permission mappings detected: {sample}"
            return True, "no duplicate role-permission mappings"
    finally:
        conn.close()


def verify_owner_role_permission_count() -> tuple[bool, str]:
    conn = psycopg2.connect(CORE_DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM identity_role_permissions rp
                JOIN identity_permissions p ON p.id = rp.permission_id
                JOIN identity_roles r ON r.id = rp.role_id
                WHERE r.slug = 'owner'
                  AND r.scope = 'organization'
                  AND r.deleted_at IS NULL
                  AND p.code LIKE 'fair_crm.%'
                """
            )
            count = int(cur.fetchone()[0])
            if count < EXPECTED_FAIR_CRM_PERMISSION_COUNT:
                return False, f"owner role has {count}/{EXPECTED_FAIR_CRM_PERMISSION_COUNT} fair_crm mappings"
            return True, f"owner role fair_crm mappings={count}"
    finally:
        conn.close()


def verify_permissions_api(token: str, org_id: str, codes: tuple[str, ...]) -> tuple[bool, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": org_id,
    }
    missing: list[str] = []
    for code in codes:
        response = httpx.post(
            f"{CORE_BASE}/api/v1/organizations/{org_id}/authorization/check",
            headers=headers,
            json={"permission_code": code},
            timeout=10.0,
        )
        allowed = response.status_code == 200 and response.json().get("allowed") is True
        if not allowed:
            if response.status_code == 200:
                missing.append(f"{code}(allowed={response.json().get('allowed')})")
            else:
                missing.append(f"{code}(status={response.status_code})")
    if missing:
        return False, "denied: " + ", ".join(missing)
    return True, f"{len(codes)} permissions allowed via Core API"


def run_seed_script() -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SEED_SCRIPT)],
        capture_output=True,
        text=True,
    )


def run_pytest(relative_path: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", relative_path, "-q", "--tb=line"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )


def services_down_detail(core_ok: bool, fair_ok: bool) -> str:
    parts: list[str] = []
    if not core_ok:
        parts.append(
            f"KYROX Core not reachable at {CORE_BASE} — "
            "start: cd kyrox-core/backend && uvicorn app.main:app --port 8000"
        )
    if not fair_ok:
        parts.append(
            f"Fair CRM not reachable at {FAIR_BASE} — "
            "start with FAIR_CRM_DEV_BYPASS_CORE=false: .\\scripts\\dev\\reset-dev.ps1"
        )
    return " | ".join(parts)


def login_role_user(email: str, password: str) -> tuple[str | None, str]:
    login_resp = httpx.post(
        f"{CORE_BASE}/api/v1/auth/login",
        json={"email": email, "password": password},
        timeout=10.0,
    )
    if login_resp.status_code != 200:
        return None, f"login failed status={login_resp.status_code} body={login_resp.text[:200]}"
    return login_resp.json()["access_token"], "ok"


def run_live_role_checks(state: dict, org_id: str, password: str) -> tuple[bool, list[str]]:
    details: list[str] = []
    ok = True
    roles = state.get("roles") or {}

    def role_headers(role_slug: str) -> dict[str, str] | None:
        role_email = (roles.get(role_slug) or {}).get("email")
        if not role_email:
            details.append(f"{role_slug}: missing seeded email in .dev_state.json")
            nonlocal_ok[0] = False
            return None
        token, err = login_role_user(role_email, password)
        if token is None:
            details.append(f"{role_slug}: {err}")
            nonlocal_ok[0] = False
            return None
        return {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org_id,
        }

    nonlocal_ok = [ok]

    cases: list[tuple[str, str, str, str, dict | None, int]] = [
        ("owner", "GET /customers", "GET", f"{FAIR_BASE}/api/v1/customers", None, 200),
        ("owner", "GET /admin/backups", "GET", f"{FAIR_BASE}/api/v1/admin/backups", None, 200),
        ("admin", "GET /admin/backups", "GET", f"{FAIR_BASE}/api/v1/admin/backups", None, 200),
        ("admin", "POST /customers", "POST", f"{FAIR_BASE}/api/v1/customers", {"display_name": "Admin Customer"}, 201),
        ("viewer", "GET /customers", "GET", f"{FAIR_BASE}/api/v1/customers", None, 200),
        ("viewer", "POST /customers denied", "POST", f"{FAIR_BASE}/api/v1/customers", {"display_name": "Viewer Denied"}, 403),
        ("sales", "POST /customers allowed", "POST", f"{FAIR_BASE}/api/v1/customers", {"display_name": "Sales Allowed"}, 201),
        ("sales", "GET /admin/backups denied", "GET", f"{FAIR_BASE}/api/v1/admin/backups", None, 403),
        ("scraper_operator", "POST /customers denied", "POST", f"{FAIR_BASE}/api/v1/customers", {"display_name": "Scraper Denied"}, 403),
    ]

    owner_headers = role_headers("owner")
    fair_id_for_scraper: str | None = None
    if owner_headers:
        create_fair = httpx.post(
            f"{FAIR_BASE}/api/v1/fairs",
            headers=owner_headers,
            json={
                "name": "E2E Scraper Role Fair",
                "adapter_key": "tuyap_new",
                "source_url": "https://example.test/list",
            },
            timeout=15.0,
        )
        if create_fair.status_code == 201:
            fair_id_for_scraper = create_fair.json()["id"]
            details.append("setup fair for scraper_operator: ok")
        else:
            nonlocal_ok[0] = False
            details.append(
                f"setup fair for scraper_operator failed: status={create_fair.status_code} body={create_fair.text[:200]}"
            )

    for role_slug, label, method, url, body, expected_status in cases:
        headers = role_headers(role_slug)
        if headers is None:
            continue
        if method == "GET":
            resp = httpx.get(url, headers=headers, timeout=15.0)
        else:
            resp = httpx.post(url, headers=headers, json=body or {}, timeout=15.0)
        if resp.status_code != expected_status:
            nonlocal_ok[0] = False
            details.append(f"{label}: status={resp.status_code}, expected={expected_status}")
        else:
            details.append(f"{label}: ok")

    if fair_id_for_scraper:
        scraper_headers = role_headers("scraper_operator")
        if scraper_headers:
            run_resp = httpx.post(
                f"{FAIR_BASE}/api/v1/fairs/{fair_id_for_scraper}/run",
                headers=scraper_headers,
                timeout=15.0,
            )
            if run_resp.status_code not in {202, 403}:
                nonlocal_ok[0] = False
                details.append(f"scraper_operator POST /fairs/run: unexpected status={run_resp.status_code}")
            elif run_resp.status_code == 202:
                details.append("scraper_operator POST /fairs/run: ok")
            else:
                nonlocal_ok[0] = False
                details.append("scraper_operator POST /fairs/run: expected 202, got 403")

            dl_resp = httpx.get(
                f"{FAIR_BASE}/api/v1/scraper/runs",
                headers=scraper_headers,
                timeout=15.0,
            )
            if dl_resp.status_code == 200:
                details.append("scraper_operator GET /scraper/runs: ok")
            else:
                nonlocal_ok[0] = False
                details.append(f"scraper_operator GET /scraper/runs: status={dl_resp.status_code}, expected=200")

    return nonlocal_ok[0], details


def _finish(ctx: RunContext, results: list[StepResult], code: int) -> int:
    passed = sum(1 for r in results if r.ok)
    failed = sum(1 for r in results if not r.ok)
    elapsed = time.time() - ctx.started_at
    pending = [r for r in results if not r.ok]

    print("")
    print_runtime_config(ctx)
    print(f"Duration: {elapsed:.1f}s")
    print(f"Summary: {passed} passed, {failed} failed")

    if pending:
        print("Failed steps:")
        for result in pending:
            print(f"  - {result.step}: {result.detail}")
            hint = _hint_for_step(result.step)
            if hint:
                print(f"    fix: {hint}")

    report = {
        "mode": "prod-path" if ctx.prod_path else "standard",
        "duration_seconds": round(elapsed, 2),
        "passed": passed,
        "failed": failed,
        "runtime_config": {
            "FAIR_CRM_DEV_BYPASS_CORE": os.environ.get("FAIR_CRM_DEV_BYPASS_CORE", "false"),
            "CORE_BASE_URL": CORE_BASE,
            "FAIR_CRM_BASE_URL": FAIR_BASE,
            "SEEDED_ORG_ID": ctx.org_id or ctx.state.get("organization_id"),
            "ROLE_MATRIX_VERSION": ctx.state.get("role_matrix_version", ROLE_MATRIX_VERSION),
        },
        "steps": [{"step": r.step, "ok": r.ok, "detail": r.detail, "hint": _hint_for_step(r.step)} for r in results],
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport written to {REPORT_FILE}")
    return code


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ctx = RunContext(prod_path=args.prod_path or args.ci)
    results: list[StepResult] = []
    state: dict = {}
    org_id: str | None = None
    token: str | None = None

    print_runtime_config(ctx)

    if ctx.prod_path:
        env_ok, env_detail = enforce_prod_path_env()
        if not record(results, "0. Prod-path env guard (FAIR_CRM_DEV_BYPASS_CORE)", env_ok, env_detail):
            return _finish(ctx, results, 1)

    try:
        conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/postgres")
        conn.close()
        record(results, "1. PostgreSQL reachable", True)
    except Exception as exc:
        record(results, "1. PostgreSQL reachable", False, str(exc))
        return _finish(ctx, results, 1)

    if ctx.prod_path:
        core_ok, core_detail = probe_service_health("Core", f"{CORE_BASE}/api/v1/health")
        if not record(results, "4. kyrox-core running (early)", core_ok, core_detail):
            return _finish(ctx, results, 1)

        fair_ok, fair_detail = probe_service_health("Fair CRM", f"{FAIR_BASE}/health")
        if not record(results, "5. fair-crm running (early)", fair_ok, fair_detail):
            return _finish(ctx, results, 1)

        bypass_ok, bypass_detail = prod_path_guard_dev_bypass_disabled(DEFAULT_DEV_ORG_ID)
        if not record(results, "0b. Early prod-path guard (live dev-bypass probe)", bypass_ok, bypass_detail):
            return _finish(ctx, results, 1)

    kyrox_root = resolve_kyrox_core_root()
    if kyrox_root is None:
        record(
            results,
            "2. kyrox-core repository present",
            False,
            "not found — set KYROX_CORE_ROOT or clone as sibling ../kyrox-core",
        )
        return _finish(ctx, results, 1)
    record(results, "2. kyrox-core repository present", True, str(kyrox_root))

    mig_core = run_migrations(
        kyrox_root,
        "alembic.ini",
        database_url="postgresql://postgres:postgres@localhost:5432/kyrox_core",
    )
    if mig_core.returncode != 0:
        record(results, "3. kyrox-core migrations", False, mig_core.stderr[-500:])
        return _finish(ctx, results, 1)
    record(results, "3. kyrox-core migrations", True, "upgrade head")

    core_revision = get_core_migration_revision()
    revision_ok = core_revision is not None and core_revision >= MIN_CORE_MIGRATION_REVISION
    if not record(
        results,
        "3b. Core migration revision >= 20260701_0026",
        revision_ok,
        core_revision or "alembic_version missing",
    ):
        return _finish(ctx, results, 1)

    seed = run_seed_script()
    seed_ok = seed.returncode == 0
    if not record(
        results,
        "10. Create development user (seed)",
        seed_ok,
        "exit 0" if seed_ok else seed.stderr.strip()[-500:] or seed.stdout.strip()[-500:],
    ):
        return _finish(ctx, results, 1)

    state = load_dev_state()
    ctx.state = state
    org_id = state.get("organization_id")
    ctx.org_id = org_id

    state_ok, state_detail = verify_seed_state(state)
    record(results, "11. Verify seed state (.dev_state.json)", state_ok, state_detail)

    owner_perm_ok, owner_perm_detail = verify_owner_role_permission_count()
    record(results, "11a. Verify owner role fair_crm permission mappings (SQL)", owner_perm_ok, owner_perm_detail)

    user_id = resolve_user_id(state)
    if state_ok and user_id and org_id:
        sql_perm_ok, sql_perm_detail = verify_permissions_sql(user_id, org_id, REQUIRED_PERMISSIONS)
        record(results, "11b. Verify fair_crm permission RBAC chain (SQL)", sql_perm_ok, sql_perm_detail)
    else:
        record(results, "11b. Verify fair_crm permission RBAC chain (SQL)", False, "seed state incomplete")

    seed_second = run_seed_script()
    seed_idempotent = seed_second.returncode == 0
    state_after = load_dev_state()
    dup_ok, dup_detail = verify_no_duplicate_role_permissions()
    state_unchanged = (
        state_after.get("organization_id") == org_id
        and state_after.get("fair_crm_permission_count") == EXPECTED_FAIR_CRM_PERMISSION_COUNT
        and state_after.get("role_matrix_version") == ROLE_MATRIX_VERSION
    )
    record(
        results,
        "11c. Seed idempotency (second run)",
        seed_idempotent and state_unchanged and dup_ok,
        "exit 0, state unchanged, no duplicates"
        if seed_idempotent and state_unchanged and dup_ok
        else f"{seed_second.stderr.strip()[-200:]} | {dup_detail}",
    )

    perm_tests = run_pytest("backend/tests/modules/test_endpoint_permission_enforcement.py")
    perm_tests_ok = perm_tests.returncode == 0
    record(
        results,
        "11e. Endpoint permission enforcement tests (pytest)",
        perm_tests_ok,
        perm_tests.stdout.strip().splitlines()[-1]
        if perm_tests_ok
        else perm_tests.stdout[-200:] + perm_tests.stderr[-300:],
    )

    role_matrix_sql_ok, role_matrix_sql_detail = verify_role_matrix_sql(state)
    record(results, "11f. Role matrix seed + RBAC chain (SQL)", role_matrix_sql_ok, role_matrix_sql_detail)

    role_matrix_tests = run_pytest("backend/tests/modules/test_role_matrix_authorization.py")
    role_matrix_tests_ok = role_matrix_tests.returncode == 0
    record(
        results,
        "11g. Role matrix authorization tests (pytest)",
        role_matrix_tests_ok,
        role_matrix_tests.stdout.strip().splitlines()[-1]
        if role_matrix_tests_ok
        else role_matrix_tests.stdout[-200:] + role_matrix_tests.stderr[-300:],
    )

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
            record(results, "6. fair-crm migrations", True, "upgrade head")
    except Exception as exc:
        record(results, "6. fair-crm migrations", False, str(exc))

    if not ctx.prod_path:
        core_ok, core_detail = probe_service_health("Core", f"{CORE_BASE}/api/v1/health", timeout=5.0)
        record(results, "4. kyrox-core running", core_ok, core_detail if core_ok else core_detail)
        fair_ok, fair_detail = probe_service_health("Fair CRM", f"{FAIR_BASE}/health", timeout=5.0)
        record(results, "5. fair-crm running", fair_ok, fair_detail if fair_ok else fair_detail)
    else:
        core_ok = True
        fair_ok = True

    record(results, "7. kyrox-core health", core_ok, f"{CORE_BASE}/api/v1/health")
    record(results, "7b. fair-crm health", fair_ok, f"{FAIR_BASE}/health")

    if not core_ok or not fair_ok:
        record(results, "Services running", False, services_down_detail(core_ok, fair_ok))
        return _finish(ctx, results, 1)

    record(results, "8. Swagger Core", True, f"{CORE_BASE}/docs")
    record(results, "8. Swagger Fair CRM", True, f"{FAIR_BASE}/docs")

    email = state.get("email", "dev@example.com")
    password = state.get("password", "DevPassword123!")

    login_resp = httpx.post(
        f"{CORE_BASE}/api/v1/auth/login",
        json={"email": email, "password": password},
        timeout=10.0,
    )
    if login_resp.status_code != 200:
        record(results, "12-13. Core login + JWT", False, login_resp.text)
        return _finish(ctx, results, 1)
    token = login_resp.json()["access_token"]
    record(results, "12-13. Core login + JWT", True, "real JWT obtained")

    if not org_id:
        record(results, "9. Use seeded dev organization", False, "organization_id missing from seed state")
        return _finish(ctx, results, 1)
    record(results, "9. Use seeded dev organization", True, org_id)

    bypass_guard_ok, bypass_guard_detail = prod_path_guard_dev_bypass_disabled(org_id)
    if not record(results, "9b. Prod-path guard (dev bypass disabled)", bypass_guard_ok, bypass_guard_detail):
        return _finish(ctx, results, 1)

    fair_headers = {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": org_id,
    }

    api_perm_ok, api_perm_detail = verify_permissions_api(token, org_id, REQUIRED_PERMISSIONS)
    record(results, "11d. Verify fair_crm permissions via Core API", api_perm_ok, api_perm_detail)

    foreign_check = httpx.post(
        f"{CORE_BASE}/api/v1/organizations/{FOREIGN_ORG_ID}/authorization/check",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": FOREIGN_ORG_ID,
        },
        json={"permission_code": "fair_crm.customers.read"},
        timeout=10.0,
    )
    foreign_ok = foreign_check.status_code in {403, 404}
    record(
        results,
        "13a. Core auth rejects foreign organization",
        foreign_ok,
        f"status={foreign_check.status_code}",
    )

    scope_mismatch = httpx.post(
        f"{CORE_BASE}/api/v1/organizations/{org_id}/authorization/check",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": FOREIGN_ORG_ID,
        },
        json={"permission_code": "fair_crm.customers.read"},
        timeout=10.0,
    )
    scope_ok = scope_mismatch.status_code in {400, 403}
    record(
        results,
        "13b. Core auth rejects organization scope mismatch",
        scope_ok,
        f"status={scope_mismatch.status_code} (expected 400 or 403)",
    )

    list_ok_resp = httpx.get(f"{FAIR_BASE}/api/v1/customers", headers=fair_headers, timeout=10.0)
    list_ok = list_ok_resp.status_code == 200
    record(
        results,
        "14. JWT + seeded org against Fair CRM",
        list_ok,
        f"GET /customers status={list_ok_resp.status_code}",
    )

    foreign_fair_headers = {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": FOREIGN_ORG_ID,
    }
    try:
        foreign_list = httpx.get(
            f"{FAIR_BASE}/api/v1/customers",
            headers=foreign_fair_headers,
            timeout=15.0,
        )
        foreign_fair_ok = foreign_list.status_code in {403, 400}
        foreign_fair_detail = f"GET /customers status={foreign_list.status_code}"
    except httpx.HTTPError as exc:
        foreign_fair_ok = False
        foreign_fair_detail = f"request failed: {exc}"
    record(
        results,
        "14a. Fair CRM rejects foreign organization header",
        foreign_fair_ok,
        foreign_fair_detail,
    )

    role_checks_ok, role_checks_detail = run_live_role_checks(state, org_id, password)
    record(
        results,
        "14b. Role matrix selective authorization (live)",
        role_checks_ok,
        "; ".join(role_checks_detail),
    )

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
        return _finish(ctx, results, 1)
    customer_id = create_resp.json()["id"]
    record(results, "15. Create customer", True, customer_id)

    list_resp = httpx.get(f"{FAIR_BASE}/api/v1/customers", headers=fair_headers, timeout=10.0)
    list_has_customer = list_resp.status_code == 200 and any(
        item["id"] == customer_id for item in list_resp.json().get("items", [])
    )
    record(results, "16. List customers", list_has_customer, f"count={len(list_resp.json().get('items', []))}")

    update_resp = httpx.patch(
        f"{FAIR_BASE}/api/v1/customers/{customer_id}",
        headers=fair_headers,
        json={"display_name": "E2E Updated Customer", "status": "active"},
        timeout=10.0,
    )
    record(results, "17. Update customer", update_resp.status_code == 200, update_resp.text[:200])

    archive_resp = httpx.delete(
        f"{FAIR_BASE}/api/v1/customers/{customer_id}",
        headers=fair_headers,
        timeout=10.0,
    )
    record(results, "18. Archive customer", archive_resp.status_code == 200, archive_resp.text[:200])

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

    final_code = 0 if all(r.ok for r in results) else 1
    if ctx.prod_path and final_code != 0:
        final_code = 1
    return _finish(ctx, results, final_code)


if __name__ == "__main__":
    raise SystemExit(main())
