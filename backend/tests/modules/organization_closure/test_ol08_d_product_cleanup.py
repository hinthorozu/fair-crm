from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.integrations.kyrox_core.ports import AuthContext
from app.modules.email_accounts.infrastructure.persistence.models import (
    EmailAccountModel,
    EmailAccountSmtpConfigModel,
)
from app.modules.imports.infrastructure.persistence.models import ImportBatchModel
from app.modules.mail_send_operations.infrastructure.persistence.models import MailSendOperationModel
from app.modules.organization_closure.application.closure_package import (
    INVENTORY_SCHEMA_VERSION,
    PACKAGE_SCHEMA_VERSION,
)
from app.modules.organization_closure.application.export_planner import EXPORT_SCHEMA_VERSION
from app.modules.organization_closure.application.product_cleanup import (
    PRODUCT_CLEANUP_PLAN,
    OrganizationClosureProductCleanupService,
)
from app.modules.organization_closure.application.service import (
    ClosureExecutionConflictError,
    ClosureLifecyclePreconditionError,
)
from app.modules.organization_closure.infrastructure.models import (
    OrganizationClosureArtifactInventoryModel,
    OrganizationClosureCredentialDispositionModel,
    OrganizationClosureExecutionModel,
    OrganizationClosureExportPlanModel,
    OrganizationClosurePackageModel,
)
from app.modules.organization_closure.infrastructure.package_storage import (
    canonical_manifest_bytes,
    write_immutable_package,
)
from app.modules.organization_closure.infrastructure.product_cleanup_repository import (
    SqlAlchemyOrganizationClosureProductCleanupRepository,
)
from app.modules.system_admin.infrastructure.persistence.models import SystemDataOperationRunModel


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
        updated_at: datetime,
        status: str = "suspended",
        is_deleted: bool = False,
    ) -> None:
        self.updated_at = updated_at
        self.status = status
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


