from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.integrations.kyrox_core.audit_retention import (
    CoreAuditRetentionResult,
    CoreAuditRetentionUnavailableError,
)
from app.integrations.kyrox_core.ports import AuthContext
from app.main import create_app
from app.modules.organization_closure.application.evidence_retention import (
    OrganizationClosureEvidenceRetentionService,
    add_calendar_months,
)
from app.modules.organization_closure.application.service import (
    ClosureLifecyclePreconditionError,
    ClosureLifecycleUnavailableError,
)
from app.modules.organization_closure.infrastructure.evidence_retention_repository import (
    SqlAlchemyOrganizationClosureEvidenceRetentionRepository,
)
from app.modules.organization_closure.infrastructure.models import (
    OrganizationClosureArtifactInventoryModel,
    OrganizationClosureCredentialDispositionModel,
    OrganizationClosureCredentialEventModel,
    OrganizationClosureEventModel,
    OrganizationClosureExecutionModel,
    OrganizationClosureExportPlanModel,
    OrganizationClosurePackageModel,
)
from app.modules.organization_closure.infrastructure.product_cleanup_models import (
    OrganizationClosureProductCleanupItemModel,
)


class AllowAuthorization:
    def check_permission(self, **kwargs: object) -> bool:
        _ = kwargs
        return True


class FakeLifecycle:
    def __init__(self, organization_id, deleted_at: datetime | None) -> None:
        self.organization_id = organization_id
        self.deleted_at = deleted_at

    def get_snapshot(self, organization_id):
        assert organization_id == self.organization_id
        return SimpleNamespace(
            organization_id=organization_id,
            status="suspended",
            work_allowed=False,
            updated_at=datetime(2025, 1, 1, tzinfo=UTC),
            is_deleted=self.deleted_at is not None,
            deleted_at=self.deleted_at,
        )


