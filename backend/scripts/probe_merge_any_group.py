"""Find duplicate groups and test merge-execute on active DB."""

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


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with engine.connect() as conn:
        groups = conn.execute(
            text(
                """
                SELECT r.id AS run_id, d.duplicate_group_key, count(*) AS members
                FROM system_data_operation_runs r
                JOIN system_data_operation_dataset_rows d ON d.run_id = r.id
                WHERE r.organization_id = :org
                  AND r.operation_key = 'duplicate_customer_analysis'
                  AND r.status = 'completed'
                  AND d.duplicate_group_key ILIKE '%3smedikal%'
                GROUP BY r.id, d.duplicate_group_key
                ORDER BY members DESC
                LIMIT 5
                """
            ),
            {"org": str(ORG_ID)},
        ).mappings().all()
        for g in groups:
            print("group", str(g["run_id"]), g["duplicate_group_key"], g["members"])

        if not groups:
            groups = conn.execute(
                text(
                    """
                    SELECT r.id AS run_id, d.duplicate_group_key, count(*) AS members
                    FROM system_data_operation_runs r
                    JOIN system_data_operation_dataset_rows d ON d.run_id = r.id
                    WHERE r.organization_id = :org
                      AND r.operation_key = 'duplicate_customer_analysis'
                      AND r.status = 'completed'
                      AND d.duplicate_group_key IS NOT NULL
                    GROUP BY r.id, d.duplicate_group_key
                    HAVING count(*) > 1
                    ORDER BY members DESC
                    LIMIT 3
                    """
                ),
                {"org": str(ORG_ID)},
            ).mappings().all()
            print("fallback_groups")
            for g in groups:
                print("group", str(g["run_id"]), g["duplicate_group_key"], g["members"])

    if not groups:
        print("no_duplicate_groups_found")
        return

    target = groups[0]
    run_id = str(target["run_id"])
    group_key = target["duplicate_group_key"]

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
    encoded = quote(group_key, safe="")
    detail = client.get(
        f"/api/v1/admin/data-operations/runs/{run_id}/dataset/duplicate-groups/{encoded}",
        headers=headers,
    )
    print("group_detail_status", detail.status_code)
    if detail.status_code != 200:
        print("group_detail_body", detail.text[:500])
        return

    customers = detail.json()["customers"]
    survivor_id = customers[0]["id"]
    payload = {
        "run_id": run_id,
        "surviving_customer_id": survivor_id,
        "scalar_selections": {k: survivor_id for k in ["company_name", "legal_name", "trade_name", "city", "country"]},
        "selected_email_ids": [e["id"] for c in customers for e in c.get("emails", [])],
        "selected_phone_ids": [p["id"] for c in customers for p in c.get("phones", [])],
        "selected_website_ids": [w["id"] for c in customers for w in c.get("websites", [])],
    }
    execute = client.post(
        f"/api/v1/admin/data-operations/duplicate-groups/{encoded}/merge-execute",
        headers=headers,
        json=payload,
    )
    print("execute_status", execute.status_code)
    print("execute_body", json.dumps(execute.json(), ensure_ascii=True)[:1500])


if __name__ == "__main__":
    main()
