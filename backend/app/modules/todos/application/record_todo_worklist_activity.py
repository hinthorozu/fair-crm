from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.activities.domain.entities import Activity
from app.modules.activities.domain.ports import ActivityRepository
from app.modules.activities.domain.value_objects import ActivitySource, ActivityStatus, ActivityType
from app.modules.participations.infrastructure.repositories.participation_repository import (
    SqlAlchemyParticipationRepository,
)
from app.modules.todos.application.worklist_commands import (
    RecordTodoWorklistActivityCommand,
    TodoWorklistActivityResult,
)
from app.modules.todos.application.worklist_mappers import (
    worklist_progress_to_result,
    worklist_row_to_result,
)
from app.modules.todos.domain.exceptions import (
    InvalidWorklistNoteError,
    TodoMissingSourceFairError,
    TodoNotFoundError,
    TodoOutcomeDefinitionNotFoundError,
    TodoOutcomeInactiveError,
    WorklistCustomerNotInTodoError,
)
from app.modules.todos.domain.ports import TodoRepository
from app.modules.todos.domain.worklist_entities import TodoWorklistState
from app.modules.todos.domain.worklist_ports import (
    TodoOutcomeDefinitionRepository,
    TodoWorklistQueryRepository,
    TodoWorklistStateRepository,
)
from app.modules.todos.domain.worklist_value_objects import WorklistFilter

PERMISSION_CREATE = "fair_crm.todos.create"
NOTE_SUMMARY_MAX_LEN = 500


def _truncate_note(note: str) -> str:
    trimmed = note.strip()
    if not trimmed:
        raise InvalidWorklistNoteError("note must not be empty")
    if len(trimmed) <= NOTE_SUMMARY_MAX_LEN:
        return trimmed
    return trimmed[: NOTE_SUMMARY_MAX_LEN - 1] + "…"


class RecordTodoWorklistActivityUseCase:
    def __init__(
        self,
        todo_repository: TodoRepository,
        outcome_repository: TodoOutcomeDefinitionRepository,
        worklist_state_repository: TodoWorklistStateRepository,
        worklist_query_repository: TodoWorklistQueryRepository,
        activity_repository: ActivityRepository,
        participation_repository: SqlAlchemyParticipationRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._todo_repository = todo_repository
        self._outcome_repository = outcome_repository
        self._worklist_state_repository = worklist_state_repository
        self._worklist_query_repository = worklist_query_repository
        self._activity_repository = activity_repository
        self._participation_repository = participation_repository
        self._authorization = authorization

    def execute(self, command: RecordTodoWorklistActivityCommand) -> TodoWorklistActivityResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_CREATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        note_summary = _truncate_note(command.note)

        todo = self._todo_repository.get_by_id(command.organization_id, command.todo_id)
        if todo is None:
            raise TodoNotFoundError("Todo not found")
        if todo.source_fair_id is None:
            raise TodoMissingSourceFairError("Todo source fair is required for worklist")

        participation = self._participation_repository.get_active_by_customer_and_fair(
            command.organization_id,
            command.customer_id,
            todo.source_fair_id,
        )
        if participation is None:
            raise WorklistCustomerNotInTodoError("Customer is not in this todo worklist")

        outcome = self._outcome_repository.get_by_id(command.organization_id, command.outcome_id)
        if outcome is None:
            raise TodoOutcomeDefinitionNotFoundError("Outcome not found")
        if not outcome.is_active:
            raise TodoOutcomeInactiveError("Outcome is inactive")

        now = datetime.now(tz=UTC)
        activity = Activity.create(
            organization_id=command.organization_id,
            customer_id=command.customer_id,
            contact_id=command.contact_id,
            activity_type=command.activity_type or ActivityType.CALL,
            subject=outcome.name,
            description=command.note.strip(),
            activity_date=now,
            follow_up_date=command.follow_up_at,
            status=ActivityStatus.COMPLETED,
            source=ActivitySource.MANUAL,
            metadata_json={
                "todo_id": str(command.todo_id),
                "outcome_id": str(command.outcome_id),
                "worklist": True,
            },
            now=now,
        )
        saved_activity = self._activity_repository.add(activity)

        existing_state = self._worklist_state_repository.get_by_todo_and_customer(
            command.organization_id,
            command.todo_id,
            command.customer_id,
        )
        if existing_state is None:
            state = TodoWorklistState.create(
                organization_id=command.organization_id,
                todo_id=command.todo_id,
                customer_id=command.customer_id,
                participation_id=participation.id,
                primary_status=outcome.primary_worklist_status,
                last_activity_id=saved_activity.id,
                last_outcome_id=outcome.id,
                follow_up_at=command.follow_up_at,
                last_note_summary=note_summary,
                last_activity_at=now,
                last_actor_user_id=command.user_id,
                action_required=command.action_required,
                data_problem=command.data_problem,
                now=now,
            )
            self._worklist_state_repository.add(state)
        else:
            existing_state.apply_activity_record(
                primary_status=outcome.primary_worklist_status,
                last_activity_id=saved_activity.id,
                last_outcome_id=outcome.id,
                follow_up_at=command.follow_up_at,
                last_note_summary=note_summary,
                last_activity_at=now,
                last_actor_user_id=command.user_id,
                action_required=command.action_required,
                data_problem=command.data_problem,
                now=now,
            )
            self._worklist_state_repository.update(existing_state)

        row = self._worklist_query_repository.get_row_for_customer(
            command.organization_id,
            command.todo_id,
            todo.source_fair_id,
            command.customer_id,
            todo_completed_at=todo.completed_at,
        )
        if row is None:
            raise WorklistCustomerNotInTodoError("Customer is not in this todo worklist")

        progress = self._worklist_query_repository.progress_for_todo(
            command.organization_id,
            command.todo_id,
            todo.source_fair_id,
        )

        next_customer_id = None
        if command.advance_to_next:
            next_list = self._worklist_query_repository.list_for_todo(
                command.organization_id,
                command.todo_id,
                todo.source_fair_id,
                todo_completed_at=todo.completed_at,
                worklist_filter=WorklistFilter.YAPILMADI,
                page=1,
                page_size=1,
                sort_by="company_name",
                sort_dir="asc",
            )
            if next_list.items:
                next_customer_id = next_list.items[0].customer_id

        return TodoWorklistActivityResult(
            activity_id=saved_activity.id,
            worklist_row=worklist_row_to_result(row),
            progress=worklist_progress_to_result(progress),
            next_customer_id=next_customer_id,
        )
