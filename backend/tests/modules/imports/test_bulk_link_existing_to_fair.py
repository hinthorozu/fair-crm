"""Bulk link existing customers to fair — preview and apply."""

from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID, uuid4

from openpyxl import Workbook

from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.value_objects import CustomerSource
from app.modules.imports.domain.services.bulk_link_existing_to_fair import row_in_link_existing_scope
from app.modules.imports.domain.value_objects import ImportRowStatus
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel


def _xlsx(rows: list[list[str]], headers: list[str] | None = None) -> bytes:
    wb = Workbook()
    ws = wb.active
    if headers:
        ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _fair_id(client, auth_headers) -> str:
    res = client.post(
        "/api/v1/fairs",
        headers=auth_headers,
        json={"name": "Link Fair", "location": "Istanbul", "start_date": "2026-06-01", "end_date": "2026-06-03"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _create_customer(db_session, organization_id, *, display_name: str) -> Customer:
    now = datetime.now(tz=UTC)
    customer = Customer.create(
        organization_id=organization_id,
        display_name=display_name,
        tax_number=None,
        country=None,
        city=None,
        address=None,
        description=None,
        source=CustomerSource.EXCEL,
        now=now,
    )
    from app.modules.customers.infrastructure.repositories.customer_repository import SqlAlchemyCustomerRepository

    return SqlAlchemyCustomerRepository(db_session).add(customer)


def _upload_map_analyze(client, auth_headers, fair_id: str, company_name: str) -> str:
    content = _xlsx([[company_name]], headers=["Firma"])
    upload = client.post(
        "/api/v1/data-integration/imports/upload",
        headers=auth_headers,
        data={"fair_id": fair_id},
        files={"file": ("link.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert upload.status_code == 201
    batch_id = upload.json()["batch_id"]
    client.patch(
        f"/api/v1/data-integration/imports/{batch_id}/sheet",
        headers=auth_headers,
        json={"sheet_name": upload.json()["selected_sheet_name"]},
    )
    client.patch(
        f"/api/v1/data-integration/imports/{batch_id}/header-config",
        headers=auth_headers,
        json={"has_header_row": True, "header_mode": "first_row_header", "header_row_index": 0},
    )
    client.patch(
        f"/api/v1/data-integration/imports/{batch_id}/column-mapping",
        headers=auth_headers,
        json={
            "has_header_row": True,
            "header_mode": "first_row_header",
            "header_row_index": 0,
            "mappings": {"company_name": {"type": "column_index", "value": 0}},
        },
    )
    analyze = client.post(
        f"/api/v1/data-integration/imports/{batch_id}/analyze-job",
        headers=auth_headers,
    )
    assert analyze.status_code == 202
    job_id = analyze.json()["job_id"]
    for _ in range(60):
        job = client.get(f"/api/v1/data-integration/jobs/{job_id}", headers=auth_headers)
        if job.json()["status"] == "completed":
            break
    return batch_id


def test_row_in_link_existing_scope_requires_match_and_will_update_status():
    from app.modules.imports.domain.entities import ImportRow

    now = datetime.now(tz=UTC)
    row = ImportRow.create(
        batch_id=uuid4(),
        organization_id=uuid4(),
        row_number=1,
        raw_data_json={},
        normalized_data_json={"company_name": "Acme"},
        status=ImportRowStatus.READY_TO_UPDATE,
        validation_errors_json=None,
        match_customer_id=uuid4(),
        match_confidence=100,
        match_reason="exact",
        now=now,
    )
    assert row_in_link_existing_scope(row)

    row.status = ImportRowStatus.INVALID
    assert not row_in_link_existing_scope(row)


def test_bulk_link_existing_preview_and_apply(client, auth_headers, db_session, organization_id):
    customer = _create_customer(db_session, organization_id, display_name="Existing Link Co")
    fair_id = _fair_id(client, auth_headers)
    batch_id = _upload_map_analyze(client, auth_headers, fair_id, "Existing Link Co")

    rows_resp = client.get(
        f"/api/v1/data-integration/imports/{batch_id}/rows",
        headers=auth_headers,
        params={"filter": "will_update", "page_size": 100},
    )
    assert rows_resp.status_code == 200
    will_update_total = rows_resp.json()["pagination"]["totalItems"]
    assert will_update_total >= 1

    preview = client.post(
        f"/api/v1/data-integration/imports/{batch_id}/bulk-actions/preview",
        headers=auth_headers,
        json={"action_type": "link_all_existing"},
    )
    assert preview.status_code == 200
    body = preview.json()
    assert body["to_process_rows"] >= 1
    assert body["skipped_already_linked_rows"] == 0
    assert "hedef fuara bağlanacak" in body["summary"]

    apply = client.post(
        f"/api/v1/data-integration/imports/{batch_id}/bulk-actions/apply",
        headers=auth_headers,
        json={"action_type": "link_all_existing"},
    )
    assert apply.status_code == 202
    job_id = apply.json()["job_id"]
    for _ in range(60):
        job = client.get(f"/api/v1/data-integration/jobs/{job_id}", headers=auth_headers)
        job_body = job.json()
        if job_body["status"] == "completed":
            break
        if job_body["status"] == "failed":
            raise AssertionError(job_body.get("error_message") or "bulk link job failed")
    assert job.json()["status"] == "completed"
    result = job.json()["result_json"]
    assert result["processed_rows"] >= 1

    pending = client.get(
        f"/api/v1/data-integration/imports/{batch_id}/rows",
        headers=auth_headers,
        params={"filter": "pending", "page_size": 100},
    )
    assert pending.json()["pagination"]["totalItems"] < will_update_total

    participation = (
        db_session.query(CustomerFairParticipationModel)
        .filter(
            CustomerFairParticipationModel.organization_id == organization_id,
            CustomerFairParticipationModel.customer_id == customer.id,
            CustomerFairParticipationModel.fair_id == UUID(fair_id),
        )
        .one_or_none()
    )
    assert participation is not None

    batch_after = client.get(
        f"/api/v1/data-integration/imports/{batch_id}",
        headers=auth_headers,
    )
    assert batch_after.status_code == 200
    assert batch_after.json()["status"] == "completed"

    count = (
        db_session.query(CustomerFairParticipationModel)
        .filter(
            CustomerFairParticipationModel.organization_id == organization_id,
            CustomerFairParticipationModel.customer_id == customer.id,
            CustomerFairParticipationModel.fair_id == UUID(fair_id),
        )
        .count()
    )
    assert count == 1
