from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from app.integrations.kyrox_core.lifecycle import (
    OrganizationLifecycleSnapshot,
    OrganizationLifecycleUnavailableError,
)
from app.integrations.kyrox_core.ports import AuthContext
from app.integrations.kyrox_core.tombstone import (
    CoreOrganizationTombstoneUnavailableError,
)
from app.modules.organization_closure.application.closure_package import PACKAGE_SCHEMA_VERSION
from app.modules.organization_closure.application.export_planner import EXPORT_SCHEMA_VERSION
from app.modules.organization_closure.application.product_cleanup import (
    PRODUCT_CLEANUP_PLAN,
    PRODUCT_CLEANUP_POLICY_VERSION,
)
from app.modules.organization_closure.application.service import (
    ClosureExecutionConflictError,
    ClosureLifecyclePreconditionError,
    ClosureLifecycleUnavailableError,
    OrganizationClosureService,
)
from app.modules.organization_closure.application.terminal_closure import (
    PHASE_CORE_TOMBSTONE_COMPLETED,
    STATUS_COMPLETED,
    OrganizationClosureTerminalService,
)
from app.modules.organization_closure.infrastructure.models import (
    OrganizationClosureArtifactInventoryModel,
    OrganizationClosureCredentialDispositionModel,
    OrganizationClosureEventModel,
    OrganizationClosureExecutionModel,
    OrganizationClosureExportPlanModel,
    OrganizationClosurePackageModel,
)
from app.modules.organization_closure.infrastructure.product_cleanup_models import (
    OrganizationClosureProductCleanupItemModel,
)
from app.modules.organization_closure.infrastructure.product_cleanup_repository import (
    SqlAlchemyOrganizationClosureProductCleanupRepository,
)
from app.modules.organization_closure.infrastructure.repository import (
    SqlAlchemyOrganizationClosureRepository,
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
        organization_id: UUID,
        updated_at: datetime,
        status: str = "suspended",
        is_deleted: bool = False,
        deleted_at: datetime | None = None,
    ) -> None:
        self.organization_id = organization_id
        self.updated_at = updated_at
        self.status = status
        self.is_deleted = is_deleted
        self.deleted_at = deleted_at
        self.fail_next = False

    def get_snapshot(self, organization_id: UUID) -> OrganizationLifecycleSnapshot:
        assert organization_id == self.organization_id
        if self.fail_next:
            self.fail_next = False
            raise OrganizationLifecycleUnavailableError("offline")
        return OrganizationLifecycleSnapshot(
            organization_id=organization_id,
            status=self.status,
            work_allowed=self.status == "active" and not self.is_deleted,
            updated_at=self.updated_at,
            is_deleted=self.is_deleted,
            deleted_at=self.deleted_at,
        )

    def mark_deleted(self, deleted_at: datetime) -> None:
        self.is_deleted = True
        self.deleted_at = deleted_at


class RecordingTombstone:
    def __init__(
        self,
        lifecycle: FakeLifecycle,
        *,
        deleted_at: datetime,
        unavailable: bool = False,
        fail_post_delete_read: bool = False,
    ) -> None:
        self.lifecycle = lifecycle
        self.deleted_at = deleted_at
        self.unavailable = unavailable
        self.fail_post_delete_read = fail_post_delete_read
        self.calls: list[dict[str, object]] = []

    def delete_suspended_episode(self, **kwargs: object) -> None:
        self.calls.append(kwargs)
        if self.unavailable:
            raise CoreOrganizationTombstoneUnavailableError("offline")
        self.lifecycle.mark_deleted(self.deleted_at)
        if self.fail_post_delete_read:
            self.lifecycle.fail_next = True
            self.fail_post_delete_read = False


class RecordingAudit:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def record_event(self, **kwargs: object) -> None:
        self.events.append(kwargs)


def _auth(organization_id: UUID) -> AuthContext:
    return AuthContext(
        user_id=uuid4(),
        email="platform-admin@example.com",
        session_id=uuid4(),
        organization_id=organization_id,
    )


