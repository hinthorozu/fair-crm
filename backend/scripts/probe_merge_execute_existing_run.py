"""Find completed duplicate analysis runs and test merge-execute."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import quote
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_db
from app.integrations.kyrox_core.auth import create_test_token
from app.main import create_app
from app.modules.system_admin.api.dependencies import get_authorization_adapter as get_system_admin_auth
from tests.conftest import AllowAllAuthorization

import app.modules.system_admin.api.dependencies as sad
import app.modules.data_integration.api.dependencies as did
import app.modules.imports.api.dependencies as iid
from app.modules.data_integration.application.import_job_runner import ImportJobRunner
from app.modules.system_admin.application.data_operation_job_runner import DataOperationJobRunner

ORG_ID = UUID("00000000-0000-4000-8000-000000000010")
USER_ID = UUID("00000000-0000-4000-8000-000000000001")
GROUP_EMAIL = "info@3smedikal.com"


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with engine.connect() as conn:
        runs = conn.execute(
            text(
                """
                SELECT id, status, result, error_message
                FROM system_data_operation_runs
                WHERE organization_id = :org
                  AND operation_key = 'duplicate_customer_analysis'
                ORDER BY started_at DESC
                LIMIT 5
                """
            ),
            {"org": str(ORG_ID)},
        ).mappings().all()
        print("recent_runs_count", len(runs))
        for row in runs:
            print(
                "run",
                str(row["id"]),
                row["status"],
                row["result"],
                (row["error_message"] or "")[:120].encode("ascii", "backslashreplace").decode(),
            )

        audit_exists = conn.execute(
            text(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_schema='public'
                  AND table_name='system_duplicate_group_merge_audit_logs'
                """
            )
        ).fetchone()
        print("audit_table_exists", bool(audit_exists))
        print("alembic_version", conn.execute(text("SELECT version_num FROM alembic_version")).scalar())

    app = create_app()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_system_admin_auth] = lambda: AllowAllAuthorization()
    sad._data_operation_job_runner = DataOperationJobRunner(session_factory=SessionLocal)
    shared = ImportJobRunner(session_factory=SessionLocal)
    did._job_runner = shared
    iid._import_job_runner = shared

    headers = {
        "Authorization": f"Bearer {create_test_token(user_id=USER_ID)}",
        "X-Organization-Id": str(ORG_ID),
        "Origin": "http://localhost:5173",
    }
    client = TestClient(app, raise_server_exceptions=False)

    completed_run = next((r for r in runs if r["status"] == "completed"), None)
    if not completed_run:
        print("no_completed_duplicate_run")
        return

    run_id = str(completed_run["id"])
    encoded = quote(GROUP_EMAIL, safe="")
    detail = client.get(
        f"/api/v1/admin/data-operations/runs/{run_id}/dataset/duplicate-groups/{encoded}",
        headers=headers,
    )
    print("group_detail_status", detail.status_code)
    if detail.status_code != 200:
        print("group_detail_body", detail.text[:500])
        return

    customers = detail.json()["customers"]
    print("group_customer_count", len(customers))
    survivor_id = customers[0]["customer"]["id"]
    payload = {
        "run_id": run_id,
        "surviving_customer_id": survivor_id,
        "scalar_selections": {k: survivor_id for k in ["company_name", "legal_name", "trade_name", "city", "country"]},
        "selected_email_ids": [e["id"] for c in customers for e in c["emails"]],
        "selected_phone_ids": [p["id"] for c in customers for p in c["phones"]],
        "selected_website_ids": [w["id"] for c in customers for w in c["websites"]],
    }
    execute = client.post(
        f"/api/v1/admin/data-operations/duplicate-groups/{encoded}/merge-execute",
        headers=headers,
        json=payload,
    )
    print("execute_status", execute.status_code)
    print("execute_body", json.dumps(execute.json(), ensure_ascii=True)[:1200])


if __name__ == "__main__":
    main()
