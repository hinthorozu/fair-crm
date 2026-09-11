from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from app.integrations.kyrox_core.lifecycle import (
    OrganizationLifecycleGuard,
    OrganizationLifecycleUnavailableError,
)
from app.integrations.kyrox_core.ports import AuditPort, AuthContext, AuthorizationPort
from app.modules.organization_closure.infrastructure.models import (
    OrganizationClosureEventModel,
    OrganizationClosureExecutionModel,
)
from app.modules.organization_closure.infrastructure.repository import (
    SqlAlchemyOrganizationClosureRepository,
)

SYSTEM_CLOSURE_PERMISSION = "identity.organizations.delete"
STATUS_IN_PROGRESS = "in_progress"
STATUS_BLOCKED = "blocked"
PHASE_INITIALIZED = "orchestration_initialized"


class OrganizationClosureError(Exception):
    pass


class ClosurePermissionDeniedError(OrganizationClosureError):
    pass


class ClosureAuthorizationUnavailableError(OrganizationClosureError):
    pass


class ClosureLifecycleUnavailableError(OrganizationClosureError):
    pass


class ClosureLifecyclePreconditionError(OrganizationClosureError):
    pass


class ClosureExecutionConflictError(OrganizationClosureError):
    pass


class ClosureExecutionNotFoundError(OrganizationClosureError):
    pass


