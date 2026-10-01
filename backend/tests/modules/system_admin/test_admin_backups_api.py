"""Admin database backup API tests (Sprint 09.2.2 / 09.2.4)."""

import zipfile
from pathlib import Path

import pytest

from app.shared.database_backup.engine import BackupRunResult
from app.shared.database_backup.post_restore_health import PostRestoreHealthResult


def _batch_items(body: dict) -> list[dict]:
    return body["items"]


def _first_item(body: dict) -> dict:
    items = _batch_items(body)
    assert items, "Expected at least one backup item"
    return items[0]


def _success_post_restore_health(**kwargs) -> PostRestoreHealthResult:
    database_key = kwargs.get("database_key", "fair_crm")
    if database_key == "kyrox_core":
        return PostRestoreHealthResult(
            ok=True,
            migration_result=kwargs.get("migration_result", "success"),
            database_key="kyrox_core",
            users_count=5,
            organizations_count=2,
            roles_count=3,
            permissions_count=10,
            user_roles_count=7,
        )
    if database_key == "fair_stand":
        return PostRestoreHealthResult(
            ok=True,
            migration_result=kwargs.get("migration_result", "success"),
            database_key="fair_stand",
            categories_count=6,
            preview_kinds_count=28,
            items_count=96,
        )
    return PostRestoreHealthResult(
        ok=True,
        migration_result=kwargs.get("migration_result", "success"),
        database_key="fair_crm",
        customers_count=12,
        fairs_count=4,
        contacts_count=7,
    )


def _failed_post_restore_health(**kwargs) -> PostRestoreHealthResult:
    database_key = kwargs.get("database_key", "fair_crm")
    if database_key == "kyrox_core":
        return PostRestoreHealthResult(
            ok=False,
            migration_result="success",
            database_key="kyrox_core",
            error_message="Missing critical tables: identity_roles",
        )
    return PostRestoreHealthResult(
        ok=False,
        migration_result="success",
        database_key="fair_crm",
        error_message="Missing critical tables: crm_fairs",
    )


def _fake_pg_dump(*, database_url: str, output_path: Path, on_stage=None) -> BackupRunResult:
    _ = database_url
    if on_stage:
        on_stage("preparing")
        on_stage("dumping")
        on_stage("compressing")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = b"PGDMP" + b"\x00" * 20 + b"FAIRCRM_TEST_BACKUP"
    output_path.write_bytes(payload)
    return BackupRunResult(
        path=output_path,
        size_bytes=len(payload),
        checksum_sha256="deadbeef" * 8,
        toc_entry_count=1,
        toolchain="test",
    )


def _fake_pg_dump_plain(*, database_url: str, output_path: Path, on_stage=None) -> BackupRunResult:
    _ = database_url
    if on_stage:
        on_stage("preparing")
        on_stage("dumping")
        on_stage("compressing")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sql = "-- PostgreSQL database dump\nCREATE TABLE demo (id uuid PRIMARY KEY);\n"
    output_path.write_text(sql, encoding="utf-8")
    return BackupRunResult(
        path=output_path,
        size_bytes=len(sql.encode()),
        checksum_sha256="cafebabe" * 8,
        toc_entry_count=2,
        toolchain="test",
    )


def _fake_build_package(self, *, session, organization_id, output_path, on_stage=None):
    _ = (self, session, organization_id)
    if on_stage:
        on_stage("preparing")
        on_stage("dumping")
        on_stage("compressing")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"app": "fair-crm", "entity_counts": {"customers": 0}}
    with zipfile.ZipFile(output_path, "w") as archive:
        archive.writestr("manifest.json", '{"app":"fair-crm"}')
        archive.writestr("customers.json", "[]")
    size = output_path.stat().st_size
    return (
        BackupRunResult(
            path=output_path,
            size_bytes=size,
            checksum_sha256="feedface" * 8,
            toc_entry_count=2,
            toolchain="test-zip",
        ),
        manifest,
    )


@pytest.fixture
def backups_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    (root / "backups").mkdir(parents=True)
    (root / "data" / "restore_uploads").mkdir(parents=True)
    (root / "data" / "restore_logs").mkdir(parents=True)
    monkeypatch.setattr("app.shared.database_backup.paths.get_repo_root", lambda: root)
    monkeypatch.setattr("app.modules.system_admin.application.backup_service.get_restore_uploads_dir", lambda repo_root=None: root / "data" / "restore_uploads")
    monkeypatch.setattr("app.modules.system_admin.application.backup_service.relative_repo_path", lambda path: str(path.resolve().relative_to(root.resolve())).replace("\\", "/"))
    monkeypatch.setattr("app.shared.database_backup.paths.get_restore_uploads_dir", lambda repo_root=None: root / "data" / "restore_uploads")
    monkeypatch.setattr("app.shared.database_backup.paths.get_restore_logs_dir", lambda repo_root=None: root / "data" / "restore_logs")
    monkeypatch.setattr("app.modules.system_admin.application.restore_job_service.get_repo_root", lambda: root)
    monkeypatch.setattr("app.modules.system_admin.application.restore_job_service.get_restore_logs_dir", lambda repo_root=None: root / "data" / "restore_logs")
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.relative_repo_path",
        lambda path: str(path.resolve().relative_to(root.resolve())).replace("\\", "/"),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_job_runner.pg_dump_custom",
        _fake_pg_dump,
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_job_runner.pg_dump_plain",
        _fake_pg_dump_plain,
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_job_runner.UniversalDataPackageService.build_package",
        _fake_build_package,
    )
    return root


