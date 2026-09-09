"""Fail-closed post-restore reconciliation for FAIR CRM organization data.

A restored FAIR CRM database is historical state. Current organization lifecycle
truth is owned by Kyrox Core and must be re-established before the restore can be
certified for production use.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import MetaData, create_engine, select
from sqlalchemy.exc import SQLAlchemyError

from app.integrations.kyrox_core.lifecycle import (
    OrganizationLifecycleGuard,
    OrganizationLifecycleUnavailableError,
)


@dataclass(frozen=True, slots=True)
class RestoredOrganizationState:
    organization_id: UUID
    status: str
    work_allowed: bool
    is_deleted: bool


@dataclass(frozen=True, slots=True)
class RestoreOrganizationReconciliationResult:
    ok: bool
    organization_count: int
    active_count: int
    inactive_count: int
    deleted_count: int
    states: tuple[RestoredOrganizationState, ...] = ()
    error_message: str | None = None

    def log_lines(self) -> list[str]:
        lines = [
            "organization reconciliation:",
            f"  organizations discovered: {self.organization_count}",
            f"  active: {self.active_count}",
            f"  non-active: {self.inactive_count}",
            f"  Core-deleted: {self.deleted_count}",
        ]
        for state in self.states:
            lines.append(
                "  organization "
                f"{state.organization_id}: status={state.status} "
                f"work_allowed={str(state.work_allowed).lower()} "
                f"is_deleted={str(state.is_deleted).lower()}"
            )
        if self.error_message:
            lines.append(f"  error: {self.error_message}")
        lines.append(f"  result: {'PASS' if self.ok else 'BLOCK'}")
        return lines

    def summary_text(self) -> str:
        return (
            "OL10 organization reconciliation: "
            f"result={'PASS' if self.ok else 'BLOCK'}; "
            f"organizations={self.organization_count}; "
            f"active={self.active_count}; "
            f"non_active={self.inactive_count}; "
            f"core_deleted={self.deleted_count}"
        )


def enumerate_restored_organization_ids(*, database_url: str) -> tuple[UUID, ...]:
    """Discover tenant ids from every restored table carrying organization_id.

    This intentionally uses the restored database surface instead of trusting the
    organization-closure table. Reflection also safely quotes identifiers for the
    generated DISTINCT queries.
    """

    engine = create_engine(database_url)
    try:
        metadata = MetaData()
        metadata.reflect(bind=engine)
        organization_ids: set[UUID] = set()
        with engine.connect() as connection:
            for table in metadata.sorted_tables:
                column = table.c.get("organization_id")
                if column is None:
                    continue
                rows = connection.execute(
                    select(column).where(column.is_not(None)).distinct()
                ).scalars()
                for raw_value in rows:
                    try:
                        organization_ids.add(UUID(str(raw_value)))
                    except (TypeError, ValueError, AttributeError) as exc:
                        raise ValueError(
                            f"Invalid organization_id in restored table {table.fullname}"
                        ) from exc
        return tuple(sorted(organization_ids, key=str))
    except SQLAlchemyError as exc:
        raise ValueError("Could not enumerate restored organization data") from exc
    finally:
        engine.dispose()


def run_restore_organization_reconciliation(
    *,
    database_url: str,
    lifecycle_guard: OrganizationLifecycleGuard | None = None,
) -> RestoreOrganizationReconciliationResult:
    """Reconcile restored tenant ids against live Kyrox Core lifecycle truth.

    Non-active but non-deleted organizations may remain physically present because
    normal FAIR CRM work is already gated by Core lifecycle state. Any explicit
    Core deletion, unknown organization, authority outage, malformed response, or
    inconsistent response blocks restore certification.
    """

    guard = lifecycle_guard or OrganizationLifecycleGuard()
    try:
        organization_ids = enumerate_restored_organization_ids(database_url=database_url)
    except ValueError as exc:
        return RestoreOrganizationReconciliationResult(
            ok=False,
            organization_count=0,
            active_count=0,
            inactive_count=0,
            deleted_count=0,
            error_message=str(exc),
        )

    states: list[RestoredOrganizationState] = []
    active_count = 0
    inactive_count = 0
    deleted_count = 0

    for organization_id in organization_ids:
        try:
            snapshot = guard.get_snapshot(organization_id)
        except OrganizationLifecycleUnavailableError as exc:
            return RestoreOrganizationReconciliationResult(
                ok=False,
                organization_count=len(organization_ids),
                active_count=active_count,
                inactive_count=inactive_count,
                deleted_count=deleted_count,
                states=tuple(states),
                error_message=(
                    "Kyrox Core lifecycle authority could not establish current state for "
                    f"organization {organization_id}: {exc}"
                ),
            )

        state = RestoredOrganizationState(
            organization_id=organization_id,
            status=snapshot.status,
            work_allowed=snapshot.work_allowed,
            is_deleted=snapshot.is_deleted,
        )
        states.append(state)
        if snapshot.is_deleted:
            deleted_count += 1
        elif snapshot.work_allowed:
            active_count += 1
        else:
            inactive_count += 1

    if deleted_count:
        deleted_ids = ", ".join(
            str(state.organization_id) for state in states if state.is_deleted
        )
        return RestoreOrganizationReconciliationResult(
            ok=False,
            organization_count=len(organization_ids),
            active_count=active_count,
            inactive_count=inactive_count,
            deleted_count=deleted_count,
            states=tuple(states),
            error_message=(
                "Restored FAIR CRM data references Core-deleted organizations "
                f"({deleted_ids}). Restore remains blocked until destructive reconciliation "
                "is explicitly completed."
            ),
        )

    return RestoreOrganizationReconciliationResult(
        ok=True,
        organization_count=len(organization_ids),
        active_count=active_count,
        inactive_count=inactive_count,
        deleted_count=0,
        states=tuple(states),
    )
