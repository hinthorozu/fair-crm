"""Move all active participations from one fair to another."""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.fairs.domain.ports import FairRepository
from app.modules.participations.application.commands import (
    MoveParticipationsToFairCommand,
    MoveParticipationsToFairResult,
)
from app.modules.participations.application.validators import ensure_fair_for_participation
from app.modules.participations.domain.exceptions import SameFairMoveError
from app.modules.participations.domain.ports import ParticipationRepository

PERMISSION_UPDATE = "fair_crm.participations.update"


class MoveParticipationsToFairUseCase:
    def __init__(
        self,
        participation_repository: ParticipationRepository,
        fair_repository: FairRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._participation_repository = participation_repository
        self._fair_repository = fair_repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: MoveParticipationsToFairCommand) -> MoveParticipationsToFairResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_UPDATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        if command.source_fair_id == command.target_fair_id:
            raise SameFairMoveError("Source and target fair must be different")

        ensure_fair_for_participation(
            self._fair_repository, command.organization_id, command.source_fair_id
        )
        ensure_fair_for_participation(
            self._fair_repository, command.organization_id, command.target_fair_id
        )

        now = datetime.now(tz=UTC)
        bulk = self._participation_repository.move_all_active_to_fair(
            command.organization_id,
            command.source_fair_id,
            command.target_fair_id,
            now=now,
        )
        moved_count = bulk.moved_count
        already_on_target_count = bulk.already_on_target_count
        source_remaining = bulk.source_remaining

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.participation.moved_to_fair",
            resource_type="fair",
            resource_id=str(command.source_fair_id),
            new_values={
                "target_fair_id": str(command.target_fair_id),
                "moved_count": moved_count,
                "already_on_target_count": already_on_target_count,
                "source_remaining": source_remaining,
            },
            metadata={"user_id": str(command.user_id)},
        )

        return MoveParticipationsToFairResult(
            source_fair_id=command.source_fair_id,
            target_fair_id=command.target_fair_id,
            moved_count=moved_count,
            already_on_target_count=already_on_target_count,
            source_remaining=source_remaining,
        )