def test_create_list_and_get_backup(client, auth_headers, backups_root):
    create = client.post(
        "/api/v1/admin/backups",
        headers=auth_headers,
        json={"notes": "Sprint 09.2.2 test backup"},
    )
    assert create.status_code == 202
    body = create.json()
    item = _first_item(body)
    backup_id = item["id"]
    assert item["status"] in {"running", "completed"}
    assert item["backup_format"] == "postgresql_dump"
    assert item["database_key"] == "fair_crm"
    assert item["database_label"] == "FAIR CRM"
    assert item["file_name"].startswith("fair_crm_backup_")
    assert item["file_name"].endswith(".dump")

    detail = client.get(f"/api/v1/admin/backups/{backup_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "completed"
    assert detail.json()["backup_format"] == "postgresql_dump"
    assert detail.json()["database_key"] == "fair_crm"
    assert detail.json()["database_label"] == "FAIR CRM"
    assert detail.json()["notes"] == "Sprint 09.2.2 test backup"
    assert detail.json()["file_size"] == len(b"PGDMP" + b"\x00" * 20 + b"FAIRCRM_TEST_BACKUP")

    listing = client.get("/api/v1/admin/backups", headers=auth_headers)
    assert listing.status_code == 200
    data = listing.json()
    assert data["pagination"]["totalItems"] >= 1
    assert any(item["id"] == backup_id for item in data["items"])


def test_create_sql_backup(client, auth_headers, backups_root):
    create = client.post(
        "/api/v1/admin/backups",
        headers=auth_headers,
        json={"backup_format": "postgresql_sql"},
    )
    assert create.status_code == 202
    body = create.json()
    item = _first_item(body)
    assert item["backup_format"] == "postgresql_sql"
    assert item["file_name"].endswith(".sql")

    detail = client.get(f"/api/v1/admin/backups/{item['id']}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "completed"
    assert "PostgreSQL database dump" in (backups_root / "backups" / item["file_name"]).read_text(encoding="utf-8")


def test_create_universal_data_package(client, auth_headers, backups_root):
    create = client.post(
        "/api/v1/admin/backups",
        headers=auth_headers,
        json={"backup_format": "universal_data_package"},
    )
    assert create.status_code == 202
    body = create.json()
    item = _first_item(body)
    assert item["backup_format"] == "universal_data_package"
    assert item["file_name"].startswith("fair_crm_data_package_")
    assert item["file_name"].endswith(".zip")

    detail = client.get(f"/api/v1/admin/backups/{item['id']}", headers=auth_headers)
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["status"] == "completed"
    assert payload["manifest_json"]["app"] == "fair-crm"

    zip_path = backups_root / "backups" / item["file_name"]
    with zipfile.ZipFile(zip_path) as archive:
        assert "manifest.json" in archive.namelist()


def test_download_backup_increments_count(client, auth_headers, backups_root):
    create = client.post("/api/v1/admin/backups", headers=auth_headers, json={"notes": None})
    assert create.status_code == 202
    item = _first_item(create.json())
    backup_id = item["id"]
    file_name = item["file_name"]

    download = client.get(f"/api/v1/admin/backups/{backup_id}/download", headers=auth_headers)
    assert download.status_code == 200
    assert download.content.startswith(b"PGDMP")
    assert download.headers.get("content-disposition", "").find(file_name) >= 0

    detail = client.get(f"/api/v1/admin/backups/{backup_id}", headers=auth_headers)
    assert detail.json()["download_count"] == 1


def test_restore_completed_backup(client, auth_headers, backups_root, monkeypatch):
    from app.shared.database_backup.engine import BackupVerificationResult

    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_service.verify_backup_dump",
        lambda **kwargs: BackupVerificationResult(path=kwargs["dump_path"], size_bytes=32, toc_entry_count=1),
    )

    create = client.post("/api/v1/admin/backups", headers=auth_headers, json={})
    backup_id = _first_item(create.json())["id"]

    restore = client.post(f"/api/v1/admin/backups/{backup_id}/restore", headers=auth_headers)
    assert restore.status_code == 202
    body = restore.json()
    assert body["status"] == "manual_restore_required"
    assert body["backup_id"] == backup_id
    assert body["uploaded"] is False
    assert body["source_type"] == "existing_backup"
    assert body["source_database_key"] == "fair_crm"
    assert body["target_database_key"] == "fair_crm"

    jobs = client.get("/api/v1/admin/backups/restore-jobs", headers=auth_headers)
    assert jobs.status_code == 200
    assert jobs.json()["pagination"]["totalItems"] >= 1
    assert any(item["id"] == body["id"] for item in jobs.json()["items"])

    detail = client.get(f"/api/v1/admin/backups/restore-jobs/{body['id']}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "manual_restore_required"
    assert detail.json()["source_file_name"]


def test_restore_job_log_endpoint_returns_queued_log(client, auth_headers, backups_root, monkeypatch):
    from app.shared.database_backup.engine import BackupVerificationResult

    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_service.verify_backup_dump",
        lambda **kwargs: BackupVerificationResult(path=kwargs["dump_path"], size_bytes=32, toc_entry_count=1),
    )

    create = client.post("/api/v1/admin/backups", headers=auth_headers, json={})
    backup_id = _first_item(create.json())["id"]
    restore = client.post(f"/api/v1/admin/backups/{backup_id}/restore", headers=auth_headers)
    job_id = restore.json()["id"]
    assert restore.json()["restore_log_path"]

    log = client.get(f"/api/v1/admin/backups/restore-jobs/{job_id}/log", headers=auth_headers)
    assert log.status_code == 200
    payload = log.json()
    assert payload["job_id"] == job_id
    assert payload["status"] == "manual_restore_required"
    assert payload["exists"] is True
    assert "[restore job queued]" in payload["content"]
    assert "source db: fair_crm" in payload["content"]


def test_restore_job_log_endpoint_not_found(client, auth_headers):
    log = client.get(
        "/api/v1/admin/backups/restore-jobs/00000000-0000-4000-8000-000000000099/log",
        headers=auth_headers,
    )
    assert log.status_code == 404


def test_restore_job_log_endpoint_after_runner(client, auth_headers, backups_root, monkeypatch, db_session):
    from uuid import UUID

    from app.shared.database_backup.engine import BackupVerificationResult
    from app.modules.system_admin.application.restore_job_service import (
        RestoreJobMaintenanceCommand,
        RestoreJobMaintenanceRunner,
    )

    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_service.verify_backup_dump",
        lambda **kwargs: BackupVerificationResult(path=kwargs["dump_path"], size_bytes=32, toc_entry_count=1),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.verify_backup_dump",
        lambda **kwargs: BackupVerificationResult(path=kwargs["dump_path"], size_bytes=32, toc_entry_count=1),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.pg_restore_custom",
        lambda **kwargs: None,
    )
    monkeypatch.setattr("app.modules.system_admin.application.restore_job_service.get_repo_root", lambda: backups_root)
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.subprocess.run",
        lambda *args, **kwargs: type("Proc", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.run_post_restore_health_check",
        _success_post_restore_health,
    )

    create = client.post("/api/v1/admin/backups", headers=auth_headers, json={})
    backup_id = _first_item(create.json())["id"]
    restore = client.post(f"/api/v1/admin/backups/{backup_id}/restore", headers=auth_headers)
    job_id = UUID(restore.json()["id"])

    runner = RestoreJobMaintenanceRunner(session_factory=lambda: db_session)
    assert (
        runner.run(
            RestoreJobMaintenanceCommand(
                job_id=job_id,
                target_database_url="postgresql://postgres:postgres@localhost:5432/fair_crm",
                allow_restore=True,
            )
        )
        == 0
    )

    log = client.get(f"/api/v1/admin/backups/restore-jobs/{str(job_id)}/log", headers=auth_headers)
    assert log.status_code == 200
    payload = log.json()
    assert payload["exists"] is True
    assert payload["status"] == "completed"
    assert "pg_restore completed" in payload["content"]
    assert "completed" in payload["content"]


def test_restore_rejects_non_dump_format(client, auth_headers, backups_root):
    create = client.post(
        "/api/v1/admin/backups",
        headers=auth_headers,
        json={"backup_format": "postgresql_sql"},
    )
    backup_id = _first_item(create.json())["id"]

    restore = client.post(f"/api/v1/admin/backups/{backup_id}/restore", headers=auth_headers)
    assert restore.status_code == 400
    assert "dump" in restore.json()["detail"].lower()


