from app.modules.todos.domain.outcome_entities import TodoOutcomeDefinition
from app.modules.todos.domain.worklist_entities import TodoWorklistState
from app.modules.todos.infrastructure.persistence.models import (
    TodoOutcomeDefinitionModel,
    TodoWorklistStateModel,
)


def outcome_model_to_entity(model: TodoOutcomeDefinitionModel) -> TodoOutcomeDefinition:
    return TodoOutcomeDefinition(
        id=model.id,
        organization_id=model.organization_id,
        name=model.name,
        code=model.code,
        description=model.description,
        is_active=model.is_active,
        sort_order=model.sort_order,
        primary_worklist_status=model.primary_worklist_status,
        requires_action=model.requires_action,
        marks_data_problem=model.marks_data_problem,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def outcome_entity_to_model(outcome: TodoOutcomeDefinition) -> TodoOutcomeDefinitionModel:
    return TodoOutcomeDefinitionModel(
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


def update_outcome_model_from_entity(
    model: TodoOutcomeDefinitionModel,
    outcome: TodoOutcomeDefinition,
) -> None:
    model.name = outcome.name
    model.code = outcome.code
    model.description = outcome.description
    model.is_active = outcome.is_active
    model.sort_order = outcome.sort_order
    model.primary_worklist_status = outcome.primary_worklist_status
    model.requires_action = outcome.requires_action
    model.marks_data_problem = outcome.marks_data_problem
    model.updated_at = outcome.updated_at


def worklist_state_model_to_entity(model: TodoWorklistStateModel) -> TodoWorklistState:
    return TodoWorklistState(
        id=model.id,
        organization_id=model.organization_id,
        todo_id=model.todo_id,
        customer_id=model.customer_id,
        participation_id=model.participation_id,
        primary_status=model.primary_status,
        last_activity_id=model.last_activity_id,
        last_outcome_id=model.last_outcome_id,
        follow_up_at=model.follow_up_at,
        last_note_summary=model.last_note_summary,
        last_activity_at=model.last_activity_at,
        last_actor_user_id=model.last_actor_user_id,
        action_required=model.action_required,
        data_problem=model.data_problem,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def worklist_state_entity_to_model(state: TodoWorklistState) -> TodoWorklistStateModel:
    return TodoWorklistStateModel(
        id=state.id,
        organization_id=state.organization_id,
        todo_id=state.todo_id,
        customer_id=state.customer_id,
        participation_id=state.participation_id,
        primary_status=state.primary_status,
        last_activity_id=state.last_activity_id,
        last_outcome_id=state.last_outcome_id,
        follow_up_at=state.follow_up_at,
        last_note_summary=state.last_note_summary,
        last_activity_at=state.last_activity_at,
        last_actor_user_id=state.last_actor_user_id,
        action_required=state.action_required,
        data_problem=state.data_problem,
        created_at=state.created_at,
        updated_at=state.updated_at,
    )


def update_worklist_state_model_from_entity(
    model: TodoWorklistStateModel,
    state: TodoWorklistState,
) -> None:
    model.participation_id = state.participation_id
    model.primary_status = state.primary_status
    model.last_activity_id = state.last_activity_id
    model.last_outcome_id = state.last_outcome_id
    model.follow_up_at = state.follow_up_at
    model.last_note_summary = state.last_note_summary
    model.last_activity_at = state.last_activity_at
    model.last_actor_user_id = state.last_actor_user_id
    model.action_required = state.action_required
    model.data_problem = state.data_problem
    model.updated_at = state.updated_at
