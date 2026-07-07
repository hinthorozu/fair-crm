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
            memberships_count=7,
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


def test_resolve_backup_path_rejects_traversal():
    from app.shared.database_backup.paths import resolve_backup_path

    with pytest.raises(ValueError):
        resolve_backup_path("../evil.dump")


def test_resolve_backup_path_accepts_supported_extensions(tmp_path, monkeypatch):
    from app.shared.database_backup.paths import resolve_backup_path

    root = tmp_path / "repo"
    (root / "backups").mkdir(parents=True)
    monkeypatch.setattr("app.shared.database_backup.paths.get_repo_root", lambda: root)

    for name in ("fair_crm_backup_20260702_120000.dump", "kyrox_core_backup_20260702_120000.dump", "fair_crm_backup_20260702_120000.sql", "fair_crm_data_package_20260702_120000.zip"):
        path = resolve_backup_path(name)
        assert path.name == name

    with pytest.raises(ValueError):
        resolve_backup_path("evil.exe")