def test_restore_from_upload_accepts_custom_dump(client, auth_headers, backups_root, monkeypatch):
    from app.shared.database_backup.engine import BackupVerificationResult

    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_service.verify_backup_dump",
        lambda **kwargs: BackupVerificationResult(path=kwargs["dump_path"], size_bytes=32, toc_entry_count=1),
    )

    payload = b"PGDMP" + b"\x00" * 20 + b"uploaded"
    files = {"file": ("restore.dump", payload, "application/octet-stream")}
    restore = client.post(
        "/api/v1/admin/backups/restore/upload",
        headers=auth_headers,
        files=files,
        data={"notes": "manual upload"},
    )
    assert restore.status_code == 202, restore.text
    body = restore.json()
    assert body["status"] == "manual_restore_required"
    assert body["uploaded"] is True
    assert body["source_file_name"].endswith(".dump")
    assert body["source_type"] == "uploaded_file"
    assert body["source_database_key"] == "fair_crm"
    assert body["target_database_key"] == "fair_crm"
    assert body["checksum_sha256"]


def test_delete_uploaded_restore_job_removes_uploaded_file_and_log(client, auth_headers, backups_root, monkeypatch):
    from app.shared.database_backup.engine import BackupVerificationResult

    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_service.verify_backup_dump",
        lambda **kwargs: BackupVerificationResult(path=kwargs["dump_path"], size_bytes=32, toc_entry_count=1),
    )

    files = {"file": ("restore.dump", b"PGDMP" + b"\x00" * 20 + b"uploaded", "application/octet-stream")}
    restore = client.post("/api/v1/admin/backups/restore/upload", headers=auth_headers, files=files)
    assert restore.status_code == 202
    job = restore.json()
    uploaded_files = list((backups_root / "data" / "restore_uploads").iterdir())
    assert len(uploaded_files) == 1
    log_path = backups_root / job["restore_log_path"]
    log_path.write_text("queued", encoding="utf-8")

    deleted = client.delete(f"/api/v1/admin/backups/restore-jobs/{job['id']}", headers=auth_headers)
    assert deleted.status_code == 200
    assert deleted.json() == {"id": job["id"], "file_deleted": True, "log_deleted": True}
    assert not uploaded_files[0].exists()
    assert not log_path.exists()
    assert client.get(f"/api/v1/admin/backups/restore-jobs/{job['id']}", headers=auth_headers).status_code == 404


def test_delete_existing_backup_restore_job_preserves_backup_file(client, auth_headers, backups_root, monkeypatch):
    from app.shared.database_backup.engine import BackupVerificationResult

    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_service.verify_backup_dump",
        lambda **kwargs: BackupVerificationResult(path=kwargs["dump_path"], size_bytes=32, toc_entry_count=1),
    )
    create = client.post("/api/v1/admin/backups", headers=auth_headers, json={})
    backup = _first_item(create.json())
    backup_path = backups_root / "backups" / backup["file_name"]
    assert backup_path.exists()
    restore = client.post(f"/api/v1/admin/backups/{backup['id']}/restore", headers=auth_headers)
    assert restore.status_code == 202

    deleted = client.delete(
        f"/api/v1/admin/backups/restore-jobs/{restore.json()['id']}",
        headers=auth_headers,
    )
    assert deleted.status_code == 200
    assert deleted.json()["file_deleted"] is False
    assert backup_path.exists()


def test_restore_from_upload_rejects_non_dump(client, auth_headers, backups_root):
    files = {"file": ("restore.sql", b"SELECT 1;", "application/sql")}
    restore = client.post(
        "/api/v1/admin/backups/restore/upload",
        headers=auth_headers,
        files=files,
    )
    assert restore.status_code == 400


def test_restore_from_upload_rejects_wrong_database_key(client, auth_headers, backups_root, monkeypatch):
    from app.shared.database_backup.engine import BackupVerificationResult

    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_service.verify_backup_dump",
        lambda **kwargs: BackupVerificationResult(path=kwargs["dump_path"], size_bytes=32, toc_entry_count=1),
    )

    payload = b"PGDMP" + b"\x00" * 20 + b"uploaded"
    files = {"file": ("kyrox_core_backup_test.dump", payload, "application/octet-stream")}
    restore = client.post(
        "/api/v1/admin/backups/restore/upload",
        headers=auth_headers,
        files=files,
        data={"database_key": "fair_crm"},
    )
    assert restore.status_code == 400
    assert "kyrox_core" in restore.json()["detail"].lower()


def test_delete_backup(client, auth_headers, backups_root):
    create = client.post("/api/v1/admin/backups", headers=auth_headers, json={"notes": "to delete"})
    assert create.status_code == 202
    item = _first_item(create.json())
    backup_id = item["id"]
    file_name = item["file_name"]
    assert (backups_root / "backups" / file_name).exists()

    delete = client.delete(f"/api/v1/admin/backups/{backup_id}", headers=auth_headers)
    assert delete.status_code == 200
    assert delete.json()["id"] == backup_id
    assert delete.json()["file_name"] == file_name
    assert not (backups_root / "backups" / file_name).exists()

    detail = client.get(f"/api/v1/admin/backups/{backup_id}", headers=auth_headers)
    assert detail.status_code == 404


def test_list_restore_jobs_empty(client, auth_headers, backups_root):
    response = client.get(
        "/api/v1/admin/backups/restore-jobs?page=1&pageSize=20&sort_by=requested_at&sort_order=desc",
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["items"] == []
    assert body["pagination"]["totalItems"] == 0
    assert body["sorting"]["field"] == "requested_at"
    assert body["sorting"]["direction"] == "desc"


def test_restore_job_detail_not_found(client, auth_headers, backups_root):
    missing = client.get(
        "/api/v1/admin/backups/restore-jobs/00000000-0000-4000-8000-000000000099",
        headers=auth_headers,
    )
    assert missing.status_code == 404


def test_restore_job_maintenance_runner_completes_job(client, auth_headers, backups_root, monkeypatch, db_session):
    from uuid import UUID

    from app.shared.database_backup.engine import BackupVerificationResult
    from app.modules.system_admin.application.restore_job_service import (
        RestoreJobMaintenanceCommand,
        RestoreJobMaintenanceRunner,
    )

    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_service.verify_backup_dump",
        lambda **kwargs: BackupVerificationResult(path=kwargs["dump_path"], size_bytes=32, toc_entry_count=1),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.verify_backup_dump",
        lambda **kwargs: BackupVerificationResult(path=kwargs["dump_path"], size_bytes=32, toc_entry_count=1),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.pg_restore_custom",
        lambda **kwargs: None,
    )
    monkeypatch.setattr("app.modules.system_admin.application.restore_job_service.get_repo_root", lambda: backups_root)
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.subprocess.run",
        lambda *args, **kwargs: type("Proc", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.run_post_restore_health_check",
        _success_post_restore_health,
    )

    create = client.post("/api/v1/admin/backups", headers=auth_headers, json={})
    backup_id = _first_item(create.json())["id"]
    restore = client.post(f"/api/v1/admin/backups/{backup_id}/restore", headers=auth_headers)
    job_id = UUID(restore.json()["id"])

    runner = RestoreJobMaintenanceRunner(session_factory=lambda: db_session)
    exit_code = runner.run(
        RestoreJobMaintenanceCommand(
            job_id=job_id,
            target_database_url="postgresql://postgres:postgres@localhost:5432/fair_crm",
            allow_restore=True,
        )
    )
    assert exit_code == 0

    detail = client.get(f"/api/v1/admin/backups/restore-jobs/{str(job_id)}", headers=auth_headers)
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["status"] == "completed"
    assert payload["restore_log_path"]
    assert payload["completed_at"]
    assert "customers: 12" in (payload["notes"] or "")

    log_path = backups_root / payload["restore_log_path"]
    assert log_path.exists()
    log_text = log_path.read_text(encoding="utf-8")
    assert "Post-restore health check passed" in log_text
    assert "customers count: 12" in log_text


