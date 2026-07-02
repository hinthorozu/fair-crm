"""Admin database backup API tests (Sprint 09.2.2)."""

from pathlib import Path

import pytest

from app.shared.database_backup.engine import BackupRunResult


def _fake_pg_dump(*, database_url: str, output_path: Path, on_stage=None) -> BackupRunResult:
    _ = database_url
    if on_stage:
        on_stage("preparing")
        on_stage("dumping")
        on_stage("compressing")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = b"FAIRCRM_TEST_BACKUP"
    output_path.write_bytes(payload)
    return BackupRunResult(
        path=output_path,
        size_bytes=len(payload),
        checksum_sha256="deadbeef" * 8,
        toc_entry_count=1,
        toolchain="test",
    )


@pytest.fixture
def backups_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    (root / "backups").mkdir(parents=True)
    monkeypatch.setattr("app.shared.database_backup.paths.get_repo_root", lambda: root)
    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_job_runner.pg_dump_custom",
        _fake_pg_dump,
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
    backup_id = body["id"]
    assert body["status"] in {"running", "completed"}
    assert body["file_name"].startswith("faircrm_backup_")

    detail = client.get(f"/api/v1/admin/backups/{backup_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "completed"
    assert detail.json()["notes"] == "Sprint 09.2.2 test backup"
    assert detail.json()["file_size"] == len(b"FAIRCRM_TEST_BACKUP")

    listing = client.get("/api/v1/admin/backups", headers=auth_headers)
    assert listing.status_code == 200
    data = listing.json()
    assert data["pagination"]["totalItems"] >= 1
    assert any(item["id"] == backup_id for item in data["items"])


def test_download_backup_increments_count(client, auth_headers, backups_root):
    create = client.post("/api/v1/admin/backups", headers=auth_headers, json={"notes": None})
    assert create.status_code == 202
    backup_id = create.json()["id"]
    file_name = create.json()["file_name"]

    download = client.get(f"/api/v1/admin/backups/{backup_id}/download", headers=auth_headers)
    assert download.status_code == 200
    assert download.content == b"FAIRCRM_TEST_BACKUP"
    assert download.headers.get("content-disposition", "").find(file_name) >= 0

    detail = client.get(f"/api/v1/admin/backups/{backup_id}", headers=auth_headers)
    assert detail.json()["download_count"] == 1


def test_restore_endpoint_disabled(client, auth_headers, backups_root):
    create = client.post("/api/v1/admin/backups", headers=auth_headers, json={})
    backup_id = create.json()["id"]

    restore = client.post(f"/api/v1/admin/backups/{backup_id}/restore", headers=auth_headers)
    assert restore.status_code == 501
    assert restore.json()["enabled"] is False


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


def test_resolve_backup_path_rejects_traversal():
    from app.shared.database_backup.paths import resolve_backup_path

    with pytest.raises(ValueError):
        resolve_backup_path("../evil.dump")
