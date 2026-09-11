from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable
from uuid import UUID

from app.integrations.kyrox_core.audit_retention import (
    CoreAuditRetentionPreconditionError,
    CoreAuditRetentionUnavailableError,
    KyroxCoreAuditRetentionAdapter,
)
from app.integrations.kyrox_core.lifecycle import (
    OrganizationLifecycleGuard,
    OrganizationLifecycleUnavailableError,
)
from app.integrations.kyrox_core.ports import AuthContext, AuthorizationPort
from app.modules.organization_closure.application.service import (
    SYSTEM_CLOSURE_PERMISSION,
    ClosureAuthorizationUnavailableError,
    ClosureLifecyclePreconditionError,
    ClosureLifecycleUnavailableError,
    ClosurePermissionDeniedError,
)
from app.modules.organization_closure.infrastructure.evidence_retention_repository import (
    LocalClosureEvidencePurgeCounts,
    SqlAlchemyOrganizationClosureEvidenceRetentionRepository,
)

EVIDENCE_RETENTION_MONTHS = 12


@dataclass(frozen=True, slots=True)
class OrganizationClosureEvidenceRetentionResult:
    organization_id: UUID
    terminal_closed_at: datetime
    retention_deadline: datetime
    core_audit_purged_count: int
    local_purge_counts: LocalClosureEvidencePurgeCounts


def add_calendar_months(value: datetime, months: int) -> datetime:
    value = _aware(value)
    if months < 0:
        raise ValueError("Retention month offset must be non-negative")
    target_index = value.year * 12 + (value.month - 1) + months
    target_year, target_month_index = divmod(target_index, 12)
    target_month = target_month_index + 1
    target_day = min(value.day, monthrange(target_year, target_month)[1])
    return value.replace(year=target_year, month=target_month, day=target_day)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class OrganizationClosureEvidenceRetentionService:
    def __init__(
        self,
        repository: SqlAlchemyOrganizationClosureEvidenceRetentionRepository,
        authorization: AuthorizationPort,
        lifecycle: OrganizationLifecycleGuard,
        core_audit_retention: KyroxCoreAuditRetentionAdapter,
        *,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._lifecycle = lifecycle
        self._core_audit_retention = core_audit_retention
        self._now_provider = now_provider or (lambda: datetime.now(tz=UTC))

    def purge(
        self,
        *,
        organization_id: UUID,
        auth: AuthContext,
        access_token: str,
    ) -> OrganizationClosureEvidenceRetentionResult:
        self._require_system_authority(organization_id, auth, access_token)
        snapshot = self._get_lifecycle_snapshot(organization_id)
        if not snapshot.is_deleted or snapshot.deleted_at is None:
            raise ClosureLifecyclePreconditionError(
                "OL08-F retention purge requires the authoritative terminal Core tombstone"
            )

        terminal_closed_at = _aware(snapshot.deleted_at)
        execution = self._repository.get_completed_execution(organization_id)
        if execution is not None:
            if execution.closed_at is None or _aware(execution.closed_at) != terminal_closed_at:
                raise ClosureLifecyclePreconditionError(
                    "FAIR terminal closure timestamp differs from authoritative Core tombstone"
                )

        retention_deadline = add_calendar_months(
            terminal_closed_at,
            EVIDENCE_RETENTION_MONTHS,
        )
        if _aware(self._now_provider()) < retention_deadline:
            raise ClosureLifecyclePreconditionError(
                "OL08-F retained-evidence deadline has not been reached"
            )

        try:
            core_result = self._core_audit_retention.purge(organization_id)
        except CoreAuditRetentionPreconditionError as exc:
            raise ClosureLifecyclePreconditionError(
                "Core retained-audit purge precondition is not satisfied"
            ) from exc
        except CoreAuditRetentionUnavailableError as exc:
            raise ClosureLifecycleUnavailableError(
                "Core retained-audit authority unavailable"
            ) from exc

        if (
            _aware(core_result.terminal_deleted_at) != terminal_closed_at
            or _aware(core_result.retention_deadline) != retention_deadline
        ):
            raise ClosureLifecyclePreconditionError(
                "Core retained-audit retention clock differs from authoritative closure clock"
            )

        local_counts = self._repository.purge_for_organization(organization_id)
        return OrganizationClosureEvidenceRetentionResult(
            organization_id=organization_id,
            terminal_closed_at=terminal_closed_at,
            retention_deadline=retention_deadline,
            core_audit_purged_count=core_result.purged_count,
            local_purge_counts=local_counts,
        )

    def _get_lifecycle_snapshot(self, organization_id: UUID):
        try:
            return self._lifecycle.get_snapshot(organization_id)
        except OrganizationLifecycleUnavailableError as exc:
            raise ClosureLifecycleUnavailableError(
                "Organization lifecycle authority unavailable"
            ) from exc

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
                "OL08-F retention authorization authority unavailable"
            ) from exc
        if not allowed:
            raise ClosurePermissionDeniedError("Platform SuperAdmin authority required")