def test_restore_job_health_check_failure_marks_failed(client, auth_headers, backups_root, monkeypatch, db_session):
    from uuid import UUID

    from app.shared.database_backup.engine import BackupVerificationResult
    from app.modules.system_admin.application.restore_job_service import (
        RestoreJobMaintenanceCommand,
        RestoreJobMaintenanceRunner,
    )

    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_service.verify_backup_dump",
        lambda **kwargs: BackupVerificationResult(path=kwargs["dump_path"], size_bytes=32, toc_entry_count=1),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.verify_backup_dump",
        lambda **kwargs: BackupVerificationResult(path=kwargs["dump_path"], size_bytes=32, toc_entry_count=1),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.pg_restore_custom",
        lambda **kwargs: None,
    )
    monkeypatch.setattr("app.modules.system_admin.application.restore_job_service.get_repo_root", lambda: backups_root)
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.subprocess.run",
        lambda *args, **kwargs: type("Proc", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.run_post_restore_health_check",
        _failed_post_restore_health,
    )

    create = client.post("/api/v1/admin/backups", headers=auth_headers, json={})
    backup_id = _first_item(create.json())["id"]
    restore = client.post(f"/api/v1/admin/backups/{backup_id}/restore", headers=auth_headers)
    job_id = UUID(restore.json()["id"])

    runner = RestoreJobMaintenanceRunner(session_factory=lambda: db_session)
    exit_code = runner.run(
        RestoreJobMaintenanceCommand(
            job_id=job_id,
            target_database_url="postgresql://postgres:postgres@localhost:5432/fair_crm",
            allow_restore=True,
        )
    )
    assert exit_code == 1

    detail = client.get(f"/api/v1/admin/backups/restore-jobs/{str(job_id)}", headers=auth_headers)
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["status"] == "failed"
    assert payload["restore_log_path"]
    assert "crm_fairs" in (payload["error_message"] or "")

    log_path = backups_root / payload["restore_log_path"]
    assert log_path.exists()
    log_text = log_path.read_text(encoding="utf-8")
    assert "Post-restore health check FAILED" in log_text


def test_backup_forbidden_without_permission(client, auth_headers, backups_root):
    from app.modules.system_admin.api.dependencies import get_authorization_adapter
    from tests.conftest import AllowAllAuthorization, DenyAllAuthorization

    app = client.app
    app.dependency_overrides[get_authorization_adapter] = lambda: DenyAllAuthorization()
    try:
        res = client.post("/api/v1/admin/backups", headers=auth_headers, json={})
        assert res.status_code == 403
    finally:
        app.dependency_overrides[get_authorization_adapter] = lambda: AllowAllAuthorization()


def test_create_multi_database_backup(client, auth_headers, backups_root):
    create = client.post(
        "/api/v1/admin/backups",
        headers=auth_headers,
        json={"database_keys": ["kyrox_core", "fair_crm"], "notes": "multi-db"},
    )
    assert create.status_code == 202
    items = _batch_items(create.json())
    assert len(items) == 2
    keys = {item["database_key"] for item in items}
    assert keys == {"kyrox_core", "fair_crm"}
    for item in items:
        assert item["file_name"].startswith(f"{item['database_key']}_backup_")
        detail = client.get(f"/api/v1/admin/backups/{item['id']}", headers=auth_headers)
        assert detail.status_code == 200
        assert detail.json()["status"] == "completed"
        assert detail.json()["notes"] == "multi-db"


def test_create_kyrox_core_rejects_universal_package(client, auth_headers, backups_root):
    create = client.post(
        "/api/v1/admin/backups",
        headers=auth_headers,
        json={"database_keys": ["kyrox_core"], "backup_format": "universal_data_package"},
    )
    assert create.status_code == 400
    assert "fair_crm" in create.json()["detail"].lower()


def test_restore_kyrox_core_backup(client, auth_headers, backups_root, monkeypatch):
    from app.shared.database_backup.engine import BackupVerificationResult

    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_service.verify_backup_dump",
        lambda **kwargs: BackupVerificationResult(path=kwargs["dump_path"], size_bytes=32, toc_entry_count=1),
    )

    create = client.post(
        "/api/v1/admin/backups",
        headers=auth_headers,
        json={"database_keys": ["kyrox_core"]},
    )
    assert create.status_code == 202
    backup_id = _first_item(create.json())["id"]

    restore = client.post(f"/api/v1/admin/backups/{backup_id}/restore", headers=auth_headers)
    assert restore.status_code == 202
    body = restore.json()
    assert body["source_database_key"] == "kyrox_core"
    assert body["target_database_key"] == "kyrox_core"


def test_create_fair_stand_rejects_universal_package(client, auth_headers, backups_root):
    create = client.post(
        "/api/v1/admin/backups",
        headers=auth_headers,
        json={"database_keys": ["fair_stand"], "backup_format": "universal_data_package"},
    )
    assert create.status_code == 400
    assert "fair_crm" in create.json()["detail"].lower()


def test_create_and_restore_fair_stand_backup(client, auth_headers, backups_root, monkeypatch):
    from app.shared.database_backup.engine import BackupVerificationResult

    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_service.verify_backup_dump",
        lambda **kwargs: BackupVerificationResult(path=kwargs["dump_path"], size_bytes=32, toc_entry_count=1),
    )

    create = client.post(
        "/api/v1/admin/backups",
        headers=auth_headers,
        json={"database_keys": ["fair_stand"]},
    )
    assert create.status_code == 202
    item = _first_item(create.json())
    assert item["database_key"] == "fair_stand"
    assert item["file_name"].startswith("fair_stand_backup_")

    restore = client.post(f"/api/v1/admin/backups/{item['id']}/restore", headers=auth_headers)
    assert restore.status_code == 202
    body = restore.json()
    assert body["source_database_key"] == "fair_stand"
    assert body["target_database_key"] == "fair_stand"


