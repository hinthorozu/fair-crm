from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.integrations.kyrox_core.ports import AuthContext
from app.main import create_app
from app.modules.imports.infrastructure.persistence.models import ImportBatchModel
from app.modules.organization_closure.application.artifact_cleanup import (
    OrganizationClosureArtifactCleanupService,
)
from app.modules.organization_closure.application.closure_package import (
    INVENTORY_SCHEMA_VERSION,
    PACKAGE_SCHEMA_VERSION,
)
from app.modules.organization_closure.application.export_planner import EXPORT_SCHEMA_VERSION
from app.modules.organization_closure.application.service import (
    ClosureExecutionConflictError,
    ClosureLifecyclePreconditionError,
)
from app.modules.organization_closure.infrastructure.models import (
    OrganizationClosureArtifactInventoryModel,
    OrganizationClosureExecutionModel,
    OrganizationClosureExportPlanModel,
    OrganizationClosurePackageModel,
)
from app.modules.organization_closure.infrastructure.package_repository import (
    SqlAlchemyOrganizationClosurePackageRepository,
)
from app.modules.organization_closure.infrastructure.package_storage import (
    canonical_manifest_bytes,
    write_immutable_package,
)


class FakeAuthorization:
    def __init__(self, *, allowed: bool = True) -> None:
        self.allowed = allowed

    def check_permission(self, **kwargs: object) -> bool:
        _ = kwargs
        return self.allowed


class FakeLifecycle:
    def __init__(
        self,
        *,
        status: str = "suspended",
        updated_at: datetime,
        is_deleted: bool = False,
    ) -> None:
        self.status = status
        self.updated_at = updated_at
        self.is_deleted = is_deleted

    def get_snapshot(self, organization_id: object) -> SimpleNamespace:
        return SimpleNamespace(
            organization_id=organization_id,
            status=self.status,
            work_allowed=self.status == "active" and not self.is_deleted,
            updated_at=self.updated_at,
            is_deleted=self.is_deleted,
            deleted_at=None,
        )


class RecordingAudit:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def record_event(self, **kwargs: object) -> None:
        self.events.append(kwargs)


def _auth(organization_id) -> AuthContext:
    return AuthContext(
        user_id=uuid4(),
        email="platform-admin@example.com",
        session_id=uuid4(),
        organization_id=organization_id,
    )


def _foundation(
    db_session,
    organization_id,
    package_root: Path,
    *,
    ready_at: datetime,
) -> tuple[
    OrganizationClosureExecutionModel,
    OrganizationClosurePackageModel,
    AuthContext,
]:
    auth = _auth(organization_id)
    execution = OrganizationClosureExecutionModel(
        id=uuid4(),
        organization_id=organization_id,
        idempotency_key=f"ol08-e2-{uuid4()}",
        status="in_progress",
        current_phase="package_integrity_verified",
        actor_user_id=auth.user_id,
        actor_session_id=auth.session_id,
        attempt_count=1,
        failure_code=None,
        failure_message=None,
        created_at=ready_at,
        updated_at=ready_at,
        last_retry_at=None,
        closed_at=None,
    )
    plan = OrganizationClosureExportPlanModel(
        id=uuid4(),
        organization_id=organization_id,
        closure_execution_id=execution.id,
        schema_version=EXPORT_SCHEMA_VERSION,
        disposition="required",
        status="planned",
        manifest_json={},
        manifest_digest="0" * 64,
        actor_user_id=auth.user_id,
        actor_session_id=auth.session_id,
        created_at=ready_at,
        updated_at=ready_at,
    )
    package_id = uuid4()
    manifest = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "organization_id": str(organization_id),
        "closure_execution_id": str(execution.id),
        "package_id": str(package_id),
        "members": [],
    }
    stored = write_immutable_package(
        organization_id=organization_id,
        execution_id=execution.id,
        package_id=package_id,
        manifest=manifest,
        members=[],
        storage_root=package_root,
    )
    package = OrganizationClosurePackageModel(
        id=package_id,
        organization_id=organization_id,
        closure_execution_id=execution.id,
        export_plan_id=plan.id,
        schema_version=PACKAGE_SCHEMA_VERSION,
        inventory_schema_version=INVENTORY_SCHEMA_VERSION,
        status="integrity_verified",
        storage_locator=stored.relative_locator,
        manifest_json=manifest,
        manifest_digest=sha256(canonical_manifest_bytes(manifest)).hexdigest(),
        package_digest=stored.digest,
        byte_size=stored.byte_size,
        attempt_count=1,
        failure_code=None,
        failure_message=None,
        actor_user_id=auth.user_id,
        actor_session_id=auth.session_id,
        created_at=ready_at,
        updated_at=ready_at,
        ready_at=ready_at,
        integrity_verified_at=ready_at,
        expires_at=ready_at + timedelta(days=30),
        purged_at=None,
    )
    db_session.add_all([execution, plan, package])
    db_session.flush()
    return execution, package, auth