def _seed_terminal_evidence(
    db_session,
    *,
    organization_id: UUID,
    package_root: Path,
    episode: datetime,
    now: datetime,
):
    auth = _auth(organization_id)
    execution = OrganizationClosureExecutionModel(
        id=uuid4(),
        organization_id=organization_id,
        idempotency_key=f"ol08-07-{uuid4()}",
        status="in_progress",
        current_phase="product_data_cleanup_complete",
        actor_user_id=auth.user_id,
        actor_session_id=auth.session_id,
        attempt_count=1,
        failure_code=None,
        failure_message=None,
        created_at=now - timedelta(days=40),
        updated_at=now,
        last_retry_at=None,
        closed_at=None,
    )
    db_session.add(execution)
    db_session.flush()

    plan = OrganizationClosureExportPlanModel(
        id=uuid4(),
        organization_id=organization_id,
        closure_execution_id=execution.id,
        schema_version=EXPORT_SCHEMA_VERSION,
        disposition="required",
        status="planned",
        manifest_json={},
        manifest_digest="1" * 64,
        actor_user_id=auth.user_id,
        actor_session_id=auth.session_id,
        created_at=now - timedelta(days=35),
        updated_at=now - timedelta(days=35),
    )
    db_session.add(plan)
    db_session.flush()

    package = OrganizationClosurePackageModel(
        id=uuid4(),
        organization_id=organization_id,
        closure_execution_id=execution.id,
        export_plan_id=plan.id,
        schema_version=PACKAGE_SCHEMA_VERSION,
        inventory_schema_version="ol08.artifact-inventory.v1",
        status="purged",
        storage_locator=(
            Path(str(organization_id)) / str(execution.id) / f"{uuid4()}.zip"
        ).as_posix(),
        manifest_json={},
        manifest_digest="2" * 64,
        package_digest="3" * 64,
        byte_size=123,
        attempt_count=1,
        failure_code=None,
        failure_message=None,
        actor_user_id=auth.user_id,
        actor_session_id=auth.session_id,
        created_at=now - timedelta(days=35),
        updated_at=now,
        ready_at=now - timedelta(days=32),
        integrity_verified_at=now - timedelta(days=32),
        expires_at=now - timedelta(days=2),
        purged_at=now - timedelta(days=1),
    )
    db_session.add(package)

    inventory = OrganizationClosureArtifactInventoryModel(
        id=uuid4(),
        package_id=package.id,
        closure_execution_id=execution.id,
        organization_id=organization_id,
        inventory_schema_version=package.inventory_schema_version,
        artifact_key="managed-logo:test",
        artifact_class="quote_template_logo",
        ownership_class="managed_product_artifact",
        owner_type="quote_template_version",
        owner_id=str(uuid4()),
        storage_kind="managed_file",
        package_disposition="included",
        cleanup_action="package_then_hard_delete",
        locator_json={"filename": "logo.png"},
        package_entry="artifacts/quote-template-logos/logo.png",
        byte_size=10,
        content_digest="4" * 64,
        cleanup_status="purged",
        cleanup_attempt_count=1,
        cleanup_failure_code=None,
        cleanup_failure_message=None,
        cleanup_last_attempt_at=now - timedelta(days=1),
        nonexistence_verified_at=now - timedelta(days=1),
        created_at=now - timedelta(days=32),
    )
    db_session.add(inventory)

    for spec in PRODUCT_CLEANUP_PLAN:
        db_session.add(
            OrganizationClosureProductCleanupItemModel(
                id=uuid4(),
                organization_id=organization_id,
                closure_execution_id=execution.id,
                policy_version=PRODUCT_CLEANUP_POLICY_VERSION,
                suspension_episode_updated_at=episode,
                class_key=spec.key,
                sequence=spec.sequence,
                action="hard_delete",
                status="completed",
                attempt_count=1,
                before_count=0,
                deleted_count=0,
                remaining_count=0,
                failure_code=None,
                failure_message=None,
                actor_user_id=auth.user_id,
                actor_session_id=auth.session_id,
                created_at=now - timedelta(days=2),
                updated_at=now - timedelta(days=1),
                started_at=now - timedelta(days=2),
                completed_at=now - timedelta(days=1),
                last_attempt_at=now - timedelta(days=1),
            )
        )
    db_session.flush()
    assert not (package_root / package.storage_locator).exists()
    return execution, package, inventory, auth


def _service(
    db_session,
    *,
    lifecycle: FakeLifecycle,
    tombstone: RecordingTombstone,
    package_root: Path,
    now: datetime,
):
    audit = RecordingAudit()
    service = OrganizationClosureTerminalService(
        SqlAlchemyOrganizationClosureProductCleanupRepository(db_session),
        SqlAlchemyOrganizationClosureRepository(db_session),
        FakeAuthorization(),
        lifecycle,
        tombstone,
        audit,
        package_storage_root=package_root,
        now_provider=lambda: now,
    )
    return service, audit


def _event_count(db_session, execution_id: UUID) -> int:
    return int(
        db_session.scalar(
            select(func.count())
            .select_from(OrganizationClosureEventModel)
            .where(
                OrganizationClosureEventModel.execution_id == execution_id,
                OrganizationClosureEventModel.action == "core_tombstone_completed",
            )
        )
        or 0
    )


