from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.integrations.kyrox_core.lifecycle import OrganizationLifecycleUnavailableError
from app.integrations.kyrox_core.ports import AuthContext
from app.modules.organization_closure.application.service import (
    ClosureExecutionConflictError,
    ClosureLifecyclePreconditionError,
    ClosureLifecycleUnavailableError,
    ClosurePermissionDeniedError,
    OrganizationClosureService,
    PHASE_INITIALIZED,
    STATUS_BLOCKED,
    STATUS_IN_PROGRESS,
    SYSTEM_CLOSURE_PERMISSION,
)
from app.modules.organization_closure.infrastructure.models import (
    OrganizationClosureEventModel,
    OrganizationClosureExecutionModel,
)
from app.modules.organization_closure.infrastructure.repository import (
    SqlAlchemyOrganizationClosureRepository,
)


class FakeAuthorization:
    def __init__(self, *, allowed: bool = True, error: Exception | None = None) -> None:
        self.allowed = allowed
        self.error = error
        self.calls: list[dict[str, object]] = []

    def check_permission(self, **kwargs: object) -> bool:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.allowed


class FakeLifecycle:
    def __init__(self, *, status: str = "suspended", error: Exception | None = None) -> None:
        self.status = status
        self.error = error
        self.calls: list[object] = []

    def get_snapshot(self, organization_id: object) -> SimpleNamespace:
        self.calls.append(organization_id)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(status=self.status)


class RecordingAudit:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def record_event(self, **kwargs: object) -> None:
        self.events.append(kwargs)


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            OrganizationClosureExecutionModel.__table__,
            OrganizationClosureEventModel.__table__,
        ],
    )
    with Session(engine) as session:
        yield session
    engine.dispose()


def _auth(organization_id):
    return AuthContext(
        user_id=uuid4(),
        email="platform-admin@example.com",
        session_id=uuid4(),
        organization_id=organization_id,
    )


def _service(
    session: Session,
    *,
    allowed: bool = True,
    lifecycle_status: str = "suspended",
    lifecycle_error: Exception | None = None,
):
    authorization = FakeAuthorization(allowed=allowed)
    lifecycle = FakeLifecycle(status=lifecycle_status, error=lifecycle_error)
    audit = RecordingAudit()
    service = OrganizationClosureService(
        SqlAlchemyOrganizationClosureRepository(session),
        authorization,
        lifecycle,
        audit,
    )
    return service, authorization, lifecycle, audit


def _row_count(session: Session, model: type) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def test_start_requires_system_authority_and_live_suspended_state(db_session: Session) -> None:
    organization_id = uuid4()
    auth = _auth(organization_id)
    service, authorization, lifecycle, audit = _service(db_session)

    execution = service.start(
        organization_id=organization_id,
        idempotency_key="close-2026-09-07",
        auth=auth,
        access_token="token",
    )

    assert execution.organization_id == organization_id
    assert execution.status == STATUS_IN_PROGRESS
    assert execution.current_phase == PHASE_INITIALIZED
    assert execution.attempt_count == 1
    assert execution.closed_at is None
    assert authorization.calls[0]["permission_code"] == SYSTEM_CLOSURE_PERMISSION
    assert lifecycle.calls == [organization_id]
    assert _row_count(db_session, OrganizationClosureExecutionModel) == 1

    events = list(db_session.scalars(select(OrganizationClosureEventModel)).all())
    assert len(events) == 1
    assert events[0].action == "started"
    assert events[0].execution_id == execution.id
    assert events[0].actor_user_id == auth.user_id
    assert audit.events[0]["action"] == "fair_crm.organization_closure.started"


def test_duplicate_start_with_same_idempotency_key_converges(db_session: Session) -> None:
    organization_id = uuid4()
    auth = _auth(organization_id)
    service, _, lifecycle, _ = _service(db_session)

    first = service.start(
        organization_id=organization_id,
        idempotency_key="same-key",
        auth=auth,
        access_token="token",
    )
    second = service.start(
        organization_id=organization_id,
        idempotency_key="same-key",
        auth=auth,
        access_token="token",
    )

    assert second.id == first.id
    assert _row_count(db_session, OrganizationClosureExecutionModel) == 1
    assert _row_count(db_session, OrganizationClosureEventModel) == 1
    assert lifecycle.calls == [organization_id, organization_id]


def test_conflicting_second_open_execution_is_rejected(db_session: Session) -> None:
    organization_id = uuid4()
    auth = _auth(organization_id)
    service, _, _, _ = _service(db_session)

    service.start(
        organization_id=organization_id,
        idempotency_key="first-key",
        auth=auth,
        access_token="token",
    )

    with pytest.raises(ClosureExecutionConflictError):
        service.start(
            organization_id=organization_id,
            idempotency_key="different-key",
            auth=auth,
            access_token="token",
        )

    assert _row_count(db_session, OrganizationClosureExecutionModel) == 1