def test_create_multi_database_backup_includes_fair_stand(client, auth_headers, backups_root):
    create = client.post(
        "/api/v1/admin/backups",
        headers=auth_headers,
        json={"database_keys": ["kyrox_core", "fair_crm", "fair_stand"], "notes": "trio"},
    )
    assert create.status_code == 202
    items = _batch_items(create.json())
    assert {item["database_key"] for item in items} == {"kyrox_core", "fair_crm", "fair_stand"}


def test_resolve_restore_job_log_path_rejects_traversal(backups_root):
    from datetime import UTC, datetime
    from uuid import uuid4

    from app.modules.system_admin.application.restore_job_service import resolve_restore_job_log_path
    from app.modules.system_admin.domain.entities import SystemBackupRestoreJob
    from app.modules.system_admin.domain.value_objects import RestoreJobSourceType, RestoreJobStatus
    from app.shared.database_backup.database_keys import DatabaseKey

    now = datetime.now(tz=UTC)
    job = SystemBackupRestoreJob(
        id=uuid4(),
        organization_id=uuid4(),
        source_type=RestoreJobSourceType.EXISTING_BACKUP,
        source_database_key=DatabaseKey.FAIR_CRM,
        target_database_key=DatabaseKey.FAIR_CRM,
        backup_id=uuid4(),
        uploaded_file_path=None,
        source_file_name="faircrm_backup_test.dump",
        checksum_sha256=None,
        status=RestoreJobStatus.MANUAL_RESTORE_REQUIRED,
        notes=None,
        requested_by_user_id=uuid4(),
        requested_by_email="dev@example.com",
        requested_at=now,
        started_at=None,
        completed_at=None,
        failed_at=None,
        error_message=None,
        restore_log_path="../backups/evil.log",
        created_at=now,
        updated_at=now,
    )

    with pytest.raises(ValueError, match="escapes restore logs directory"):
        resolve_restore_job_log_path(job)


def test_resolve_backup_path_rejects_traversal():
    from app.shared.database_backup.paths import resolve_backup_path

    with pytest.raises(ValueError):
        resolve_backup_path("../evil.dump")


def test_resolve_backup_path_accepts_supported_extensions(tmp_path, monkeypatch):
    from app.shared.database_backup.paths import resolve_backup_path

    root = tmp_path / "repo"
    (root / "backups").mkdir(parents=True)
    monkeypatch.setattr("app.shared.database_backup.paths.get_repo_root", lambda: root)

    for name in ("fair_crm_backup_20260702_120000.dump", "kyrox_core_backup_20260702_120000.dump", "fair_stand_backup_20260702_120000.dump", "fair_crm_backup_20260702_120000.sql", "fair_crm_data_package_20260702_120000.zip"):
        path = resolve_backup_path(name)
        assert path.name == name

    with pytest.raises(ValueError):
        resolve_backup_path("evil.exe")


def test_restore_job_can_be_started_from_api(client, auth_headers, backups_root, monkeypatch):
    from types import SimpleNamespace

    from app.shared.database_backup.engine import BackupVerificationResult

    launched: list[dict] = []
    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_service.verify_backup_dump",
        lambda **kwargs: BackupVerificationResult(path=kwargs["dump_path"], size_bytes=32, toc_entry_count=1),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.api.routes.get_settings",
        lambda: SimpleNamespace(database_restore_enabled=True),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.api.routes.resolve_database_url",
        lambda database_key: "postgresql://postgres:postgres@localhost:5432/fair_crm",
    )
    monkeypatch.setattr(
        "app.modules.system_admin.api.routes.launch_restore_job_process",
        lambda **kwargs: launched.append(kwargs),
    )

    create = client.post("/api/v1/admin/backups", headers=auth_headers, json={})
    backup_id = _first_item(create.json())["id"]
    restore = client.post(f"/api/v1/admin/backups/{backup_id}/restore", headers=auth_headers)
    assert restore.status_code == 202, restore.text
    job_id = restore.json()["id"]

    started = client.post(f"/api/v1/admin/backups/restore-jobs/{job_id}/start", headers=auth_headers)
    assert started.status_code == 202
    assert started.json()["status"] == "running"
    assert launched == [{
        "job_id": launched[0]["job_id"],
        "target_database_url": "postgresql://postgres:postgres@localhost:5432/fair_crm",
    }]

    duplicate = client.post(f"/api/v1/admin/backups/restore-jobs/{job_id}/start", headers=auth_headers)
    assert duplicate.status_code == 409

    delete_running = client.delete(f"/api/v1/admin/backups/restore-jobs/{job_id}", headers=auth_headers)
    assert delete_running.status_code == 409


def _record_pg_dump(monkeypatch):
    calls: list[dict] = []

    def _dump(**kwargs):
        calls.append(kwargs)
        return _fake_pg_dump(
            database_url=kwargs["database_url"],
            output_path=kwargs["output_path"],
            on_stage=kwargs.get("on_stage"),
        )

    monkeypatch.setattr("app.modules.system_admin.application.backup_job_runner.pg_dump_custom", _dump)
    return calls


def test_omitted_scope_and_empty_tables_stay_full_backup(client, auth_headers, backups_root, monkeypatch):
    calls = _record_pg_dump(monkeypatch)
    create = client.post(
        "/api/v1/admin/backups",
        headers=auth_headers,
        json={"database_keys": ["fair_crm"], "tables": []},
    )
    assert create.status_code == 202, create.text
    item = _first_item(create.json())
    detail = client.get(f"/api/v1/admin/backups/{item['id']}", headers=auth_headers)
    assert detail.json()["manifest_json"] == {"scope": "full"}
    assert "tables" not in calls[0]


def test_explicit_full_scope_ignores_table_payload(client, auth_headers, backups_root, monkeypatch):
    calls = _record_pg_dump(monkeypatch)
    create = client.post(
        "/api/v1/admin/backups",
        headers=auth_headers,
        json={"scope": "full", "tables": ["public.crm_quotes"]},
    )
    assert create.status_code == 202, create.text
    item = _first_item(create.json())
    detail = client.get(f"/api/v1/admin/backups/{item['id']}", headers=auth_headers)
    assert detail.json()["manifest_json"] == {"scope": "full"}
    assert "tables" not in calls[0]


def test_selected_backup_passes_only_requested_tables(client, auth_headers, backups_root, monkeypatch):
    calls = _record_pg_dump(monkeypatch)
    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_service.list_public_base_tables",
        lambda database_url: ["public.crm_quotes", "public.crm_contacts", "public.crm_customers"],
    )
    create = client.post(
        "/api/v1/admin/backups",
        headers=auth_headers,
        json={
            "database_keys": ["fair_crm"],
            "scope": "selected_tables",
            "tables": ["crm_quotes", "public.crm_contacts"],
        },
    )
    assert create.status_code == 202, create.text
    item = _first_item(create.json())
    detail = client.get(f"/api/v1/admin/backups/{item['id']}", headers=auth_headers)
    assert detail.json()["manifest_json"] == {
        "scope": "selected_tables",
        "tables": ["public.crm_quotes", "public.crm_contacts"],
    }
    assert calls[0]["tables"] == ["public.crm_quotes", "public.crm_contacts"]


