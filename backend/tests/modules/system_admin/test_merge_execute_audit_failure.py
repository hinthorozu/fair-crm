"""Regression tests for merge execute failure handling."""

from datetime import UTC, datetime
from urllib.parse import quote

from sqlalchemy.exc import ProgrammingError

from app.modules.customers.domain.value_objects import CustomerStatus
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.system_admin.application.duplicate_group_merge_audit import DuplicateGroupMergeAuditRecorder
from tests.modules.system_admin.test_3s_medikal_merge_repro import GROUP_EMAIL, _seed_3s_medikal_group


def test_duplicate_group_merge_execute_rolls_back_when_audit_table_missing(
    client, auth_headers, db_session, organization_id, monkeypatch
):
    seed = _seed_3s_medikal_group(db_session, organization_id)
    survivor_id = seed["survivor_id"]
    loser_id = seed["customer_ids"][1]

    create = client.post(
        "/api/v1/admin/data-operations/duplicate_customer_analysis/run",
        headers=auth_headers,
        json={"group_by": "email"},
    )
    assert create.status_code == 202
    run_id = create.json()["id"]
    encoded_key = quote(GROUP_EMAIL, safe="")

    def _raise_missing_audit_table(self, **kwargs):
        raise ProgrammingError(
            "INSERT INTO system_duplicate_group_merge_audit_logs",
            {},
            Exception('relation "system_duplicate_group_merge_audit_logs" does not exist'),
        )

    monkeypatch.setattr(DuplicateGroupMergeAuditRecorder, "record", _raise_missing_audit_table)

    execute = client.post(
        f"/api/v1/admin/data-operations/duplicate-groups/{encoded_key}/merge-execute",
        headers={**auth_headers, "Origin": "http://localhost:5173"},
        json={
            "run_id": run_id,
            "surviving_customer_id": str(survivor_id),
            "scalar_selections": {
                "company_name": str(survivor_id),
                "legal_name": str(survivor_id),
                "trade_name": str(survivor_id),
                "city": str(survivor_id),
                "country": str(survivor_id),
            },
            "selected_email_ids": [str(eid) for eid in seed["email_ids"]],
            "selected_phone_ids": [str(pid) for pid in seed["phone_ids"]],
            "selected_website_ids": [str(wid) for wid in seed["website_ids"]],
        },
    )
    assert execute.status_code == 503, execute.text
    body = execute.json()
    assert "detail" in body
    assert "audit log table is missing" in body["detail"].lower()
    assert execute.headers.get("access-control-allow-origin") == "http://localhost:5173"

    db_session.expire_all()
    survivor = db_session.get(CustomerModel, survivor_id)
    loser = db_session.get(CustomerModel, loser_id)
    assert survivor is not None
    assert survivor.status == CustomerStatus.ACTIVE.value
    assert loser is not None
    assert loser.status == CustomerStatus.ACTIVE.value
    assert loser.deleted_at is None
