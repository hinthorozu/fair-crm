from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.fairs.application.commands import CreateFairCommand, FairResult
from app.modules.fairs.application.mappers import fair_to_result
from app.modules.fairs.domain.entities import Fair
from app.modules.fairs.domain.ports import FairRepository

PERMISSION_CREATE = "fair_crm.fairs.create"


class CreateFairUseCase:
    def __init__(
        self,
        repository: FairRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: CreateFairCommand) -> FairResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_CREATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        now = datetime.now(tz=UTC)
        fair = Fair.create(
            organization_id=command.organization_id,
            name=command.name,
            organizer=command.organizer,
            venue=command.venue,
            city=command.city,
            country=command.country,
            start_date=command.start_date,
            end_date=command.end_date,
            website=command.website,
            status=command.status,
            description=command.description,
            adapter_key=command.adapter_key,
            source_url=command.source_url,
            scraper_config=command.scraper_config,
            now=now,
        )

        saved = self._repository.add(fair)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.fair.created",
            resource_type="fair",
            resource_id=str(saved.id),
            new_values={"name": saved.name, "status": saved.status.value},
            metadata={"user_id": str(command.user_id)},
        )

        return fair_to_result(saved)