def test_selected_backup_rejects_unknown_duplicate_and_unsafe_tables(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_service.list_public_base_tables",
        lambda database_url: ["public.crm_quotes"],
    )
    unknown = client.post(
        "/api/v1/admin/backups",
        headers=auth_headers,
        json={"database_keys": ["fair_crm"], "scope": "selected_tables", "tables": ["public.missing_table"]},
    )
    assert unknown.status_code == 400
    duplicate = client.post(
        "/api/v1/admin/backups",
        headers=auth_headers,
        json={"database_keys": ["fair_crm"], "scope": "selected_tables", "tables": ["crm_quotes", "public.crm_quotes"]},
    )
    assert duplicate.status_code == 400
    unsafe = client.post(
        "/api/v1/admin/backups",
        headers=auth_headers,
        json={"database_keys": ["fair_crm"], "scope": "selected_tables", "tables": ["public.crm_quotes;drop"]},
    )
    assert unsafe.status_code == 400
    empty = client.post(
        "/api/v1/admin/backups",
        headers=auth_headers,
        json={"database_keys": ["fair_crm"], "scope": "selected_tables", "tables": []},
    )
    assert empty.status_code == 400


def test_selected_backup_requires_dump_format_and_one_database(client, auth_headers):
    sql = client.post(
        "/api/v1/admin/backups",
        headers=auth_headers,
        json={"backup_format": "postgresql_sql", "scope": "selected_tables", "tables": ["public.crm_quotes"]},
    )
    assert sql.status_code == 400
    multi = client.post(
        "/api/v1/admin/backups",
        headers=auth_headers,
        json={
            "database_keys": ["fair_crm", "kyrox_core"],
            "scope": "selected_tables",
            "tables": ["public.crm_quotes"],
        },
    )
    assert multi.status_code == 400


def test_backup_catalog_is_database_scoped(client, auth_headers, monkeypatch):
    seen: list[str] = []

    def _catalog(database_url: str) -> list[str]:
        seen.append(database_url)
        return ["public.crm_quotes"] if database_url.endswith("/fair_crm") else ["public.identity_users"]

    monkeypatch.setattr("app.modules.system_admin.api.routes.list_public_base_tables", _catalog)
    monkeypatch.setattr(
        "app.modules.system_admin.api.routes.resolve_database_url",
        lambda database_key: f"postgresql://postgres:postgres@localhost:5432/{database_key.value}",
    )
    fair = client.get("/api/v1/admin/backups/catalog", headers=auth_headers, params={"database_key": "fair_crm"})
    core = client.get("/api/v1/admin/backups/catalog", headers=auth_headers, params={"database_key": "kyrox_core"})
    assert fair.status_code == 200
    assert fair.json() == {"database_key": "fair_crm", "tables": ["public.crm_quotes"]}
    assert core.json()["tables"] == ["public.identity_users"]
    assert seen[0].endswith("/fair_crm")
    assert seen[1].endswith("/kyrox_core")


def test_catalog_forbidden_without_permission(client, auth_headers):
    from app.modules.system_admin.api.dependencies import get_authorization_adapter
    from tests.conftest import AllowAllAuthorization, DenyAllAuthorization

    app = client.app
    app.dependency_overrides[get_authorization_adapter] = lambda: DenyAllAuthorization()
    try:
        res = client.get("/api/v1/admin/backups/catalog", headers=auth_headers, params={"database_key": "fair_crm"})
        assert res.status_code == 403
    finally:
        app.dependency_overrides[get_authorization_adapter] = lambda: AllowAllAuthorization()


def test_restore_rejects_sql_and_universal_package(client, auth_headers, backups_root):
    sql = client.post("/api/v1/admin/backups", headers=auth_headers, json={"backup_format": "postgresql_sql"})
    sql_restore = client.post(
        f"/api/v1/admin/backups/{_first_item(sql.json())['id']}/restore",
        headers=auth_headers,
        json={"scope": "selected_tables", "tables": ["public.crm_quotes"]},
    )
    assert sql_restore.status_code == 400
    package = client.post(
        "/api/v1/admin/backups",
        headers=auth_headers,
        json={"backup_format": "universal_data_package"},
    )
    package_restore = client.post(
        f"/api/v1/admin/backups/{_first_item(package.json())['id']}/restore",
        headers=auth_headers,
    )
    assert package_restore.status_code == 400


def test_selected_restore_rejects_table_missing_from_archive(client, auth_headers, backups_root, monkeypatch):
    from app.shared.database_backup.engine import BackupVerificationResult

    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_service.verify_backup_dump",
        lambda **kwargs: BackupVerificationResult(path=kwargs["dump_path"], size_bytes=32, toc_entry_count=1),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_service.list_custom_dump_tables",
        lambda **kwargs: ["public.crm_quotes"],
    )
    create = client.post("/api/v1/admin/backups", headers=auth_headers, json={})
    backup_id = _first_item(create.json())["id"]
    restore = client.post(
        f"/api/v1/admin/backups/{backup_id}/restore",
        headers=auth_headers,
        json={"scope": "selected_tables", "tables": ["public.crm_contacts"]},
    )
    assert restore.status_code == 400
    assert "crm_contacts" in restore.json()["detail"]


def test_full_restore_runner_omits_table_switch_for_legacy_null_manifest(
    client, auth_headers, backups_root, monkeypatch, db_session
):
    from uuid import UUID

    from app.modules.system_admin.application.restore_job_service import (
        RestoreJobMaintenanceCommand,
        RestoreJobMaintenanceRunner,
    )
    from app.modules.system_admin.infrastructure.persistence.models import SystemBackupRestoreJobModel
    from app.shared.database_backup.engine import BackupVerificationResult

    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_service.verify_backup_dump",
        lambda **kwargs: BackupVerificationResult(path=kwargs["dump_path"], size_bytes=32, toc_entry_count=1),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.verify_backup_dump",
        lambda **kwargs: BackupVerificationResult(path=kwargs["dump_path"], size_bytes=32, toc_entry_count=1),
    )
    calls: list[dict] = []
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.pg_restore_custom",
        lambda **kwargs: calls.append(kwargs),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.subprocess.run",
        lambda *args, **kwargs: type("Proc", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.run_post_restore_health_check",
        _success_post_restore_health,
    )

    create = client.post("/api/v1/admin/backups", headers=auth_headers, json={})
    backup_id = _first_item(create.json())["id"]
    restore = client.post(f"/api/v1/admin/backups/{backup_id}/restore", headers=auth_headers)
    assert restore.status_code == 202
    job_id = UUID(restore.json()["id"])
    row = db_session.get(SystemBackupRestoreJobModel, job_id)
    assert row is not None
    row.manifest_json = None
    db_session.commit()

    runner = RestoreJobMaintenanceRunner(session_factory=lambda: db_session)
    assert (
        runner.run(
            RestoreJobMaintenanceCommand(
                job_id=job_id,
                target_database_url="postgresql://postgres:postgres@localhost:5432/fair_crm",
                allow_restore=True,
            )
        )
        == 0
    )
    assert "tables" not in calls[0]


