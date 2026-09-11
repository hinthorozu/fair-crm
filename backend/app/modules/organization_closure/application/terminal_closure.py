from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Callable
from uuid import UUID, uuid4

from app.integrations.kyrox_core.lifecycle import (
    OrganizationLifecycleGuard,
    OrganizationLifecycleSnapshot,
    OrganizationLifecycleUnavailableError,
)
from app.integrations.kyrox_core.ports import AuditPort, AuthContext, AuthorizationPort
from app.integrations.kyrox_core.tombstone import (
    CoreOrganizationTombstoneConflictError,
    CoreOrganizationTombstoneUnavailableError,
    OrganizationTombstonePort,
)
from app.modules.organization_closure.application.closure_package import PACKAGE_SCHEMA_VERSION
from app.modules.organization_closure.application.credential_disposition import (
    STATUS_DISPOSITION_COMPLETE,
)
from app.modules.organization_closure.application.product_cleanup import (
    PRODUCT_CLEANUP_PLAN,
    PRODUCT_CLEANUP_POLICY_VERSION,
)
from app.modules.organization_closure.application.service import (
    STATUS_IN_PROGRESS,
    SYSTEM_CLOSURE_PERMISSION,
    ClosureAuthorizationUnavailableError,
    ClosureExecutionConflictError,
    ClosureExecutionNotFoundError,
    ClosureLifecyclePreconditionError,
    ClosureLifecycleUnavailableError,
    ClosurePermissionDeniedError,
)
from app.modules.organization_closure.infrastructure.models import (
    OrganizationClosureArtifactInventoryModel,
    OrganizationClosureEventModel,
    OrganizationClosureExecutionModel,
    OrganizationClosurePackageModel,
)
from app.modules.organization_closure.infrastructure.package_storage import (
    DEFAULT_CLOSURE_PACKAGE_ROOT,
    ClosurePackageStorageError,
    resolve_stored_locator,
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

STATUS_COMPLETED = "completed"
PHASE_CORE_TOMBSTONE_COMPLETED = "core_tombstone_completed"


class OrganizationClosureTerminalService:
    def __init__(
        self,
        repository: SqlAlchemyOrganizationClosureProductCleanupRepository,
        closure_repository: SqlAlchemyOrganizationClosureRepository,
        authorization: AuthorizationPort,
        lifecycle: OrganizationLifecycleGuard,
        tombstone: OrganizationTombstonePort,
        audit: AuditPort,
        *,
        package_storage_root: Path | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._closure_repository = closure_repository
        self._authorization = authorization
        self._lifecycle = lifecycle
        self._tombstone = tombstone
        self._audit = audit
        self._package_storage_root = package_storage_root or DEFAULT_CLOSURE_PACKAGE_ROOT
        self._now_provider = now_provider or (lambda: datetime.now(tz=UTC))

    def finalize(
        self,
        *,
        organization_id: UUID,
        execution_id: UUID,
        auth: AuthContext,
        access_token: str,
    ) -> OrganizationClosureExecutionModel:
        self._require_system_authority(organization_id, auth, access_token)
        execution = self._repository.get_execution(organization_id, execution_id)
        if execution is None:
            raise ClosureExecutionNotFoundError("Closure execution not found")

        items = self._repository.list_items(
            organization_id,
            execution_id,
            PRODUCT_CLEANUP_POLICY_VERSION,
        )
        expected_episode = self._require_product_cleanup_complete(items)
        package = self._require_package_purged(organization_id, execution_id)
        self._require_artifact_inventory_terminal(organization_id, execution_id, package)
        self._require_credentials_terminal(organization_id, execution_id)

        snapshot = self._get_lifecycle_snapshot(organization_id)
        self._require_same_episode(snapshot, expected_episode)

        if execution.closed_at is not None or execution.status == STATUS_COMPLETED:
            return self._reconcile_completed_execution(
                execution=execution,
                snapshot=snapshot,
                expected_episode=expected_episode,
            )
        if execution.status != STATUS_IN_PROGRESS:
            raise ClosureExecutionConflictError(
                "Closure execution must be in progress before terminal finalization"
            )

        if not snapshot.is_deleted:
            if snapshot.status != "suspended":
                raise ClosureLifecyclePreconditionError(
                    "Organization must remain suspended before terminal tombstone"
                )
            try:
                self._tombstone.delete_suspended_episode(
                    organization_id=organization_id,
                    expected_suspension_updated_at=expected_episode,
                    access_token=access_token,
                )
            except CoreOrganizationTombstoneUnavailableError as exc:
                raise ClosureLifecycleUnavailableError(
                    "Core organization tombstone authority unavailable"
                ) from exc
            except CoreOrganizationTombstoneConflictError:
                # A 404/409 may mean another actor completed the same tombstone,
                # or that the suspension episode changed. Re-read Core and decide
                # from canonical lifecycle truth instead of guessing from status.
                snapshot = self._get_lifecycle_snapshot(organization_id)
                self._require_same_episode(snapshot, expected_episode)
                if not snapshot.is_deleted:
                    raise ClosureLifecyclePreconditionError(
                        "Core organization tombstone precondition changed"
                    )
            else:
                snapshot = self._get_lifecycle_snapshot(organization_id)

        deleted_at = self._require_terminal_snapshot(snapshot, expected_episode)
        previous_status = execution.status
        now = self._now()
        execution.status = STATUS_COMPLETED
        execution.current_phase = PHASE_CORE_TOMBSTONE_COMPLETED
        execution.closed_at = deleted_at
        execution.failure_code = None
        execution.failure_message = None
        execution.actor_user_id = auth.user_id
        execution.actor_session_id = auth.session_id
        execution.updated_at = now
        self._closure_repository.add_event(
            OrganizationClosureEventModel(
                id=uuid4(),
                execution_id=execution.id,
                organization_id=organization_id,
                actor_user_id=auth.user_id,
                actor_session_id=auth.session_id,
                action="core_tombstone_completed",
                from_status=previous_status,
                to_status=STATUS_COMPLETED,
                phase=PHASE_CORE_TOMBSTONE_COMPLETED,
                created_at=now,
            )
        )
        self._closure_repository.flush()
        self._record_completion_audit(
            organization_id=organization_id,
            execution=execution,
            access_token=access_token,
        )
        return execution

    def _require_product_cleanup_complete(
        self,
        items: tuple[OrganizationClosureProductCleanupItemModel, ...],
    ) -> datetime:
        expected_plan = {(spec.key, spec.sequence) for spec in PRODUCT_CLEANUP_PLAN}
        actual_plan = {(item.class_key, item.sequence) for item in items}
        if len(items) != len(PRODUCT_CLEANUP_PLAN) or actual_plan != expected_plan:
            raise ClosureExecutionConflictError(
                "OL08-D product cleanup evidence is incomplete"
            )
        if any(
            item.status != "completed"
            or item.remaining_count != 0
            or item.completed_at is None
            for item in items
        ):
            raise ClosureExecutionConflictError(
                "OL08-D product cleanup has not reached terminal completion"
            )

        episodes = {self._aware(item.suspension_episode_updated_at) for item in items}
        if len(episodes) != 1:
            raise ClosureExecutionConflictError(
                "OL08-D product cleanup evidence spans multiple suspension episodes"
            )
        return next(iter(episodes))

    def _require_package_purged(
        self,
        organization_id: UUID,
        execution_id: UUID,
    ) -> OrganizationClosurePackageModel:
        package = self._repository.get_package(
            organization_id,
            execution_id,
            PACKAGE_SCHEMA_VERSION,
        )
        if (
            package is None
            or package.status != "purged"
            or package.integrity_verified_at is None
            or package.package_digest is None
            or package.expires_at is None
            or package.purged_at is None
        ):
            raise ClosureExecutionConflictError(
                "Canonical closure package must be integrity-verified and strictly purged before tombstone"
            )
        if self._aware(package.purged_at) < self._aware(package.expires_at):
            raise ClosureExecutionConflictError(
                "Canonical closure package was purged before its retention window completed"
            )

        try:
            resolved = resolve_stored_locator(
                package.storage_locator,
                storage_root=self._package_storage_root,
            )
        except ClosurePackageStorageError as exc:
            raise ClosureExecutionConflictError(
                "Canonical closure package purge locator is unsafe"
            ) from exc

        raw_locator = self._package_storage_root.resolve() / Path(package.storage_locator)
        if raw_locator.is_symlink() or raw_locator.exists() or resolved.exists():
            raise ClosureExecutionConflictError(
                "Canonical closure package lacks positive non-existence evidence"
            )
        return package

    def _require_artifact_inventory_terminal(
        self,
        organization_id: UUID,
        execution_id: UUID,
        package: OrganizationClosurePackageModel,
    ) -> None:
        inventory = self._repository.list_inventory(
            organization_id,
            execution_id,
            package.id,
        )
        for item in inventory:
            if item.ownership_class == "external_reference":
                accepted = item.cleanup_status == "not_applicable"
            elif item.ownership_class != "managed_product_artifact":
                accepted = False
            elif item.storage_kind == "managed_file":
                accepted = (
                    item.cleanup_status in {"purged", "already_absent"}
                    and item.nonexistence_verified_at is not None
                )
            elif item.storage_kind == "embedded_database_bytes":
                accepted = (
                    item.cleanup_status == "already_absent"
                    and item.nonexistence_verified_at is not None
                )
            else:
                accepted = False
            if not accepted:
                raise ClosureExecutionConflictError(
                    "OL08-E managed artifact cleanup evidence is incomplete or blocked"
                )

    def _require_credentials_terminal(self, organization_id: UUID, execution_id: UUID) -> None:
        dispositions = self._repository.list_credentials(organization_id, execution_id)
        if any(item.status != STATUS_DISPOSITION_COMPLETE for item in dispositions):
            raise ClosureExecutionConflictError(
                "OL08-C credential disposition is incomplete or blocked"
            )

    def _reconcile_completed_execution(
        self,
        *,
        execution: OrganizationClosureExecutionModel,
        snapshot: OrganizationLifecycleSnapshot,
        expected_episode: datetime,
    ) -> OrganizationClosureExecutionModel:
        if (
            execution.status != STATUS_COMPLETED
            or execution.current_phase != PHASE_CORE_TOMBSTONE_COMPLETED
            or execution.closed_at is None
        ):
            raise ClosureExecutionConflictError(
                "Closure execution has inconsistent terminal state"
            )
        deleted_at = self._require_terminal_snapshot(snapshot, expected_episode)
        if self._aware(execution.closed_at) != deleted_at:
            raise ClosureExecutionConflictError(
                "FAIR closure timestamp differs from authoritative Core tombstone timestamp"
            )
        return execution

    def _get_lifecycle_snapshot(self, organization_id: UUID) -> OrganizationLifecycleSnapshot:
        try:
            return self._lifecycle.get_snapshot(organization_id)
        except OrganizationLifecycleUnavailableError as exc:
            raise ClosureLifecycleUnavailableError(
                "Organization lifecycle authority unavailable"
            ) from exc

    def _require_same_episode(
        self,
        snapshot: OrganizationLifecycleSnapshot,
        expected_episode: datetime,
    ) -> None:
        if self._aware(snapshot.updated_at) != expected_episode:
            raise ClosureLifecyclePreconditionError(
                "Current Core lifecycle episode differs from OL08-D destructive cleanup evidence"
            )

    def _require_terminal_snapshot(
        self,
        snapshot: OrganizationLifecycleSnapshot,
        expected_episode: datetime,
    ) -> datetime:
        self._require_same_episode(snapshot, expected_episode)
        if not snapshot.is_deleted or snapshot.deleted_at is None:
            raise ClosureLifecyclePreconditionError(
                "Core terminal tombstone is not durably visible"
            )
        return self._aware(snapshot.deleted_at)

    def _require_system_authority(
        self,
        organization_id: UUID,
        auth: AuthContext,
        access_token: str,
    ) -> None:
        try:
            allowed = self._authorization.check_permission(
                organization_id=organization_id,
                user_id=auth.user_id,
                permission_code=SYSTEM_CLOSURE_PERMISSION,
                access_token=access_token,
            )
        except Exception as exc:
            raise ClosureAuthorizationUnavailableError(
                "Terminal closure authorization authority unavailable"
            ) from exc
        if not allowed:
            raise ClosurePermissionDeniedError("Platform SuperAdmin authority required")

    def _record_completion_audit(
        self,
        *,
        organization_id: UUID,
        execution: OrganizationClosureExecutionModel,
        access_token: str,
    ) -> None:
        self._audit.record_event(
            organization_id=organization_id,
            access_token=access_token,
            action="organization_closure.completed",
            resource_type="organization_closure_execution",
            resource_id=str(execution.id),
            new_values={
                "status": execution.status,
                "phase": execution.current_phase,
                "closed_at": self._aware(execution.closed_at).isoformat()
                if execution.closed_at is not None
                else None,
            },
            metadata={"authority": "system", "ol08_slice": "OL08-07"},
        )

    def _now(self) -> datetime:
        return self._aware(self._now_provider())

    @staticmethod
    def _aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
