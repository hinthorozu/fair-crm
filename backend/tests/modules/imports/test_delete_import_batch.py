"""Permanent delete for import batches."""

from io import BytesIO
from datetime import UTC, datetime
from uuid import UUID, uuid4

from openpyxl import Workbook

from app.modules.data_integration.domain.entities import ImportJob
from app.modules.data_integration.infrastructure.persistence.models import ImportJobModel
from app.modules.imports.infrastructure.persistence.models import ImportBatchModel, ImportRowModel


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
        json={"name": "Delete Fair", "location": "Istanbul", "start_date": "2026-06-01", "end_date": "2026-06-03"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _upload_batch(client, auth_headers, fair_id: str) -> str:
    content = _xlsx([["Acme Ltd"]], headers=["Firma"])
    upload = client.post(
        "/api/v1/data-integration/imports/upload",
        headers=auth_headers,
        data={"fair_id": fair_id},
        files={"file": ("delete-test.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert upload.status_code == 201
    return upload.json()["batch_id"]


def test_permanent_delete_removes_batch_rows_and_file(db_session, client, auth_headers):
    fair_id = _fair_id(client, auth_headers)
    batch_id = _upload_batch(client, auth_headers, fair_id)
    batch_uuid = UUID(batch_id)

    batch_model = db_session.get(ImportBatchModel, batch_uuid)
    assert batch_model is not None
    assert batch_model.stored_file_content is not None

    client.patch(
        f"/api/v1/data-integration/imports/{batch_id}/column-mapping",
        headers=auth_headers,
        json={
            "has_header_row": True,
            "header_mode": "first_row_header",
            "mappings": {"company_name": {"type": "column_index", "value": 0}},
        },
    ).raise_for_status()
    client.post(
        f"/api/v1/data-integration/imports/{batch_id}/analyze-job",
        headers=auth_headers,
    ).raise_for_status()

    rows_before = db_session.query(ImportRowModel).filter(ImportRowModel.batch_id == batch_uuid).count()
    assert rows_before >= 1

    delete = client.delete(
        f"/api/v1/data-integration/imports/{batch_id}",
        headers=auth_headers,
    )
    assert delete.status_code == 200
    assert delete.json()["deleted"] is True

    db_session.expire_all()
    assert db_session.get(ImportBatchModel, batch_uuid) is None
    assert db_session.query(ImportRowModel).filter(ImportRowModel.batch_id == batch_uuid).count() == 0
    assert db_session.query(ImportJobModel).filter(ImportJobModel.batch_id == batch_uuid).count() == 0

    get_batch = client.get(f"/api/v1/data-integration/imports/{batch_id}", headers=auth_headers)
    assert get_batch.status_code == 404


def test_delete_blocked_when_analyze_job_active(client, auth_headers, db_session, organization_id):
    fair_id = _fair_id(client, auth_headers)
    batch_id = _upload_batch(client, auth_headers, fair_id)
    batch_uuid = UUID(batch_id)

    client.patch(
        f"/api/v1/data-integration/imports/{batch_id}/column-mapping",
        headers=auth_headers,
        json={
            "has_header_row": True,
            "header_mode": "first_row_header",
            "mappings": {"company_name": {"type": "column_index", "value": 0}},
        },
    ).raise_for_status()

    job = ImportJob.create_analyze_job(
        organization_id=organization_id,
        batch_id=batch_uuid,
        progress_total=1,
        now=datetime.now(tz=UTC),
    )
    job.mark_running(now=datetime.now(tz=UTC))
    db_session.add(
        ImportJobModel(
            id=job.id,
            organization_id=job.organization_id,
            batch_id=job.batch_id,
            job_type=job.job_type.value,
            status=job.status.value,
            progress_processed=job.progress_processed,
            progress_total=job.progress_total,
            result_json=job.result_json,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )
    )
    db_session.commit()

    delete = client.delete(
        f"/api/v1/data-integration/imports/{batch_id}",
        headers=auth_headers,
    )
    assert delete.status_code == 409
    assert "devam eden" in delete.json()["detail"].lower()
    assert db_session.get(ImportBatchModel, batch_uuid) is not None


def test_delete_blocked_when_batch_status_applying(client, auth_headers, db_session):
    fair_id = _fair_id(client, auth_headers)
    batch_id = _upload_batch(client, auth_headers, fair_id)
    batch_uuid = UUID(batch_id)

    batch = db_session.get(ImportBatchModel, batch_uuid)
    batch.status = "applying"
    db_session.commit()

    delete = client.delete(
        f"/api/v1/data-integration/imports/{batch_id}",
        headers=auth_headers,
    )
    assert delete.status_code == 409


def test_delete_not_found(client, auth_headers):
    delete = client.delete(
        f"/api/v1/data-integration/imports/{uuid4()}",
        headers=auth_headers,
    )
    assert delete.status_code == 404


def test_delete_allowed_with_stale_queued_apply_job(client, auth_headers, db_session, organization_id):
    """Orphan queued apply jobs (batch no longer applying) must not block delete."""
    fair_id = _fair_id(client, auth_headers)
    batch_id = _upload_batch(client, auth_headers, fair_id)
    batch_uuid = UUID(batch_id)

    now = datetime.now(tz=UTC)
    job = ImportJob.create_apply_job(
        organization_id=organization_id,
        batch_id=batch_uuid,
        progress_total=1,
        now=now,
    )
    db_session.add(
        ImportJobModel(
            id=job.id,
            organization_id=job.organization_id,
            batch_id=job.batch_id,
            job_type=job.job_type.value,
            status=job.status.value,
            progress_processed=job.progress_processed,
            progress_total=job.progress_total,
            result_json=job.result_json,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )
    )
    batch = db_session.get(ImportBatchModel, batch_uuid)
    batch.status = "analyzed"
    db_session.commit()

    delete = client.delete(
        f"/api/v1/data-integration/imports/{batch_id}",
        headers=auth_headers,
    )
    assert delete.status_code == 200
    assert delete.json()["deleted"] is True
