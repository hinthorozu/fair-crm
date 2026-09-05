"""OL07-05 lifecycle checkpoints for already-running product work.

A checkpoint is intentionally side-effect free: Core remains the lifecycle
authority and FAIR CRM never persists a second lifecycle state.  Callers place
checkpoints immediately before the next safe unit of product work.  Explicit
non-active lifecycle state raises a cancellation signal; lifecycle authority
failure propagates separately so callers fail closed without inventing a
suspension disposition.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.integrations.kyrox_core.lifecycle import (
    OrganizationLifecycleGuard,
    OrganizationLifecycleSnapshot,
)


@dataclass(frozen=True, slots=True)
class RunningWorkLifecycleCancelledError(RuntimeError):
    """Canonical Core lifecycle explicitly stopped an already-running job."""

    organization_id: UUID
    status: str

    def __str__(self) -> str:
        return f"Organization lifecycle stopped running work: {self.status}"


class RunningWorkLifecycleCheckpoint:
    """Fresh, fail-closed Core lifecycle check for running work boundaries."""

    def __init__(
        self,
        organization_id: UUID,
        *,
        guard: OrganizationLifecycleGuard | None = None,
    ) -> None:
        self._organization_id = organization_id
        self._guard = guard or OrganizationLifecycleGuard()

    def check(self) -> OrganizationLifecycleSnapshot:
        snapshot = self._guard.get_snapshot(self._organization_id)
        if not snapshot.work_allowed:
            raise RunningWorkLifecycleCancelledError(
                organization_id=self._organization_id,
                status=snapshot.status,
            )
        return snapshot
