"""Call merge-execute on active DB and print status + body."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

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
from sqlalchemy.orm import sessionmaker

from uuid import UUID

GROUP_EMAIL = "info@3smedikal.com"
ORG_ID = UUID("00000000-0000-4000-8000-000000000010")
USER_ID = UUID("00000000-0000-4000-8000-000000000001")


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with engine.connect() as conn:
        org_exists = conn.execute(
            text("SELECT 1 FROM crm_customers WHERE organization_id = :org LIMIT 1"),
            {"org": str(ORG_ID)},
        ).fetchone()
        print("org_has_customers", bool(org_exists))

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

    token = create_test_token(user_id=USER_ID)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": str(ORG_ID),
        "Origin": "http://localhost:5173",
    }
    client = TestClient(app, raise_server_exceptions=False)

    create = client.post(
        "/api/v1/admin/data-operations/duplicate_customer_analysis/run",
        headers=headers,
        json={"group_by": "email"},
    )
    print("analysis_run_status", create.status_code)
    if create.status_code != 202:
        print(create.text)
        return
    run_id = create.json()["id"]

    for _ in range(60):
        run = client.get(f"/api/v1/admin/data-operations/runs/{run_id}", headers=headers)
        status = run.json().get("status")
        if status == "completed":
            break
        if status == "failed":
            print("analysis_run_failed", run.json().get("error_message"))
            return
        time.sleep(0.5)
    else:
        print("analysis_run_timeout", run.json())
        return
    print("analysis_run_completed")

    encoded = quote(GROUP_EMAIL, safe="")
    detail = client.get(
        f"/api/v1/admin/data-operations/runs/{run_id}/dataset/duplicate-groups/{encoded}",
        headers=headers,
    )
    print("group_detail_status", detail.status_code)
    if detail.status_code != 200:
        print(detail.text[:500])
        return
    customers = detail.json()["customers"]
    print("group_customer_count", len(customers))
    if not customers:
        print("no customers in group")
        return

    survivor_id = customers[0]["customer"]["id"]
    email_ids = [e["id"] for c in customers for e in c["emails"]]
    phone_ids = [p["id"] for c in customers for p in c["phones"]]
    website_ids = [w["id"] for c in customers for w in c["websites"]]

    payload = {
        "run_id": run_id,
        "surviving_customer_id": survivor_id,
        "scalar_selections": {
            "company_name": survivor_id,
            "legal_name": survivor_id,
            "trade_name": survivor_id,
            "city": survivor_id,
            "country": survivor_id,
        },
        "selected_email_ids": email_ids,
        "selected_phone_ids": phone_ids,
        "selected_website_ids": website_ids,
    }

    preview = client.post(
        f"/api/v1/admin/data-operations/duplicate-groups/{encoded}/merge-preview",
        headers=headers,
        json=payload,
    )
    print("preview_status", preview.status_code)
    if preview.status_code == 200:
        print("preview_is_valid", preview.json().get("is_valid"))
        if not preview.json().get("is_valid"):
            print("validation_errors", preview.json().get("validation_errors"))

    execute = client.post(
        f"/api/v1/admin/data-operations/duplicate-groups/{encoded}/merge-execute",
        headers=headers,
        json=payload,
    )
    print("execute_status", execute.status_code)
    try:
        body = execute.json()
        print("execute_body", json.dumps(body, ensure_ascii=False)[:1000])
    except Exception:
        print("execute_raw", execute.text[:1000])
    print("cors", execute.headers.get("access-control-allow-origin"))


if __name__ == "__main__":
    main()