def _foundation(db_session, organization_id, package_root: Path, *, ready_at: datetime):
    auth = _auth(organization_id)
    execution = OrganizationClosureExecutionModel(
        id=uuid4(),
        organization_id=organization_id,
        idempotency_key=f"ol08-d-{uuid4()}",
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


def _service(
    db_session,
    *,
    now: datetime,
    lifecycle: FakeLifecycle,
    package_root: Path,
):
    audit = RecordingAudit()
    service = OrganizationClosureProductCleanupService(
        SqlAlchemyOrganizationClosureProductCleanupRepository(db_session),
        FakeAuthorization(),
        lifecycle,
        audit,
        package_storage_root=package_root,
        now_provider=lambda: now,
    )
    return service, audit


def _reconcile(service, organization_id, execution_id, auth):
    return service.reconcile(
        organization_id=organization_id,
        execution_id=execution_id,
        auth=auth,
        access_token="token",
    )


def _count(db_session, model, organization_id) -> int:
    return int(
        db_session.scalar(
            select(func.count()).select_from(model).where(
                model.organization_id == organization_id
            )
        )
        or 0
    )


def _add_mail_send(db_session, organization_id, *, recipient: str):
    now = datetime(2026, 1, 1, tzinfo=UTC)
    row = MailSendOperationModel(
        id=uuid4(),
        organization_id=organization_id,
        source_type="fair_bulk_email",
        status="sent",
        priority=99,
        recipient_email=recipient,
        subject="subject",
        body_html="business content",
        retry_count=0,
        max_retry_count=3,
        operation_logs=[],
        created_at=now,
        updated_at=now,
    )
    db_session.add(row)
    db_session.flush()
    return row


def _add_import_batch(db_session, organization_id, *, content: bytes):
    now = datetime(2026, 1, 1, tzinfo=UTC)
    row = ImportBatchModel(
        id=uuid4(),
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
    db_session.add(row)
    db_session.flush()
    return row


def _add_import_inventory(
    db_session,
    *,
    organization_id,
    execution_id,
    package_id,
    batch_id,
    content: bytes,
):
    now = datetime(2026, 1, 1, tzinfo=UTC)
    item = OrganizationClosureArtifactInventoryModel(
        id=uuid4(),
        package_id=package_id,
        closure_execution_id=execution_id,
        organization_id=organization_id,
        inventory_schema_version=INVENTORY_SCHEMA_VERSION,
        artifact_key=f"import_upload:{batch_id}",
        artifact_class="import_upload",
        ownership_class="managed_product_artifact",
        owner_type="import_batch",
        owner_id=str(batch_id),
        storage_kind="embedded_database_bytes",
        package_disposition="included",
        cleanup_action="package_then_hard_delete",
        locator_json={"batch_id": str(batch_id), "field": "stored_file_content"},
        package_entry=f"artifacts/imports/{batch_id}.bin",
        byte_size=len(content),
        content_digest=sha256(content).hexdigest(),
        cleanup_status="relational_delete_required",
        cleanup_attempt_count=1,
        cleanup_failure_code=None,
        cleanup_failure_message=None,
        cleanup_last_attempt_at=now,
        nonexistence_verified_at=None,
        created_at=now,
    )
    db_session.add(item)
    db_session.flush()
    return item


def _add_terminal_credential(db_session, organization_id, execution_id, account_id):
    now = datetime(2026, 1, 1, tzinfo=UTC)
    item = OrganizationClosureCredentialDispositionModel(
        id=uuid4(),
        organization_id=organization_id,
        closure_execution_id=execution_id,
        email_account_id=account_id,
        account_type="smtp",
        provider_key=None,
        capability_class="operator_required",
        external_invalidation_state="confirmed",
        target_verification_state="not_required",
        external_credential_id=None,
        status="disposition_complete",
        signing_secret_retained=False,
        attempt_count=1,
        failure_code=None,
        failure_message=None,
        actor_user_id=uuid4(),
        actor_session_id=uuid4(),
        outbound_disabled_at=now,
        external_invalidated_at=now,
        send_secret_purged_at=now,
        created_at=now,
        updated_at=now,
        last_retry_at=None,
    )
    db_session.add(item)
    db_session.flush()
    return item


def test_product_cleanup_blocks_before_exact_30_day_grace_without_mutation(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    now = datetime(2026, 4, 1, tzinfo=UTC)
    package_root = tmp_path / "packages"
    execution, _, auth = _foundation(
        db_session,
        organization_id,
        package_root,
        ready_at=now - timedelta(days=1),
    )
    _add_mail_send(db_session, organization_id, recipient="target@example.com")
    service, _ = _service(
        db_session,
        now=now,
        lifecycle=FakeLifecycle(updated_at=now - timedelta(days=29, hours=23)),
        package_root=package_root,
    )

    with pytest.raises(ClosureLifecyclePreconditionError):
        _reconcile(service, organization_id, execution.id, auth)

    assert _count(db_session, MailSendOperationModel, organization_id) == 1
    assert service.get(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    ).items == ()


def test_reconcile_deletes_only_one_class_and_never_crosses_organization(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    now = datetime(2026, 5, 1, tzinfo=UTC)
    package_root = tmp_path / "packages"
    execution, _, auth = _foundation(
        db_session,
        organization_id,
        package_root,
        ready_at=now - timedelta(days=5),
    )
    foreign_org = uuid4()
    _add_mail_send(db_session, organization_id, recipient="target@example.com")
    foreign = _add_mail_send(db_session, foreign_org, recipient="foreign@example.com")
    service, audit = _service(
        db_session,
        now=now,
        lifecycle=FakeLifecycle(updated_at=now - timedelta(days=31)),
        package_root=package_root,
    )

    result = _reconcile(service, organization_id, execution.id, auth)

    assert result.processed_class_key == "communication_history"
    assert result.completed == 1
    assert result.pending == len(PRODUCT_CLEANUP_PLAN) - 1
    assert result.cleanup_complete is False
    assert _count(db_session, MailSendOperationModel, organization_id) == 0
    assert db_session.get(MailSendOperationModel, foreign.id) is not None
    assert any(
        event.get("action") == "organization_closure.product_cleanup.class_completed"
        for event in audit.events
    )


def test_new_suspension_episode_blocks_resume_before_next_irreversible_class(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    now = datetime(2026, 6, 30, tzinfo=UTC)
    package_root = tmp_path / "packages"
    execution, _, auth = _foundation(
        db_session,
        organization_id,
        package_root,
        ready_at=now - timedelta(days=5),
    )
    first_service, _ = _service(
        db_session,
        now=now,
        lifecycle=FakeLifecycle(updated_at=now - timedelta(days=40)),
        package_root=package_root,
    )
    first = _reconcile(first_service, organization_id, execution.id, auth)
    assert first.processed_class_key == "communication_history"

    new_episode_service, _ = _service(
        db_session,
        now=now,
        lifecycle=FakeLifecycle(updated_at=now - timedelta(days=31)),
        package_root=package_root,
    )
    with pytest.raises(ClosureLifecyclePreconditionError):
        _reconcile(new_episode_service, organization_id, execution.id, auth)

    evidence = new_episode_service.get(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )
    assert evidence.completed == 1
    assert evidence.items[1].class_key == "operations"
    assert evidence.items[1].status == "pending"


def test_unregistered_system_data_operation_output_artifact_fails_closed(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    now = datetime(2026, 7, 15, tzinfo=UTC)
    package_root = tmp_path / "packages"
    execution, _, auth = _foundation(
        db_session,
        organization_id,
        package_root,
        ready_at=now - timedelta(days=5),
    )
    run = SystemDataOperationRunModel(
        id=uuid4(),
        organization_id=organization_id,
        operation_key="duplicate_analysis",
        status="completed",
        started_by=uuid4(),
        started_by_email="admin@example.com",
        started_at=now - timedelta(hours=1),
        completed_at=now,
        duration_seconds=1,
        result="success",
        error_message=None,
        stdout_text="diagnostic product output",
        output_files_json=[{"path": "/tmp/persistent.xlsx"}],
        summary_json={},
        created_at=now,
        updated_at=now,
    )
    db_session.add(run)
    db_session.flush()
    service, _ = _service(
        db_session,
        now=now,
        lifecycle=FakeLifecycle(updated_at=now - timedelta(days=31)),
        package_root=package_root,
    )

    for expected in ("communication_history", "operations", "scraper_relational_state"):
        assert _reconcile(service, organization_id, execution.id, auth).processed_class_key == expected
    blocked = _reconcile(service, organization_id, execution.id, auth)

    assert blocked.processed_class_key == "system_data_operations"
    assert blocked.blocked == 1
    item = next(item for item in blocked.items if item.class_key == "system_data_operations")
    assert item.status == "blocked"
    assert item.failure_code == "unregistered_system_data_operation_artifact"
    assert db_session.get(SystemDataOperationRunModel, run.id) is not None


def test_import_embedded_bytes_are_destroyed_only_with_authorized_relational_delete(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    now = datetime(2026, 8, 1, tzinfo=UTC)
    package_root = tmp_path / "packages"
    execution, package, auth = _foundation(
        db_session,
        organization_id,
        package_root,
        ready_at=now - timedelta(days=5),
    )
    content = b"embedded upload bytes"
    batch = _add_import_batch(db_session, organization_id, content=content)
    inventory = _add_import_inventory(
        db_session,
        organization_id=organization_id,
        execution_id=execution.id,
        package_id=package.id,
        batch_id=batch.id,
        content=content,
    )
    service, _ = _service(
        db_session,
        now=now,
        lifecycle=FakeLifecycle(updated_at=now - timedelta(days=31)),
        package_root=package_root,
    )

    for _ in range(5):
        result = _reconcile(service, organization_id, execution.id, auth)
        assert result.blocked == 0
    result = _reconcile(service, organization_id, execution.id, auth)

    assert result.processed_class_key == "imports_data_integration"
    assert db_session.get(ImportBatchModel, batch.id) is None
    db_session.refresh(inventory)
    assert inventory.cleanup_status == "already_absent"
    assert inventory.nonexistence_verified_at == now


def test_email_account_delete_requires_terminal_credential_evidence_and_retains_scalar_proof(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    now = datetime(2026, 9, 1, tzinfo=UTC)
    package_root = tmp_path / "packages"
    execution, _, auth = _foundation(
        db_session,
        organization_id,
        package_root,
        ready_at=now - timedelta(days=5),
    )
    account = EmailAccountModel(
        id=uuid4(),
        organization_id=organization_id,
        name="Closure SMTP",
        account_type="smtp",
        provider_key=None,
        from_email="sender@example.com",
        from_name=None,
        is_default=False,
        is_active=False,
        max_delivery_attempts=3,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    config = EmailAccountSmtpConfigModel(
        email_account_id=account.id,
        host="smtp.example.com",
        port=587,
        username="sender@example.com",
        password=None,
        encryption_type="starttls",
    )
    db_session.add_all([account, config])
    db_session.flush()
    service, _ = _service(
        db_session,
        now=now,
        lifecycle=FakeLifecycle(updated_at=now - timedelta(days=31)),
        package_root=package_root,
    )

    with pytest.raises(ClosureExecutionConflictError):
        _reconcile(service, organization_id, execution.id, auth)
    assert db_session.get(EmailAccountModel, account.id) is not None

    disposition = _add_terminal_credential(
        db_session,
        organization_id,
        execution.id,
        account.id,
    )
    final = None
    for _ in PRODUCT_CLEANUP_PLAN:
        final = _reconcile(service, organization_id, execution.id, auth)
        assert final.blocked == 0

    assert final is not None
    assert final.processed_class_key == "email_accounts"
    assert final.cleanup_complete is True
    assert db_session.get(EmailAccountModel, account.id) is None
    assert db_session.get(EmailAccountSmtpConfigModel, account.id) is None
    retained = db_session.get(OrganizationClosureCredentialDispositionModel, disposition.id)
    assert retained is not None
    assert retained.email_account_id == account.id