class FakeCoreAuditRetention:
    def __init__(
        self,
        organization_id,
        deleted_at: datetime,
        deadline: datetime,
        *,
        counts: list[int] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.organization_id = organization_id
        self.deleted_at = deleted_at
        self.deadline = deadline
        self.counts = list(counts or [0])
        self.error = error
        self.calls: list[object] = []

    def purge(self, organization_id):
        self.calls.append(organization_id)
        if self.error is not None:
            raise self.error
        count = self.counts.pop(0) if self.counts else 0
        return CoreAuditRetentionResult(
            organization_id=self.organization_id,
            terminal_deleted_at=self.deleted_at,
            retention_deadline=self.deadline,
            purged_count=count,
        )


def _auth(organization_id):
    return AuthContext(
        user_id=uuid4(),
        email="platform-admin@example.com",
        session_id=uuid4(),
        organization_id=organization_id,
    )


def _seed_execution(db_session, organization_id, closed_at: datetime):
    now = closed_at
    execution = OrganizationClosureExecutionModel(
        id=uuid4(),
        organization_id=organization_id,
        idempotency_key=f"ol08-f-{uuid4()}",
        status="completed",
        current_phase="core_tombstone_completed",
        actor_user_id=uuid4(),
        actor_session_id=uuid4(),
        attempt_count=1,
        failure_code=None,
        failure_message=None,
        created_at=now - timedelta(days=60),
        updated_at=now,
        last_retry_at=None,
        closed_at=closed_at,
    )
    db_session.add(execution)
    db_session.flush()
    return execution


def _seed_full_evidence(db_session, organization_id, closed_at: datetime):
    execution = _seed_execution(db_session, organization_id, closed_at)
    now = closed_at
    actor_user_id = execution.actor_user_id
    actor_session_id = execution.actor_session_id

    db_session.add(
        OrganizationClosureEventModel(
            id=uuid4(),
            execution_id=execution.id,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            actor_session_id=actor_session_id,
            action="core_tombstone_completed",
            from_status="in_progress",
            to_status="completed",
            phase="core_tombstone_completed",
            created_at=closed_at,
        )
    )
    plan = OrganizationClosureExportPlanModel(
        id=uuid4(),
        organization_id=organization_id,
        closure_execution_id=execution.id,
        schema_version="ol08.export.v1",
        disposition="required",
        status="planned",
        manifest_json={"summary": "bounded"},
        manifest_digest="1" * 64,
        actor_user_id=actor_user_id,
        actor_session_id=actor_session_id,
        created_at=now - timedelta(days=45),
        updated_at=now - timedelta(days=45),
    )
    db_session.add(plan)
    db_session.flush()

    package = OrganizationClosurePackageModel(
        id=uuid4(),
        organization_id=organization_id,
        closure_execution_id=execution.id,
        export_plan_id=plan.id,
        schema_version="ol08.closure-package.v1",
        inventory_schema_version="ol08.artifact-inventory.v1",
        status="purged",
        storage_locator=f"{organization_id}/{execution.id}/purged.zip",
        manifest_json={"summary": "bounded"},
        manifest_digest="2" * 64,
        package_digest="3" * 64,
        byte_size=10,
        attempt_count=1,
        failure_code=None,
        failure_message=None,
        actor_user_id=actor_user_id,
        actor_session_id=actor_session_id,
        created_at=now - timedelta(days=45),
        updated_at=now - timedelta(days=1),
        ready_at=now - timedelta(days=40),
        integrity_verified_at=now - timedelta(days=40),
        expires_at=now - timedelta(days=10),
        purged_at=now - timedelta(days=9),
    )
    db_session.add(package)
    db_session.flush()

    db_session.add(
        OrganizationClosureArtifactInventoryModel(
            id=uuid4(),
            package_id=package.id,
            closure_execution_id=execution.id,
            organization_id=organization_id,
            inventory_schema_version=package.inventory_schema_version,
            artifact_key="managed:test",
            artifact_class="quote_template_logo",
            ownership_class="managed_product_artifact",
            owner_type="quote_template_version",
            owner_id=str(uuid4()),
            storage_kind="managed_file",
            package_disposition="included",
            cleanup_action="package_then_hard_delete",
            locator_json={"filename": "purged.png"},
            package_entry="artifacts/purged.png",
            byte_size=10,
            content_digest="4" * 64,
            cleanup_status="purged",
            cleanup_attempt_count=1,
            cleanup_failure_code=None,
            cleanup_failure_message=None,
            cleanup_last_attempt_at=now - timedelta(days=9),
            nonexistence_verified_at=now - timedelta(days=9),
            created_at=now - timedelta(days=40),
        )
    )

    disposition = OrganizationClosureCredentialDispositionModel(
        id=uuid4(),
        organization_id=organization_id,
        closure_execution_id=execution.id,
        email_account_id=uuid4(),
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
        actor_user_id=actor_user_id,
        actor_session_id=actor_session_id,
        outbound_disabled_at=now - timedelta(days=50),
        external_invalidated_at=now - timedelta(days=48),
        send_secret_purged_at=now - timedelta(days=48),
        created_at=now - timedelta(days=50),
        updated_at=now - timedelta(days=48),
        last_retry_at=None,
    )
    db_session.add(disposition)
    db_session.flush()
    db_session.add(
        OrganizationClosureCredentialEventModel(
            id=uuid4(),
            disposition_id=disposition.id,
            closure_execution_id=execution.id,
            organization_id=organization_id,
            email_account_id=disposition.email_account_id,
            actor_user_id=actor_user_id,
            actor_session_id=actor_session_id,
            action="external_invalidation_confirmed",
            from_status="operator_required",
            to_status="disposition_complete",
            evidence_code="bounded-proof",
            evidence_reference="ticket-reference",
            created_at=now - timedelta(days=48),
        )
    )
    db_session.add(
        OrganizationClosureProductCleanupItemModel(
            id=uuid4(),
            organization_id=organization_id,
            closure_execution_id=execution.id,
            policy_version="ol08.product-cleanup.v1",
            suspension_episode_updated_at=now - timedelta(days=60),
            class_key="customers",
            sequence=1,
            action="hard_delete",
            status="completed",
            attempt_count=1,
            before_count=1,
            deleted_count=1,
            remaining_count=0,
            failure_code=None,
            failure_message=None,
            actor_user_id=actor_user_id,
            actor_session_id=actor_session_id,
            created_at=now - timedelta(days=30),
            updated_at=now - timedelta(days=29),
            started_at=now - timedelta(days=30),
            completed_at=now - timedelta(days=29),
            last_attempt_at=now - timedelta(days=29),
        )
    )
    db_session.flush()
    return execution


def _service(db_session, organization_id, deleted_at, now, core):
    return OrganizationClosureEvidenceRetentionService(
        SqlAlchemyOrganizationClosureEvidenceRetentionRepository(db_session),
        AllowAuthorization(),
        FakeLifecycle(organization_id, deleted_at),
        core,
        now_provider=lambda: now,
    )


def _count(db_session, model, organization_id) -> int:
    return int(
        db_session.scalar(
            select(func.count())
            .select_from(model)
            .where(model.organization_id == organization_id)
        )
        or 0
    )


def test_calendar_retention_maps_leap_day_to_last_valid_day() -> None:
    assert add_calendar_months(datetime(2024, 2, 29, 8, tzinfo=UTC), 12) == datetime(
        2025,
        2,
        28,
        8,
        tzinfo=UTC,
    )


def test_retention_fails_closed_before_exact_deadline(db_session, organization_id) -> None:
    deleted_at = datetime(2025, 6, 15, 12, 30, 45, tzinfo=UTC)
    deadline = datetime(2026, 6, 15, 12, 30, 45, tzinfo=UTC)
    _seed_execution(db_session, organization_id, deleted_at)
    core = FakeCoreAuditRetention(organization_id, deleted_at, deadline)
    service = _service(
        db_session,
        organization_id,
        deleted_at,
        deadline - timedelta(microseconds=1),
        core,
    )

    with pytest.raises(ClosureLifecyclePreconditionError):
        service.purge(
            organization_id=organization_id,
            auth=_auth(organization_id),
            access_token="token",
        )

    assert core.calls == []
    assert _count(db_session, OrganizationClosureExecutionModel, organization_id) == 1


def test_core_audit_failure_leaves_all_local_evidence_untouched(db_session, organization_id) -> None:
    deleted_at = datetime(2025, 6, 15, tzinfo=UTC)
    deadline = datetime(2026, 6, 15, tzinfo=UTC)
    _seed_full_evidence(db_session, organization_id, deleted_at)
    core = FakeCoreAuditRetention(
        organization_id,
        deleted_at,
        deadline,
        error=CoreAuditRetentionUnavailableError("offline"),
    )
    service = _service(db_session, organization_id, deleted_at, deadline, core)

    with pytest.raises(ClosureLifecycleUnavailableError):
        service.purge(
            organization_id=organization_id,
            auth=_auth(organization_id),
            access_token="token",
        )

    assert _count(db_session, OrganizationClosureExecutionModel, organization_id) == 1
    assert _count(db_session, OrganizationClosureCredentialEventModel, organization_id) == 1
    assert _count(db_session, OrganizationClosureArtifactInventoryModel, organization_id) == 1


def test_terminal_clock_mismatch_fails_before_core_purge(db_session, organization_id) -> None:
    core_deleted_at = datetime(2025, 6, 15, tzinfo=UTC)
    local_closed_at = core_deleted_at + timedelta(seconds=1)
    deadline = datetime(2026, 6, 15, tzinfo=UTC)
    _seed_execution(db_session, organization_id, local_closed_at)
    core = FakeCoreAuditRetention(organization_id, core_deleted_at, deadline)
    service = _service(db_session, organization_id, core_deleted_at, deadline, core)

    with pytest.raises(ClosureLifecyclePreconditionError):
        service.purge(
            organization_id=organization_id,
            auth=_auth(organization_id),
            access_token="token",
        )

    assert core.calls == []


def test_exact_deadline_purges_complete_fk_graph_and_repeat_is_idempotent(
    db_session,
    organization_id,
    other_organization_id,
) -> None:
    deleted_at = datetime(2025, 6, 15, 12, 30, 45, tzinfo=UTC)
    deadline = datetime(2026, 6, 15, 12, 30, 45, tzinfo=UTC)
    _seed_full_evidence(db_session, organization_id, deleted_at)
    _seed_execution(db_session, other_organization_id, deleted_at)
    core = FakeCoreAuditRetention(
        organization_id,
        deleted_at,
        deadline,
        counts=[4, 0],
    )
    service = _service(db_session, organization_id, deleted_at, deadline, core)

    first = service.purge(
        organization_id=organization_id,
        auth=_auth(organization_id),
        access_token="token",
    )
    second = service.purge(
        organization_id=organization_id,
        auth=_auth(organization_id),
        access_token="token",
    )

    assert first.core_audit_purged_count == 4
    assert first.local_purge_counts.total == 8
    assert second.core_audit_purged_count == 0
    assert second.local_purge_counts.total == 0
    assert core.calls == [organization_id, organization_id]

    for model in (
        OrganizationClosureCredentialEventModel,
        OrganizationClosureCredentialDispositionModel,
        OrganizationClosureArtifactInventoryModel,
        OrganizationClosurePackageModel,
        OrganizationClosureExportPlanModel,
        OrganizationClosureProductCleanupItemModel,
        OrganizationClosureEventModel,
        OrganizationClosureExecutionModel,
    ):
        assert _count(db_session, model, organization_id) == 0
    assert _count(db_session, OrganizationClosureExecutionModel, other_organization_id) == 1


def test_api_surface_exposes_system_retention_purge_only() -> None:
    paths = create_app().openapi()["paths"]
    path = "/api/v1/system-admin/organizations/{organization_id}/closure-retention/purge"

    assert path in paths
    assert "post" in paths[path]