def test_selected_restore_runner_passes_requested_tables(client, auth_headers, backups_root, monkeypatch, db_session):
    from uuid import UUID

    from app.modules.system_admin.application.restore_job_service import (
        RestoreJobMaintenanceCommand,
        RestoreJobMaintenanceRunner,
    )
    from app.shared.database_backup.engine import BackupVerificationResult

    archive = ["public.crm_customers", "public.crm_contacts"]
    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_service.verify_backup_dump",
        lambda **kwargs: BackupVerificationResult(path=kwargs["dump_path"], size_bytes=32, toc_entry_count=2),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_service.list_custom_dump_tables",
        lambda **kwargs: archive,
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.verify_backup_dump",
        lambda **kwargs: BackupVerificationResult(path=kwargs["dump_path"], size_bytes=32, toc_entry_count=2),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.list_custom_dump_tables",
        lambda **kwargs: archive,
    )
    calls: list[dict] = []
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.pg_restore_custom",
        lambda **kwargs: calls.append(kwargs),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.subprocess.run",
        lambda *args, **kwargs: type("Proc", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.run_post_restore_health_check",
        _success_post_restore_health,
    )

    create = client.post("/api/v1/admin/backups", headers=auth_headers, json={})
    backup_id = _first_item(create.json())["id"]
    restore = client.post(
        f"/api/v1/admin/backups/{backup_id}/restore",
        headers=auth_headers,
        json={"scope": "selected_tables", "tables": ["public.crm_customers"]},
    )
    assert restore.status_code == 202, restore.text
    job_id = UUID(restore.json()["id"])
    runner = RestoreJobMaintenanceRunner(session_factory=lambda: db_session)
    assert (
        runner.run(
            RestoreJobMaintenanceCommand(
                job_id=job_id,
                target_database_url="postgresql://postgres:postgres@localhost:5432/fair_crm",
                allow_restore=True,
            )
        )
        == 0
    )
    assert calls[0]["tables"] == ["public.crm_customers"]


def _ok_organization_reconciliation(**kwargs):
    from app.shared.database_backup.restore_reconciliation import RestoreOrganizationReconciliationResult

    _ = kwargs
    return RestoreOrganizationReconciliationResult(
        ok=True,
        organization_count=0,
        active_count=0,
        inactive_count=0,
        deleted_count=0,
    )


def _patch_certified_restore(monkeypatch, *, checksum: str | None = "deadbeef" * 8, pg_restore=None, health=None):
    from app.shared.database_backup.engine import BackupVerificationResult

    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_service.verify_backup_dump",
        lambda **kwargs: BackupVerificationResult(path=kwargs["dump_path"], size_bytes=32, toc_entry_count=1),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.verify_backup_dump",
        lambda **kwargs: BackupVerificationResult(path=kwargs["dump_path"], size_bytes=32, toc_entry_count=1),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.pg_restore_custom",
        pg_restore or (lambda **kwargs: None),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.subprocess.run",
        lambda *args, **kwargs: type("Proc", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.run_post_restore_health_check",
        health or _success_post_restore_health,
    )
    monkeypatch.setattr(
        "app.modules.system_admin.maintenance.certified_restore_runner.run_restore_organization_reconciliation",
        _ok_organization_reconciliation,
    )
    if checksum is not None:
        monkeypatch.setattr(
            "app.shared.database_backup.engine.sha256_file",
            lambda path: checksum,
        )


def _backup_row(db_session, backup_id: str):
    from uuid import UUID

    from app.modules.system_admin.infrastructure.persistence.models import SystemBackupModel

    db_session.expire_all()
    return db_session.get(SystemBackupModel, UUID(backup_id))


def _rewind_catalog_row(db_session, backup_id: str, *, stage: str) -> None:
    row = _backup_row(db_session, backup_id)
    row.status = "running"
    row.progress_stage = stage
    row.file_size = None
    row.checksum = None
    row.completed_at = None
    db_session.commit()


def _run_certified(db_session, job_id):
    from app.modules.system_admin.application.restore_job_service import RestoreJobMaintenanceCommand
    from app.modules.system_admin.maintenance.certified_restore_runner import (
        CertifiedRestoreJobMaintenanceRunner,
    )

    runner = CertifiedRestoreJobMaintenanceRunner(session_factory=lambda: db_session)
    return runner.run(
        RestoreJobMaintenanceCommand(
            job_id=job_id,
            target_database_url="postgresql://postgres:postgres@localhost:5432/fair_crm",
            allow_restore=True,
        )
    )


def test_full_restore_reapplies_validated_source_backup_and_leaves_sibling(
    client, auth_headers, backups_root, monkeypatch, db_session
):
    from uuid import UUID

    source = client.post("/api/v1/admin/backups", headers=auth_headers, json={})
    source_id = _first_item(source.json())["id"]
    sibling = client.post(
        "/api/v1/admin/backups",
        headers=auth_headers,
        json={"database_keys": ["fair_stand"]},
    )
    sibling_id = _first_item(sibling.json())["id"]
    source_row = _backup_row(db_session, source_id)
    assert source_row.status == "completed"
    assert source_row.file_size
    assert source_row.checksum
    source_row.download_count = 4
    db_session.commit()
    preserved = {
        "file_size": source_row.file_size,
        "checksum": source_row.checksum,
        "completed_at": source_row.completed_at,
        "manifest_json": source_row.manifest_json,
        "download_count": 4,
        "file_name": source_row.file_name,
        "notes": source_row.notes,
    }
    _rewind_catalog_row(db_session, sibling_id, stage="preparing")
    db_session.commit()

    def pg_restore(**kwargs):
        _ = kwargs
        _rewind_catalog_row(db_session, source_id, stage="dumping")

    _patch_certified_restore(monkeypatch, pg_restore=pg_restore)
    restore = client.post(f"/api/v1/admin/backups/{source_id}/restore", headers=auth_headers)
    assert restore.status_code == 202, restore.text

    assert _run_certified(db_session, UUID(restore.json()["id"])) == 0

    restored = _backup_row(db_session, source_id)
    assert restored.status == "completed"
    assert restored.progress_stage == "completed"
    assert restored.file_size == preserved["file_size"]
    assert restored.checksum == preserved["checksum"]
    assert restored.completed_at == preserved["completed_at"]
    assert restored.manifest_json == preserved["manifest_json"]
    assert restored.download_count == preserved["download_count"]
    assert restored.file_name == preserved["file_name"]
    sibling_row = _backup_row(db_session, sibling_id)
    assert sibling_row.status == "running"
    assert sibling_row.progress_stage == "preparing"
    assert sibling_row.file_size is None
    assert sibling_row.checksum is None