def test_terminal_finalize_tombstones_exact_episode_and_mirrors_core_timestamp(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    now = datetime(2026, 10, 20, 12, tzinfo=UTC)
    episode = datetime(2026, 9, 1, 8, 15, 30, 123456, tzinfo=UTC)
    core_deleted_at = datetime(2026, 10, 20, 12, 0, 1, 654321, tzinfo=UTC)
    package_root = tmp_path / "closure-packages"
    execution, _, _, auth = _seed_terminal_evidence(
        db_session,
        organization_id=organization_id,
        package_root=package_root,
        episode=episode,
        now=now,
    )
    lifecycle = FakeLifecycle(organization_id=organization_id, updated_at=episode)
    tombstone = RecordingTombstone(lifecycle, deleted_at=core_deleted_at)
    service, audit = _service(
        db_session,
        lifecycle=lifecycle,
        tombstone=tombstone,
        package_root=package_root,
        now=now,
    )

    result = service.finalize(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )

    assert result.status == STATUS_COMPLETED
    assert result.current_phase == PHASE_CORE_TOMBSTONE_COMPLETED
    assert result.closed_at == core_deleted_at
    assert tombstone.calls == [
        {
            "organization_id": organization_id,
            "expected_suspension_updated_at": episode,
            "access_token": "token",
        }
    ]
    assert _event_count(db_session, execution.id) == 1
    assert audit.events[-1]["action"] == "organization_closure.completed"

    repeated = service.finalize(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )
    assert repeated.id == execution.id
    assert repeated.closed_at == core_deleted_at
    assert len(tombstone.calls) == 1
    assert _event_count(db_session, execution.id) == 1


def test_terminal_finalize_reconciles_core_tombstone_after_restart_without_delete(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    now = datetime(2026, 10, 20, 12, tzinfo=UTC)
    episode = datetime(2026, 9, 1, 8, tzinfo=UTC)
    core_deleted_at = datetime(2026, 10, 20, 11, 59, tzinfo=UTC)
    package_root = tmp_path / "closure-packages"
    execution, _, _, auth = _seed_terminal_evidence(
        db_session,
        organization_id=organization_id,
        package_root=package_root,
        episode=episode,
        now=now,
    )
    lifecycle = FakeLifecycle(
        organization_id=organization_id,
        updated_at=episode,
        is_deleted=True,
        deleted_at=core_deleted_at,
    )
    tombstone = RecordingTombstone(lifecycle, deleted_at=core_deleted_at)
    service, _ = _service(
        db_session,
        lifecycle=lifecycle,
        tombstone=tombstone,
        package_root=package_root,
        now=now,
    )

    result = service.finalize(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )

    assert result.status == STATUS_COMPLETED
    assert result.closed_at == core_deleted_at
    assert tombstone.calls == []
    assert _event_count(db_session, execution.id) == 1


def test_post_delete_authority_outage_leaves_fair_open_then_restart_reconciles(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    now = datetime(2026, 10, 20, 12, tzinfo=UTC)
    episode = datetime(2026, 9, 1, 8, tzinfo=UTC)
    core_deleted_at = datetime(2026, 10, 20, 12, 0, 2, tzinfo=UTC)
    package_root = tmp_path / "closure-packages"
    execution, _, _, auth = _seed_terminal_evidence(
        db_session,
        organization_id=organization_id,
        package_root=package_root,
        episode=episode,
        now=now,
    )
    lifecycle = FakeLifecycle(organization_id=organization_id, updated_at=episode)
    tombstone = RecordingTombstone(
        lifecycle,
        deleted_at=core_deleted_at,
        fail_post_delete_read=True,
    )
    service, _ = _service(
        db_session,
        lifecycle=lifecycle,
        tombstone=tombstone,
        package_root=package_root,
        now=now,
    )

    with pytest.raises(ClosureLifecycleUnavailableError):
        service.finalize(
            organization_id=organization_id,
            execution_id=execution.id,
            auth=auth,
            access_token="token",
        )
    db_session.refresh(execution)
    assert execution.status == "in_progress"
    assert execution.closed_at is None

    result = service.finalize(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )
    assert result.status == STATUS_COMPLETED
    assert result.closed_at == core_deleted_at
    assert len(tombstone.calls) == 1


def test_terminal_finalize_blocks_until_package_is_strictly_purged(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    now = datetime(2026, 10, 20, 12, tzinfo=UTC)
    episode = datetime(2026, 9, 1, 8, tzinfo=UTC)
    package_root = tmp_path / "closure-packages"
    execution, package, _, auth = _seed_terminal_evidence(
        db_session,
        organization_id=organization_id,
        package_root=package_root,
        episode=episode,
        now=now,
    )
    package.status = "expired"
    package.purged_at = None
    db_session.flush()
    lifecycle = FakeLifecycle(organization_id=organization_id, updated_at=episode)
    tombstone = RecordingTombstone(lifecycle, deleted_at=now)
    service, _ = _service(
        db_session,
        lifecycle=lifecycle,
        tombstone=tombstone,
        package_root=package_root,
        now=now,
    )

    with pytest.raises(ClosureExecutionConflictError):
        service.finalize(
            organization_id=organization_id,
            execution_id=execution.id,
            auth=auth,
            access_token="token",
        )
    assert tombstone.calls == []


def test_terminal_finalize_blocks_incomplete_cleanup_and_credentials(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    now = datetime(2026, 10, 20, 12, tzinfo=UTC)
    episode = datetime(2026, 9, 1, 8, tzinfo=UTC)
    package_root = tmp_path / "closure-packages"
    execution, _, _, auth = _seed_terminal_evidence(
        db_session,
        organization_id=organization_id,
        package_root=package_root,
        episode=episode,
        now=now,
    )
    first_item = db_session.scalar(
        select(OrganizationClosureProductCleanupItemModel)
        .where(OrganizationClosureProductCleanupItemModel.closure_execution_id == execution.id)
        .order_by(OrganizationClosureProductCleanupItemModel.sequence.asc())
    )
    assert first_item is not None
    first_item.status = "pending"
    first_item.completed_at = None
    db_session.flush()

    lifecycle = FakeLifecycle(organization_id=organization_id, updated_at=episode)
    tombstone = RecordingTombstone(lifecycle, deleted_at=now)
    service, _ = _service(
        db_session,
        lifecycle=lifecycle,
        tombstone=tombstone,
        package_root=package_root,
        now=now,
    )
    with pytest.raises(ClosureExecutionConflictError):
        service.finalize(
            organization_id=organization_id,
            execution_id=execution.id,
            auth=auth,
            access_token="token",
        )
    assert tombstone.calls == []

    first_item.status = "completed"
    first_item.completed_at = now - timedelta(days=1)
    db_session.add(
        OrganizationClosureCredentialDispositionModel(
            id=uuid4(),
            organization_id=organization_id,
            closure_execution_id=execution.id,
            email_account_id=uuid4(),
            account_type="smtp",
            provider_key=None,
            capability_class="operator_required",
            external_invalidation_state="operator_required",
            target_verification_state="not_required",
            external_credential_id=None,
            status="operator_required",
            signing_secret_retained=False,
            attempt_count=1,
            failure_code=None,
            failure_message=None,
            actor_user_id=auth.user_id,
            actor_session_id=auth.session_id,
            outbound_disabled_at=now - timedelta(days=40),
            external_invalidated_at=None,
            send_secret_purged_at=None,
            created_at=now - timedelta(days=40),
            updated_at=now - timedelta(days=40),
            last_retry_at=None,
        )
    )
    db_session.flush()
    with pytest.raises(ClosureExecutionConflictError):
        service.finalize(
            organization_id=organization_id,
            execution_id=execution.id,
            auth=auth,
            access_token="token",
        )
    assert tombstone.calls == []


def test_terminal_finalize_rejects_lifecycle_episode_drift(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    now = datetime(2026, 10, 20, 12, tzinfo=UTC)
    episode = datetime(2026, 9, 1, 8, tzinfo=UTC)
    package_root = tmp_path / "closure-packages"
    execution, _, _, auth = _seed_terminal_evidence(
        db_session,
        organization_id=organization_id,
        package_root=package_root,
        episode=episode,
        now=now,
    )
    lifecycle = FakeLifecycle(
        organization_id=organization_id,
        updated_at=episode + timedelta(seconds=1),
    )
    tombstone = RecordingTombstone(lifecycle, deleted_at=now)
    service, _ = _service(
        db_session,
        lifecycle=lifecycle,
        tombstone=tombstone,
        package_root=package_root,
        now=now,
    )

    with pytest.raises(ClosureLifecyclePreconditionError):
        service.finalize(
            organization_id=organization_id,
            execution_id=execution.id,
            auth=auth,
            access_token="token",
        )
    assert tombstone.calls == []


def test_closure_start_rejects_already_tombstoned_organization(
    db_session,
    organization_id,
) -> None:
    now = datetime(2026, 10, 20, 12, tzinfo=UTC)
    lifecycle = FakeLifecycle(
        organization_id=organization_id,
        updated_at=now - timedelta(days=40),
        is_deleted=True,
        deleted_at=now,
    )
    service = OrganizationClosureService(
        SqlAlchemyOrganizationClosureRepository(db_session),
        FakeAuthorization(),
        lifecycle,
        RecordingAudit(),
    )

    with pytest.raises(ClosureLifecyclePreconditionError):
        service.start(
            organization_id=organization_id,
            idempotency_key="cannot-reopen-after-tombstone",
            auth=_auth(organization_id),
            access_token="token",
        )