def test_ordinary_or_organization_role_authority_is_denied_without_mutation(
    db_session: Session,
) -> None:
    organization_id = uuid4()
    auth = _auth(organization_id)
    service, authorization, lifecycle, _ = _service(db_session, allowed=False)

    with pytest.raises(ClosurePermissionDeniedError):
        service.start(
            organization_id=organization_id,
            idempotency_key="denied",
            auth=auth,
            access_token="token",
        )

    assert authorization.calls[0]["permission_code"] == "identity.organizations.delete"
    assert lifecycle.calls == []
    assert _row_count(db_session, OrganizationClosureExecutionModel) == 0


def test_non_suspended_state_fails_closed_without_mutation(db_session: Session) -> None:
    organization_id = uuid4()
    auth = _auth(organization_id)
    service, _, _, _ = _service(db_session, lifecycle_status="active")

    with pytest.raises(ClosureLifecyclePreconditionError):
        service.start(
            organization_id=organization_id,
            idempotency_key="active-org",
            auth=auth,
            access_token="token",
        )

    assert _row_count(db_session, OrganizationClosureExecutionModel) == 0


def test_lifecycle_authority_outage_fails_closed_without_mutation(db_session: Session) -> None:
    organization_id = uuid4()
    auth = _auth(organization_id)
    service, _, _, _ = _service(
        db_session,
        lifecycle_error=OrganizationLifecycleUnavailableError("Core unavailable"),
    )

    with pytest.raises(ClosureLifecycleUnavailableError):
        service.start(
            organization_id=organization_id,
            idempotency_key="authority-outage",
            auth=auth,
            access_token="token",
        )

    assert _row_count(db_session, OrganizationClosureExecutionModel) == 0


def test_blocked_execution_retries_same_logical_execution_idempotently(
    db_session: Session,
) -> None:
    organization_id = uuid4()
    auth = _auth(organization_id)
    service, _, lifecycle, _ = _service(db_session)

    execution = service.start(
        organization_id=organization_id,
        idempotency_key="retryable",
        auth=auth,
        access_token="token",
    )
    service.mark_blocked(
        organization_id=organization_id,
        execution_id=execution.id,
        actor=auth,
        failure_code="internal_checkpoint_failed",
        failure_message="checkpoint failed before any destructive phase",
    )
    assert execution.status == STATUS_BLOCKED

    retried = service.retry(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )
    repeated_retry = service.retry(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )

    assert retried.id == execution.id == repeated_retry.id
    assert retried.status == STATUS_IN_PROGRESS
    assert retried.attempt_count == 2
    assert retried.failure_code is None
    assert retried.failure_message is None
    assert retried.last_retry_at is not None
    assert lifecycle.calls == [organization_id, organization_id, organization_id]

    actions = list(
        db_session.scalars(
            select(OrganizationClosureEventModel.action).order_by(
                OrganizationClosureEventModel.created_at,
                OrganizationClosureEventModel.action,
            )
        ).all()
    )
    assert sorted(actions) == ["blocked", "retried", "started"]


def test_retry_rechecks_lifecycle_and_leaves_blocked_state_unchanged(db_session: Session) -> None:
    organization_id = uuid4()
    auth = _auth(organization_id)
    service, _, lifecycle, _ = _service(db_session)

    execution = service.start(
        organization_id=organization_id,
        idempotency_key="retry-live-check",
        auth=auth,
        access_token="token",
    )
    service.mark_blocked(
        organization_id=organization_id,
        execution_id=execution.id,
        actor=auth,
        failure_code="blocked",
        failure_message="blocked",
    )
    lifecycle.status = "active"

    with pytest.raises(ClosureLifecyclePreconditionError):
        service.retry(
            organization_id=organization_id,
            execution_id=execution.id,
            auth=auth,
            access_token="token",
        )

    assert execution.status == STATUS_BLOCKED
    assert execution.attempt_count == 1


def test_database_constraint_prevents_two_open_executions_for_same_organization(
    db_session: Session,
) -> None:
    organization_id = uuid4()
    auth = _auth(organization_id)
    service, _, _, _ = _service(db_session)
    first = service.start(
        organization_id=organization_id,
        idempotency_key="race-a",
        auth=auth,
        access_token="token",
    )
    db_session.commit()

    second = OrganizationClosureExecutionModel(
        id=uuid4(),
        organization_id=organization_id,
        idempotency_key="race-b",
        status=STATUS_IN_PROGRESS,
        current_phase=PHASE_INITIALIZED,
        actor_user_id=auth.user_id,
        actor_session_id=auth.session_id,
        attempt_count=1,
        failure_code=None,
        failure_message=None,
        created_at=first.created_at,
        updated_at=first.updated_at,
        last_retry_at=None,
        closed_at=None,
    )
    db_session.add(second)

    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

    assert _row_count(db_session, OrganizationClosureExecutionModel) == 1


def test_ol08_01_has_no_cleanup_complete_or_tombstone_ready_state() -> None:
    allowed_runtime_states = {STATUS_IN_PROGRESS, STATUS_BLOCKED}

    assert allowed_runtime_states == {"in_progress", "blocked"}
    assert "complete" not in allowed_runtime_states
    assert "ready_for_tombstone" not in allowed_runtime_states
