from datetime import UTC, date, datetime
from typing import Any, Optional

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.fairs.application.commands import FairResult, UpdateFairCommand
from app.modules.fairs.application.mappers import fair_to_result
from app.modules.fairs.domain.exceptions import FairNotFoundError
from app.modules.fairs.domain.ports import FairRepository

PERMISSION_UPDATE = "fair_crm.fairs.update"

_STRING_CLEAR_FIELDS = (
    "organizer",
    "venue",
    "city",
    "country",
    "website",
    "description",
    "adapter_key",
    "source_url",
)


def _clearable_str(command: UpdateFairCommand, field: str) -> Optional[str]:
    """Omit when unset; convert explicit null to '' so domain clears the field."""
    if field not in command.fields_set:
        return None
    value = getattr(command, field)
    if value is None:
        return ""
    return value


def _should_auto_plan(command: UpdateFairCommand, today: date) -> bool:
    """When start/end is set to today or a future date, force status to planned.

    Explicit status in the same request wins (auto-plan is skipped).
    """
    if "status" in command.fields_set:
        return False

    candidates: list[date] = []
    if "start_date" in command.fields_set and command.start_date is not None:
        candidates.append(command.start_date)
    if "end_date" in command.fields_set and command.end_date is not None:
        candidates.append(command.end_date)

    return any(value >= today for value in candidates)


class UpdateFairUseCase:
    def __init__(
        self,
        repository: FairRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: UpdateFairCommand) -> FairResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_UPDATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        fair = self._repository.get_by_id(command.organization_id, command.fair_id)
        if fair is None:
            raise FairNotFoundError("Fair not found")

        now = datetime.now(tz=UTC)
        string_kwargs: dict[str, Any] = {
            field: _clearable_str(command, field) for field in _STRING_CLEAR_FIELDS
        }

        fair.update_fields(
            name=command.name if "name" in command.fields_set else None,
            organizer=string_kwargs["organizer"],
            venue=string_kwargs["venue"],
            city=string_kwargs["city"],
            country=string_kwargs["country"],
            start_date=command.start_date if "start_date" in command.fields_set else None,
            end_date=command.end_date if "end_date" in command.fields_set else None,
            website=string_kwargs["website"],
            status=command.status if "status" in command.fields_set else None,
            description=string_kwargs["description"],
            adapter_key=string_kwargs["adapter_key"],
            source_url=string_kwargs["source_url"],
            scraper_config=(
                command.scraper_config if "scraper_config" in command.fields_set else None
            ),
            now=now,
            clear_start_date="start_date" in command.fields_set and command.start_date is None,
            clear_end_date="end_date" in command.fields_set and command.end_date is None,
            clear_scraper_config=(
                "scraper_config" in command.fields_set and command.scraper_config is None
            ),
            auto_planned_from_dates=_should_auto_plan(command, now.date()),
        )

        saved = self._repository.update(fair)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.fair.updated",
            resource_type="fair",
            resource_id=str(saved.id),
            new_values={"name": saved.name, "status": saved.status.value},
            metadata={"user_id": str(command.user_id)},
        )

        return fair_to_result(saved)