class OrganizationClosureService:
    def __init__(
        self,
        repository: SqlAlchemyOrganizationClosureRepository,
        authorization: AuthorizationPort,
        lifecycle: OrganizationLifecycleGuard,
        audit: AuditPort,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._lifecycle = lifecycle
        self._audit = audit

    def start(
        self,
        *,
        organization_id: UUID,
        idempotency_key: str,
        auth: AuthContext,
        access_token: str,
    ) -> OrganizationClosureExecutionModel:
        self._require_system_authority(organization_id, auth, access_token)
        self._require_suspended(organization_id)

        existing = self._repository.get_by_idempotency(organization_id, idempotency_key)
        if existing is not None:
            return existing

        open_execution = self._repository.get_open_for_organization(organization_id)
        if open_execution is not None:
            raise ClosureExecutionConflictError(
                "Another closure execution is already open for this organization"
            )

        now = datetime.now(tz=UTC)
        execution = OrganizationClosureExecutionModel(
            id=uuid4(),
            organization_id=organization_id,
            idempotency_key=idempotency_key,
            status=STATUS_IN_PROGRESS,
            current_phase=PHASE_INITIALIZED,
            actor_user_id=auth.user_id,
            actor_session_id=auth.session_id,
            attempt_count=1,
            failure_code=None,
            failure_message=None,
            created_at=now,
            updated_at=now,
            last_retry_at=None,
            closed_at=None,
        )
        event = self._build_event(
            execution=execution,
            actor=auth,
            action="started",
            from_status=None,
            to_status=STATUS_IN_PROGRESS,
            at=now,
        )
        self._repository.add_execution(execution)

        try:
            # The append-only event has a real FK to the execution. Flush the
            # parent first so FK-enforcing databases cannot schedule the event
            # insert ahead of its parent. Both flushes remain in the same
            # transaction; any event failure rolls the execution back too.
            self._repository.flush()
            self._repository.add_event(event)
            self._repository.flush()
        except IntegrityError as exc:
            self._repository.rollback()
            duplicate = self._repository.get_by_idempotency(organization_id, idempotency_key)
            if duplicate is not None:
                return duplicate
            if self._repository.get_open_for_organization(organization_id) is not None:
                raise ClosureExecutionConflictError(
                    "Another closure execution is already open for this organization"
                ) from exc
            raise

        self._record_core_audit(
            organization_id=organization_id,
            access_token=access_token,
            execution=execution,
            action="organization_closure.started",
        )
        return execution

    def get(
        self,
        *,
        organization_id: UUID,
        execution_id: UUID,
        auth: AuthContext,
        access_token: str,
    ) -> OrganizationClosureExecutionModel:
        self._require_system_authority(organization_id, auth, access_token)
        execution = self._repository.get_by_id(organization_id, execution_id)
        if execution is None:
            raise ClosureExecutionNotFoundError("Closure execution not found")
        return execution

    def retry(
        self,
        *,
        organization_id: UUID,
        execution_id: UUID,
        auth: AuthContext,
        access_token: str,
    ) -> OrganizationClosureExecutionModel:
        self._require_system_authority(organization_id, auth, access_token)
        self._require_suspended(organization_id)

        execution = self._repository.get_by_id(organization_id, execution_id)
        if execution is None or execution.closed_at is not None:
            raise ClosureExecutionNotFoundError("Open closure execution not found")
        if execution.status == STATUS_IN_PROGRESS:
            return execution
        if execution.status != STATUS_BLOCKED:
            raise ClosureExecutionConflictError("Closure execution cannot be retried")

        now = datetime.now(tz=UTC)
        previous_status = execution.status
        execution.status = STATUS_IN_PROGRESS
        execution.failure_code = None
        execution.failure_message = None
        execution.attempt_count += 1
        execution.last_retry_at = now
        execution.updated_at = now
        execution.actor_user_id = auth.user_id
        execution.actor_session_id = auth.session_id
        self._repository.add_event(
            self._build_event(
                execution=execution,
                actor=auth,
                action="retried",
                from_status=previous_status,
                to_status=STATUS_IN_PROGRESS,
                at=now,
            )
        )
        self._repository.flush()
        self._record_core_audit(
            organization_id=organization_id,
            access_token=access_token,
            execution=execution,
            action="organization_closure.retried",
        )
        return execution

    def mark_blocked(
        self,
        *,
        organization_id: UUID,
        execution_id: UUID,
        actor: AuthContext,
        failure_code: str,
        failure_message: str,
        access_token: str | None = None,
    ) -> OrganizationClosureExecutionModel:
        execution = self._repository.get_by_id(organization_id, execution_id)
        if execution is None or execution.closed_at is not None:
            raise ClosureExecutionNotFoundError("Open closure execution not found")

        now = datetime.now(tz=UTC)
        previous_status = execution.status
        execution.status = STATUS_BLOCKED
        execution.failure_code = failure_code
        execution.failure_message = failure_message
        execution.updated_at = now
        execution.actor_user_id = actor.user_id
        execution.actor_session_id = actor.session_id
        self._repository.add_event(
            self._build_event(
                execution=execution,
                actor=actor,
                action="blocked",
                from_status=previous_status,
                to_status=STATUS_BLOCKED,
                at=now,
            )
        )
        self._repository.flush()
        if access_token:
            self._record_core_audit(
                organization_id=organization_id,
                access_token=access_token,
                execution=execution,
                action="organization_closure.blocked",
            )
        return execution

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
                "Closure authorization authority unavailable"
            ) from exc
        if not allowed:
            raise ClosurePermissionDeniedError("Platform SuperAdmin authority required")

    def _require_suspended(self, organization_id: UUID) -> None:
        try:
            snapshot = self._lifecycle.get_snapshot(organization_id)
        except OrganizationLifecycleUnavailableError as exc:
            raise ClosureLifecycleUnavailableError(
                "Organization lifecycle authority unavailable"
            ) from exc
        if snapshot.is_deleted or snapshot.status != "suspended":
            state = "deleted" if snapshot.is_deleted else snapshot.status
            raise ClosureLifecyclePreconditionError(
                f"Organization must be suspended before closure execution: {state}"
            )

    @staticmethod
    def _build_event(
        *,
        execution: OrganizationClosureExecutionModel,
        actor: AuthContext,
        action: str,
        from_status: str | None,
        to_status: str,
        at: datetime,
    ) -> OrganizationClosureEventModel:
        return OrganizationClosureEventModel(
            id=uuid4(),
            execution_id=execution.id,
            organization_id=execution.organization_id,
            actor_user_id=actor.user_id,
            actor_session_id=actor.session_id,
            action=action,
            from_status=from_status,
            to_status=to_status,
            phase=execution.current_phase,
            created_at=at,
        )

    def _record_core_audit(
        self,
        *,
        organization_id: UUID,
        access_token: str,
        execution: OrganizationClosureExecutionModel,
        action: str,
    ) -> None:
        self._audit.record_event(
            organization_id=organization_id,
            access_token=access_token,
            action=action,
            resource_type="organization_closure_execution",
            resource_id=str(execution.id),
            new_values={
                "status": execution.status,
                "phase": execution.current_phase,
                "attempt_count": execution.attempt_count,
            },
            metadata={"authority": "system", "ol08_slice": "OL08-01"},
        )
