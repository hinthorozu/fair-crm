from app.modules.activities.application.list_activities_by_customer import (
    ListActivitiesByCustomerUseCase,
)
from app.modules.activities.application.commands import ListActivitiesByCustomerQuery
from app.modules.todos.application.ensure_default_outcomes import EnsureDefaultOutcomesUseCase
from app.modules.todos.application.list_todo_outcomes import ListTodoOutcomesUseCase
from app.modules.todos.application.outcome_commands import EnsureDefaultOutcomesCommand, ListTodoOutcomesQuery
from app.modules.todos.application.worklist_commands import (
    GetTodoWorklistModalContextQuery,
    TodoWorklistModalActivityItem,
    TodoWorklistModalContextResult,
    TodoWorklistModalOutcomeItem,
)
from app.modules.todos.application.worklist_mappers import worklist_row_to_result
from app.modules.todos.domain.exceptions import (
    TodoMissingSourceFairError,
    TodoNotFoundError,
    WorklistCustomerNotInTodoError,
)
from app.modules.todos.domain.ports import TodoRepository
from app.modules.todos.domain.worklist_ports import TodoWorklistQueryRepository


class GetTodoWorklistModalContextUseCase:
    def __init__(
        self,
        todo_repository: TodoRepository,
        worklist_query_repository: TodoWorklistQueryRepository,
        list_outcomes: ListTodoOutcomesUseCase,
        ensure_defaults: EnsureDefaultOutcomesUseCase,
        list_activities: ListActivitiesByCustomerUseCase,
    ) -> None:
        self._todo_repository = todo_repository
        self._worklist_query_repository = worklist_query_repository
        self._list_outcomes = list_outcomes
        self._ensure_defaults = ensure_defaults
        self._list_activities = list_activities

    def execute(self, query: GetTodoWorklistModalContextQuery) -> TodoWorklistModalContextResult:
        todo = self._todo_repository.get_by_id(query.organization_id, query.todo_id)
        if todo is None:
            raise TodoNotFoundError("Todo not found")
        if todo.source_fair_id is None:
            raise TodoMissingSourceFairError("Todo source fair is required for worklist")

        row = self._worklist_query_repository.get_row_for_customer(
            query.organization_id,
            query.todo_id,
            todo.source_fair_id,
            query.customer_id,
            todo_completed_at=todo.completed_at,
        )
        if row is None:
            raise WorklistCustomerNotInTodoError("Customer is not in this todo worklist")

        self._ensure_defaults.execute(
            EnsureDefaultOutcomesCommand(organization_id=query.organization_id)
        )
        outcomes_result = self._list_outcomes.execute(
            ListTodoOutcomesQuery(
                organization_id=query.organization_id,
                is_active=True,
                page=1,
                page_size=100,
                ensure_defaults=False,
            )
        )
        activities_result = self._list_activities.execute(
            ListActivitiesByCustomerQuery(
                organization_id=query.organization_id,
                customer_id=query.customer_id,
                page=1,
                page_size=5,
            )
        )

        return TodoWorklistModalContextResult(
            todo_id=todo.id,
            todo_title=todo.title,
            customer_id=row.customer_id,
            customer_name=row.customer_name,
            city=row.city,
            country=row.country,
            phone_summary=row.phone_summary,
            email_summary=row.email_summary,
            contact_count=row.contact_count,
            worklist_row=worklist_row_to_result(row),
            outcomes=[
                TodoWorklistModalOutcomeItem(
                    id=item.id,
                    name=item.name,
                    code=item.code,
                    primary_worklist_status=item.primary_worklist_status,
                    requires_action=item.requires_action,
                    marks_data_problem=item.marks_data_problem,
                )
                for item in outcomes_result.items
            ],
            recent_activities=[
                TodoWorklistModalActivityItem(
                    id=item.id,
                    subject=item.subject,
                    description=item.description,
                    activity_date=item.activity_date,
                    follow_up_date=item.follow_up_date,
                )
                for item in activities_result.items
            ],
        )