def _inventory_item(
    db_session,
    *,
    organization_id,
    execution_id,
    package_id,
    artifact_key: str,
    artifact_class: str,
    ownership_class: str,
    owner_type: str,
    owner_id: str,
    storage_kind: str,
    cleanup_action: str,
    locator_json: dict,
    content: bytes | None = None,
) -> OrganizationClosureArtifactInventoryModel:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    item = OrganizationClosureArtifactInventoryModel(
        id=uuid4(),
        package_id=package_id,
        closure_execution_id=execution_id,
        organization_id=organization_id,
        inventory_schema_version=INVENTORY_SCHEMA_VERSION,
        artifact_key=artifact_key,
        artifact_class=artifact_class,
        ownership_class=ownership_class,
        owner_type=owner_type,
        owner_id=owner_id,
        storage_kind=storage_kind,
        package_disposition="included" if content is not None else "not_included",
        cleanup_action=cleanup_action,
        locator_json=locator_json,
        package_entry=None,
        byte_size=len(content) if content is not None else None,
        content_digest=sha256(content).hexdigest() if content is not None else None,
        cleanup_status="pending",
        cleanup_attempt_count=0,
        cleanup_failure_code=None,
        cleanup_failure_message=None,
        cleanup_last_attempt_at=None,
        nonexistence_verified_at=None,
        created_at=now,
    )
    db_session.add(item)
    db_session.flush()
    return item


def _add_import_batch(db_session, organization_id, *, batch_id, content: bytes) -> ImportBatchModel:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    batch = ImportBatchModel(
        id=batch_id,
        organization_id=organization_id,
        fair_id=None,
        source_type="excel",
        file_name="customers.xlsx",
        status="completed",
        total_rows=1,
        valid_rows=1,
        invalid_rows=0,
        duplicate_rows=0,
        created_rows=1,
        updated_rows=0,
        skipped_rows=0,
        created_participations=0,
        updated_participations=0,
        column_mapping_json={},
        raw_preview_json={},
        has_header_row=True,
        header_mode="first_row",
        header_row_index=0,
        selected_sheet_name="Sheet1",
        stored_file_content=content,
        created_at=now,
        updated_at=now,
        completed_at=now,
        analyzed_at=now,
        notes=None,
    )
    db_session.add(batch)
    db_session.flush()
    return batch


def _service(
    db_session,
    *,
    now: datetime,
    lifecycle: FakeLifecycle,
    package_root: Path,
    logo_root: Path,
    handoff_root: Path,
):
    audit = RecordingAudit()
    service = OrganizationClosureArtifactCleanupService(
        SqlAlchemyOrganizationClosurePackageRepository(db_session),
        FakeAuthorization(),
        lifecycle,
        audit,
        package_storage_root=package_root,
        logo_storage_root=logo_root,
        handoff_storage_root=handoff_root,
        now_provider=lambda: now,
    )
    return service, audit


