from app.modules.todos.application.outcome_commands import TodoOutcomeListResultDto, TodoOutcomeResult
from app.modules.todos.domain.outcome_entities import TodoOutcomeDefinition
from app.modules.todos.domain.worklist_ports import OutcomeListResult


def outcome_to_result(outcome: TodoOutcomeDefinition) -> TodoOutcomeResult:
    return TodoOutcomeResult(
        id=outcome.id,
        organization_id=outcome.organization_id,
        name=outcome.name,
        code=outcome.code,
        description=outcome.description,
        is_active=outcome.is_active,
        sort_order=outcome.sort_order,
        primary_worklist_status=outcome.primary_worklist_status,
        requires_action=outcome.requires_action,
        marks_data_problem=outcome.marks_data_problem,
        created_at=outcome.created_at,
        updated_at=outcome.updated_at,
    )


def outcome_list_to_dto(result: OutcomeListResult) -> TodoOutcomeListResultDto:
    return TodoOutcomeListResultDto(
        items=[outcome_to_result(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )
