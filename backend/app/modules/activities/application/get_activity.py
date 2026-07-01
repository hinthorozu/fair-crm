from app.modules.activities.application.commands import ActivityResult, GetActivityQuery
from app.modules.activities.application.mappers import activity_to_result, resolve_contact_full_name
from app.modules.activities.domain.exceptions import ActivityNotFoundError
from app.modules.activities.domain.ports import ActivityRepository
from app.modules.contacts.domain.ports import ContactRepository


class GetActivityUseCase:
    def __init__(
        self,
        activity_repository: ActivityRepository,
        contact_repository: ContactRepository,
    ) -> None:
        self._activity_repository = activity_repository
        self._contact_repository = contact_repository

    def execute(self, query: GetActivityQuery) -> ActivityResult:
        activity = self._activity_repository.get_by_id(query.organization_id, query.activity_id)
        if activity is None:
            raise ActivityNotFoundError("Activity not found")

        contact_full_name = resolve_contact_full_name(
            self._contact_repository, query.organization_id, activity.contact_id
        )
        return activity_to_result(activity, contact_full_name=contact_full_name)