def test_source_artifact_cleanup_is_blocked_until_exact_suspension_grace(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    now = datetime(2026, 2, 1, tzinfo=UTC)
    package_root = tmp_path / "packages"
    logo_root = tmp_path / "logos"
    handoff_root = tmp_path / "handoff"
    execution, package, auth = _foundation(
        db_session,
        organization_id,
        package_root,
        ready_at=now - timedelta(days=1),
    )
    organization_dir = logo_root / str(organization_id)
    organization_dir.mkdir(parents=True)
    logo = organization_dir / "grace.png"
    logo.write_bytes(b"grace-logo")
    item = _inventory_item(
        db_session,
        organization_id=organization_id,
        execution_id=execution.id,
        package_id=package.id,
        artifact_key="quote_template_logo:grace",
        artifact_class="quote_template_logo",
        ownership_class="managed_product_artifact",
        owner_type="quote_template_version",
        owner_id=str(uuid4()),
        storage_kind="managed_file",
        cleanup_action="package_then_hard_delete",
        locator_json={"filename": "grace.png"},
        content=b"grace-logo",
    )
    service, _ = _service(
        db_session,
        now=now,
        lifecycle=FakeLifecycle(updated_at=now - timedelta(days=29, hours=23)),
        package_root=package_root,
        logo_root=logo_root,
        handoff_root=handoff_root,
    )

    with pytest.raises(ClosureLifecyclePreconditionError):
        service.purge_source_artifacts(
            organization_id=organization_id,
            execution_id=execution.id,
            auth=auth,
            access_token="token",
        )

    assert logo.exists()
    assert item.cleanup_status == "pending"
    assert item.cleanup_attempt_count == 0


def test_source_cleanup_strictly_purges_files_but_leaves_import_bytes_for_ol08d(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    now = datetime(2026, 3, 15, tzinfo=UTC)
    package_root = tmp_path / "packages"
    logo_root = tmp_path / "logos"
    handoff_root = tmp_path / "handoff"
    execution, package, auth = _foundation(
        db_session,
        organization_id,
        package_root,
        ready_at=now - timedelta(days=5),
    )

    organization_dir = logo_root / str(organization_id)
    organization_dir.mkdir(parents=True)
    logo = organization_dir / "owned.png"
    logo_bytes = b"owned-logo"
    logo.write_bytes(logo_bytes)
    logo_item = _inventory_item(
        db_session,
        organization_id=organization_id,
        execution_id=execution.id,
        package_id=package.id,
        artifact_key="quote_template_logo:owned",
        artifact_class="quote_template_logo",
        ownership_class="managed_product_artifact",
        owner_type="quote_template_version",
        owner_id=str(uuid4()),
        storage_kind="managed_file",
        cleanup_action="package_then_hard_delete",
        locator_json={"filename": "owned.png"},
        content=logo_bytes,
    )

    handoff_root.mkdir(parents=True)
    run_id = uuid4()
    handoff = handoff_root / f"{run_id}.json"
    handoff_bytes = b'{"handoff":true}\n'
    handoff.write_bytes(handoff_bytes)
    scraper_item = _inventory_item(
        db_session,
        organization_id=organization_id,
        execution_id=execution.id,
        package_id=package.id,
        artifact_key=f"scraper_handoff:{run_id}:json:test",
        artifact_class="scraper_handoff",
        ownership_class="managed_product_artifact",
        owner_type="scraper_run",
        owner_id=str(run_id),
        storage_kind="managed_file",
        cleanup_action="package_then_hard_delete",
        locator_json={
            "run_id": str(run_id),
            "kind": "json",
            "relative_path": handoff.name,
        },
        content=handoff_bytes,
    )

    external_item = _inventory_item(
        db_session,
        organization_id=organization_id,
        execution_id=execution.id,
        package_id=package.id,
        artifact_key="quote_template_logo_external:test",
        artifact_class="quote_template_logo",
        ownership_class="external_reference",
        owner_type="quote_template_version",
        owner_id=str(uuid4()),
        storage_kind="external_reference",
        cleanup_action="relational_pointer_only",
        locator_json={"reference_kind": "quote_template_logo_url"},
    )

    batch_id = uuid4()
    import_bytes = b"IMPORT-BYTES-MUST-REMAIN"
    batch = _add_import_batch(db_session, organization_id, batch_id=batch_id, content=import_bytes)
    import_item = _inventory_item(
        db_session,
        organization_id=organization_id,
        execution_id=execution.id,
        package_id=package.id,
        artifact_key=f"import_upload:{batch_id}",
        artifact_class="import_upload",
        ownership_class="managed_product_artifact",
        owner_type="import_batch",
        owner_id=str(batch_id),
        storage_kind="embedded_database_bytes",
        cleanup_action="package_then_hard_delete",
        locator_json={"batch_id": str(batch_id), "field": "stored_file_content"},
        content=import_bytes,
    )

    service, audit = _service(
        db_session,
        now=now,
        lifecycle=FakeLifecycle(updated_at=now - timedelta(days=30)),
        package_root=package_root,
        logo_root=logo_root,
        handoff_root=handoff_root,
    )
    result = service.purge_source_artifacts(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )

    assert not logo.exists()
    assert not handoff.exists()
    assert logo_item.cleanup_status == "purged"
    assert scraper_item.cleanup_status == "purged"
    assert logo_item.nonexistence_verified_at == now
    assert scraper_item.nonexistence_verified_at == now
    assert external_item.cleanup_status == "not_applicable"
    assert import_item.cleanup_status == "relational_delete_required"
    assert batch.stored_file_content == import_bytes
    assert result.purged == 2
    assert result.not_applicable == 1
    assert result.relational_delete_required == 1
    assert result.blocked == 0
    assert result.file_cleanup_complete is True
    assert any(
        event.get("action") == "organization_closure.artifacts.source_cleanup_reconciled"
        for event in audit.events
    )

    second = service.purge_source_artifacts(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )
    assert second.purged == 2
    assert logo_item.cleanup_attempt_count == 1
    assert scraper_item.cleanup_attempt_count == 1


def test_changed_managed_artifact_blocks_without_deleting_new_bytes(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    now = datetime(2026, 4, 1, tzinfo=UTC)
    package_root = tmp_path / "packages"
    logo_root = tmp_path / "logos"
    handoff_root = tmp_path / "handoff"
    execution, package, auth = _foundation(
        db_session,
        organization_id,
        package_root,
        ready_at=now - timedelta(days=2),
    )
    organization_dir = logo_root / str(organization_id)
    organization_dir.mkdir(parents=True)
    path = organization_dir / "changed.png"
    original = b"original"
    path.write_bytes(b"replacement")
    item = _inventory_item(
        db_session,
        organization_id=organization_id,
        execution_id=execution.id,
        package_id=package.id,
        artifact_key="quote_template_logo:changed",
        artifact_class="quote_template_logo",
        ownership_class="managed_product_artifact",
        owner_type="quote_template_version",
        owner_id=str(uuid4()),
        storage_kind="managed_file",
        cleanup_action="package_then_hard_delete",
        locator_json={"filename": "changed.png"},
        content=original,
    )
    service, _ = _service(
        db_session,
        now=now,
        lifecycle=FakeLifecycle(updated_at=now - timedelta(days=31)),
        package_root=package_root,
        logo_root=logo_root,
        handoff_root=handoff_root,
    )

    result = service.purge_source_artifacts(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )

    assert path.read_bytes() == b"replacement"
    assert item.cleanup_status == "blocked"
    assert item.cleanup_failure_code == "artifact_content_changed"
    assert result.blocked == 1
    assert result.file_cleanup_complete is False


def test_unsafe_scraper_locator_blocks_and_never_deletes_foreign_path(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    now = datetime(2026, 5, 1, tzinfo=UTC)
    package_root = tmp_path / "packages"
    logo_root = tmp_path / "logos"
    handoff_root = tmp_path / "handoff"
    execution, package, auth = _foundation(
        db_session,
        organization_id,
        package_root,
        ready_at=now - timedelta(days=2),
    )
    foreign = tmp_path / "foreign.json"
    foreign.write_bytes(b"foreign")
    run_id = uuid4()
    item = _inventory_item(
        db_session,
        organization_id=organization_id,
        execution_id=execution.id,
        package_id=package.id,
        artifact_key=f"scraper_handoff:{run_id}:json:unsafe",
        artifact_class="scraper_handoff",
        ownership_class="managed_product_artifact",
        owner_type="scraper_run",
        owner_id=str(run_id),
        storage_kind="managed_file",
        cleanup_action="package_then_hard_delete",
        locator_json={
            "run_id": str(run_id),
            "kind": "json",
            "relative_path": "../foreign.json",
        },
        content=b"foreign",
    )
    service, _ = _service(
        db_session,
        now=now,
        lifecycle=FakeLifecycle(updated_at=now - timedelta(days=31)),
        package_root=package_root,
        logo_root=logo_root,
        handoff_root=handoff_root,
    )

    result = service.purge_source_artifacts(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )

    assert foreign.exists()
    assert item.cleanup_status == "blocked"
    assert item.cleanup_failure_code == "invalid_scraper_handoff_locator"
    assert result.blocked == 1


def test_import_inventory_becomes_already_absent_after_ol08d_removes_bytes(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    now = datetime(2026, 6, 1, tzinfo=UTC)
    package_root = tmp_path / "packages"
    logo_root = tmp_path / "logos"
    handoff_root = tmp_path / "handoff"
    execution, package, auth = _foundation(
        db_session,
        organization_id,
        package_root,
        ready_at=now - timedelta(days=2),
    )
    batch_id = uuid4()
    batch = _add_import_batch(db_session, organization_id, batch_id=batch_id, content=b"bytes")
    item = _inventory_item(
        db_session,
        organization_id=organization_id,
        execution_id=execution.id,
        package_id=package.id,
        artifact_key=f"import_upload:{batch_id}",
        artifact_class="import_upload",
        ownership_class="managed_product_artifact",
        owner_type="import_batch",
        owner_id=str(batch_id),
        storage_kind="embedded_database_bytes",
        cleanup_action="package_then_hard_delete",
        locator_json={"batch_id": str(batch_id), "field": "stored_file_content"},
        content=b"bytes",
    )
    service, _ = _service(
        db_session,
        now=now,
        lifecycle=FakeLifecycle(updated_at=now - timedelta(days=31)),
        package_root=package_root,
        logo_root=logo_root,
        handoff_root=handoff_root,
    )

    first = service.purge_source_artifacts(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )
    assert first.relational_delete_required == 1
    batch.stored_file_content = None
    db_session.flush()

    second = service.purge_source_artifacts(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )
    assert second.already_absent == 1
    assert item.cleanup_status == "already_absent"
    assert item.nonexistence_verified_at == now


def test_package_purge_requires_expiry_then_is_strict_and_idempotent(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    ready_at = datetime(2026, 1, 1, tzinfo=UTC)
    before_expiry = ready_at + timedelta(days=29, hours=23)
    package_root = tmp_path / "packages"
    logo_root = tmp_path / "logos"
    handoff_root = tmp_path / "handoff"
    execution, package, auth = _foundation(
        db_session,
        organization_id,
        package_root,
        ready_at=ready_at,
    )
    package_path = package_root / package.storage_locator
    service_before, _ = _service(
        db_session,
        now=before_expiry,
        lifecycle=FakeLifecycle(
            status="suspended",
            updated_at=ready_at - timedelta(days=30),
        ),
        package_root=package_root,
        logo_root=logo_root,
        handoff_root=handoff_root,
    )
    with pytest.raises(ClosureExecutionConflictError):
        service_before.purge_package(
            organization_id=organization_id,
            execution_id=execution.id,
            auth=auth,
            access_token="token",
        )
    assert package_path.exists()

    expiry = ready_at + timedelta(days=30)
    service_expired, audit = _service(
        db_session,
        now=expiry,
        lifecycle=FakeLifecycle(status="suspended", updated_at=ready_at),
        package_root=package_root,
        logo_root=logo_root,
        handoff_root=handoff_root,
    )
    purged = service_expired.purge_package(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )
    assert purged.status == "purged"
    assert purged.purged_at == expiry
    assert not package_path.exists()
    assert any(
        event.get("action") == "organization_closure.package.purged"
        for event in audit.events
    )

    same = service_expired.purge_package(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )
    assert same.status == "purged"
    assert same.purged_at == expiry


def test_reactivation_makes_package_immediately_purge_eligible(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    ready_at = datetime(2026, 7, 1, tzinfo=UTC)
    now = ready_at + timedelta(days=2)
    package_root = tmp_path / "packages"
    execution, package, auth = _foundation(
        db_session,
        organization_id,
        package_root,
        ready_at=ready_at,
    )
    service, _ = _service(
        db_session,
        now=now,
        lifecycle=FakeLifecycle(status="active", updated_at=now),
        package_root=package_root,
        logo_root=tmp_path / "logos",
        handoff_root=tmp_path / "handoff",
    )

    result = service.purge_package(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )

    assert result.status == "purged"
    assert result.purged_at == now
    assert not (package_root / package.storage_locator).exists()


def test_package_integrity_mismatch_blocks_purge_and_preserves_bytes(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    ready_at = datetime(2026, 8, 1, tzinfo=UTC)
    now = ready_at + timedelta(days=31)
    package_root = tmp_path / "packages"
    execution, package, auth = _foundation(
        db_session,
        organization_id,
        package_root,
        ready_at=ready_at,
    )
    path = package_root / package.storage_locator
    path.write_bytes(b"replacement-package-bytes")
    service, _ = _service(
        db_session,
        now=now,
        lifecycle=FakeLifecycle(status="suspended", updated_at=ready_at),
        package_root=package_root,
        logo_root=tmp_path / "logos",
        handoff_root=tmp_path / "handoff",
    )

    result = service.purge_package(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )

    assert result.status == "blocked"
    assert result.failure_code == "package_purge_integrity_mismatch"
    assert path.read_bytes() == b"replacement-package-bytes"
    assert result.purged_at is None


def test_source_cleanup_can_continue_after_package_was_strictly_purged(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    ready_at = datetime(2026, 9, 1, tzinfo=UTC)
    now = ready_at + timedelta(days=31)
    package_root = tmp_path / "packages"
    logo_root = tmp_path / "logos"
    execution, package, auth = _foundation(
        db_session,
        organization_id,
        package_root,
        ready_at=ready_at,
    )
    organization_dir = logo_root / str(organization_id)
    organization_dir.mkdir(parents=True)
    source = organization_dir / "late.png"
    source.write_bytes(b"late")
    item = _inventory_item(
        db_session,
        organization_id=organization_id,
        execution_id=execution.id,
        package_id=package.id,
        artifact_key="quote_template_logo:late",
        artifact_class="quote_template_logo",
        ownership_class="managed_product_artifact",
        owner_type="quote_template_version",
        owner_id=str(uuid4()),
        storage_kind="managed_file",
        cleanup_action="package_then_hard_delete",
        locator_json={"filename": "late.png"},
        content=b"late",
    )
    service, _ = _service(
        db_session,
        now=now,
        lifecycle=FakeLifecycle(
            status="suspended",
            updated_at=now - timedelta(days=31),
        ),
        package_root=package_root,
        logo_root=logo_root,
        handoff_root=tmp_path / "handoff",
    )
    service.purge_package(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )

    cleanup = service.purge_source_artifacts(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )

    assert cleanup.file_cleanup_complete is True
    assert item.cleanup_status == "purged"
    assert not source.exists()


def test_api_exposes_separate_source_and_package_purge_surfaces() -> None:
    paths = create_app().openapi()["paths"]
    prefix = "/api/v1/system-admin/organizations/{organization_id}/closure-executions/{execution_id}"
    assert f"{prefix}/closure-package/artifacts/purge" in paths
    assert "post" in paths[f"{prefix}/closure-package/artifacts/purge"]
    assert f"{prefix}/closure-package/purge" in paths
    assert "post" in paths[f"{prefix}/closure-package/purge"]
