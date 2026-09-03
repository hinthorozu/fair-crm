"""Bulk assign import row decisions to selected rows (no CRM writes)."""

from datetime import UTC, datetime
from uuid import UUID

from app.modules.imports.domain.entities import ImportBatch, ImportRow
from app.modules.imports.domain.value_objects import ImportRowStatus, ImportSourceType
from app.modules.imports.infrastructure.repositories.import_repository import (
    SqlAlchemyImportBatchRepository,
    SqlAlchemyImportRowRepository,
)


def _seed_undecided_rows(
    client,
    auth_headers,
    db_session,
    organization_id: UUID,
    company_names: list[str],
) -> tuple[str, list[dict]]:
    now = datetime.now(tz=UTC)
    batch_repo = SqlAlchemyImportBatchRepository(db_session)
    row_repo = SqlAlchemyImportRowRepository(db_session)
    batch = batch_repo.add(
        ImportBatch.create_from_canonical(
            organization_id=organization_id,
            fair_id=None,
            source_type=ImportSourceType.EXCEL,
            file_name="bulk-assign.xlsx",
            total_rows=len(company_names),
            valid_rows=len(company_names),
            invalid_rows=0,
            raw_preview_json={"total_rows": len(company_names)},
            now=now,
        )
    )
    row_repo.add_many(
        [
            ImportRow.create(
                batch_id=batch.id,
                organization_id=organization_id,
                row_number=index,
                raw_data_json={"company_name": company_name},
                normalized_data_json={"company_name": company_name},
                status=ImportRowStatus.READY_TO_CREATE,
                validation_errors_json=None,
                match_customer_id=None,
                match_confidence=None,
                match_reason="no_match",
                now=now,
            )
            for index, company_name in enumerate(company_names, start=1)
        ]
    )
    db_session.flush()
    listed = client.get(
        f"/api/v1/data-integration/imports/{batch.id}/rows",
        headers=auth_headers,
    )
    assert listed.status_code == 200
    return str(batch.id), listed.json()["items"]


def test_bulk_assign_decisions_updates_selected_rows_only(
    client,
    auth_headers,
    db_session,
    organization_id,
):
    batch_id, rows = _seed_undecided_rows(
        client,
        auth_headers,
        db_session,
        organization_id,
        ["Alpha Co", "Beta Co", "Gamma Co"],
    )
    selected = [rows[0]["id"], rows[1]["id"]]

    response = client.patch(
        f"/api/v1/data-integration/imports/{batch_id}/rows/bulk-decision",
        headers=auth_headers,
        json={"row_ids": selected, "decision": "create_new"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["updated_count"] == 2
    assert body["skipped_count"] == 0

    refreshed = client.get(
        f"/api/v1/data-integration/imports/{batch_id}/rows",
        headers=auth_headers,
    ).json()["items"]
    by_id = {row["id"]: row for row in refreshed}
    assert by_id[rows[0]["id"]]["decision"] == "create_new"
    assert by_id[rows[1]["id"]]["decision"] == "create_new"
    assert by_id[rows[2]["id"]]["decision"] is None

    customers = client.get("/api/v1/customers?search=Alpha", headers=auth_headers).json()["items"]
    assert len(customers) == 0


def test_bulk_assign_update_existing_without_match_is_skipped(
    client,
    auth_headers,
    db_session,
    organization_id,
):
    batch_id, rows = _seed_undecided_rows(
        client,
        auth_headers,
        db_session,
        organization_id,
        ["No Match Co"],
    )

    response = client.patch(
        f"/api/v1/data-integration/imports/{batch_id}/rows/bulk-decision",
        headers=auth_headers,
        json={"row_ids": [rows[0]["id"]], "decision": "update_existing"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["updated_count"] == 0
    assert body["skipped_count"] == 1
    assert len(body["errors"]) == 1

    row = client.get(
        f"/api/v1/data-integration/imports/{batch_id}/rows",
        headers=auth_headers,
    ).json()["items"][0]
    assert row["decision"] is None


def test_bulk_assign_does_not_require_row_ids_and_decision_together(
    client,
    auth_headers,
    db_session,
    organization_id,
):
    batch_id, _ = _seed_undecided_rows(
        client,
        auth_headers,
        db_session,
        organization_id,
        ["Only Co"],
    )

    response = client.patch(
        f"/api/v1/data-integration/imports/{batch_id}/rows/bulk-decision",
        headers=auth_headers,
        json={"row_ids": [], "decision": "skip"},
    )
    assert response.status_code == 422