def test_legacy_null_manifest_full_restore_reapplies_source_backup(
    client, auth_headers, backups_root, monkeypatch, db_session
):
    from uuid import UUID

    from app.modules.system_admin.infrastructure.persistence.models import SystemBackupRestoreJobModel

    source = client.post("/api/v1/admin/backups", headers=auth_headers, json={})
    source_id = _first_item(source.json())["id"]
    source_row = _backup_row(db_session, source_id)
    source_row.manifest_json = None
    checksum = source_row.checksum
    file_size = source_row.file_size
    completed_at = source_row.completed_at
    db_session.commit()

    def pg_restore(**kwargs):
        assert "tables" not in kwargs
        _rewind_catalog_row(db_session, source_id, stage="dumping")

    _patch_certified_restore(monkeypatch, pg_restore=pg_restore)
    restore = client.post(f"/api/v1/admin/backups/{source_id}/restore", headers=auth_headers)
    job_id = UUID(restore.json()["id"])
    job = db_session.get(SystemBackupRestoreJobModel, job_id)
    job.manifest_json = None
    db_session.commit()

    assert _run_certified(db_session, job_id) == 0
    restored = _backup_row(db_session, source_id)
    assert restored.status == "completed"
    assert restored.file_size == file_size
    assert restored.checksum == checksum
    assert restored.completed_at == completed_at
    assert restored.manifest_json is None


def test_selected_restore_does_not_rewrite_catalog_rows(
    client, auth_headers, backups_root, monkeypatch, db_session
):
    from uuid import UUID

    source = client.post("/api/v1/admin/backups", headers=auth_headers, json={})
    source_id = _first_item(source.json())["id"]
    sibling = client.post(
        "/api/v1/admin/backups",
        headers=auth_headers,
        json={"database_keys": ["kyrox_core"]},
    )
    sibling_id = _first_item(sibling.json())["id"]
    _rewind_catalog_row(db_session, sibling_id, stage="preparing")
    calls: list[dict] = []

    def pg_restore(**kwargs):
        calls.append(kwargs)
        _rewind_catalog_row(db_session, source_id, stage="dumping")

    _patch_certified_restore(monkeypatch, pg_restore=pg_restore)
    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_service.verify_backup_dump",
        lambda **kwargs: __import__(
            "app.shared.database_backup.engine", fromlist=["BackupVerificationResult"]
        ).BackupVerificationResult(path=kwargs["dump_path"], size_bytes=32, toc_entry_count=1),
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_service.list_custom_dump_tables",
        lambda **kwargs: ["public.crm_customers"],
    )
    monkeypatch.setattr(
        "app.modules.system_admin.application.restore_job_service.list_custom_dump_tables",
        lambda **kwargs: ["public.crm_customers"],
    )
    restore = client.post(
        f"/api/v1/admin/backups/{source_id}/restore",
        headers=auth_headers,
        json={"scope": "selected_tables", "tables": ["public.crm_customers"]},
    )
    assert restore.status_code == 202, restore.text
    assert _run_certified(db_session, UUID(restore.json()["id"])) == 0
    assert calls[0]["tables"] == ["public.crm_customers"]
    rewound = _backup_row(db_session, source_id)
    assert rewound.status == "running"
    assert rewound.progress_stage == "dumping"
    assert rewound.checksum is None
    sibling_row = _backup_row(db_session, sibling_id)
    assert sibling_row.status == "running"
    assert sibling_row.progress_stage == "preparing"


def test_restore_failure_does_not_reapply_source_backup(
    client, auth_headers, backups_root, monkeypatch, db_session
):
    from uuid import UUID

    from app.shared.database_backup.engine import DatabaseBackupError

    source = client.post("/api/v1/admin/backups", headers=auth_headers, json={})
    source_id = _first_item(source.json())["id"]
    sibling = client.post(
        "/api/v1/admin/backups",
        headers=auth_headers,
        json={"database_keys": ["fair_stand"]},
    )
    sibling_id = _first_item(sibling.json())["id"]
    _rewind_catalog_row(db_session, sibling_id, stage="preparing")

    def pg_restore(**kwargs):
        _rewind_catalog_row(db_session, source_id, stage="dumping")
        raise DatabaseBackupError("pg_restore failed")

    _patch_certified_restore(monkeypatch, pg_restore=pg_restore)
    restore = client.post(f"/api/v1/admin/backups/{source_id}/restore", headers=auth_headers)
    assert _run_certified(db_session, UUID(restore.json()["id"])) == 1
    rewound = _backup_row(db_session, source_id)
    assert rewound.status == "running"
    assert rewound.progress_stage == "dumping"
    assert rewound.file_size is None
    assert rewound.checksum is None
    sibling_row = _backup_row(db_session, sibling_id)
    assert sibling_row.status == "running"
    assert sibling_row.progress_stage == "preparing"


def test_invalid_restore_source_does_not_complete_running_row(
    client, auth_headers, backups_root, monkeypatch, db_session
):
    from uuid import UUID

    calls: list[dict] = []

    def pg_restore(**kwargs):
        calls.append(kwargs)

    _patch_certified_restore(monkeypatch, checksum="b" * 64, pg_restore=pg_restore)

    def prepare_running_source() -> tuple[str, Path, str]:
        created = client.post("/api/v1/admin/backups", headers=auth_headers, json={})
        backup_id = _first_item(created.json())["id"]
        file_name = _backup_row(db_session, backup_id).file_name
        restore = client.post(f"/api/v1/admin/backups/{backup_id}/restore", headers=auth_headers)
        assert restore.status_code == 202, restore.text
        _rewind_catalog_row(db_session, backup_id, stage="dumping")
        return backup_id, backups_root / "backups" / file_name, restore.json()["id"]

    completed = client.post("/api/v1/admin/backups", headers=auth_headers, json={})
    completed_id = _first_item(completed.json())["id"]
    original_checksum = _backup_row(db_session, completed_id).checksum
    completed_restore = client.post(f"/api/v1/admin/backups/{completed_id}/restore", headers=auth_headers)
    assert completed_restore.status_code == 202, completed_restore.text
    assert _run_certified(db_session, UUID(completed_restore.json()["id"])) == 1
    assert calls == []
    unchanged = _backup_row(db_session, completed_id)
    assert unchanged.status == "completed"
    assert unchanged.checksum == original_checksum

    source_id, _dump_path, job_id = prepare_running_source()
    assert _run_certified(db_session, UUID(job_id)) == 1
    row = _backup_row(db_session, source_id)
    assert row.status == "running"
    assert row.checksum is None

    source_id, dump_path, job_id = prepare_running_source()
    dump_path.unlink()
    _patch_certified_restore(monkeypatch, pg_restore=pg_restore)
    assert _run_certified(db_session, UUID(job_id)) == 1
    row = _backup_row(db_session, source_id)
    assert row.status == "running"
    assert row.file_size is None

    source_id, dump_path, job_id = prepare_running_source()
    dump_path.write_bytes(b"not-a-dump")
    _patch_certified_restore(monkeypatch, pg_restore=pg_restore)
    assert _run_certified(db_session, UUID(job_id)) == 1
    assert calls == []
    row = _backup_row(db_session, source_id)
    assert row.status == "running"
    assert row.file_size is None
    assert row.checksum is None
