from app.modules.todos.domain.entities import Todo
from app.modules.todos.infrastructure.persistence.models import TodoModel


def model_to_entity(model: TodoModel) -> Todo:
    return Todo(
        id=model.id,
        organization_id=model.organization_id,
        title=model.title,
        description=model.description,
        status=model.status,
        priority=model.priority,
        category=model.category,
        deadline=model.deadline,
        assignee_user_id=model.assignee_user_id,
        source_fair_id=model.source_fair_id,
        created_by=model.created_by,
        updated_by=model.updated_by,
        archived_at=model.archived_at,
        completed_at=model.completed_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def entity_to_model(todo: Todo) -> TodoModel:
    return TodoModel(
        id=todo.id,
        organization_id=todo.organization_id,
        title=todo.title,
        description=todo.description,
        status=todo.status,
        priority=todo.priority,
        category=todo.category,
        deadline=todo.deadline,
        assignee_user_id=todo.assignee_user_id,
        source_fair_id=todo.source_fair_id,
        created_by=todo.created_by,
        updated_by=todo.updated_by,
        archived_at=todo.archived_at,
        completed_at=todo.completed_at,
        created_at=todo.created_at,
        updated_at=todo.updated_at,
    )


def update_model_from_entity(model: TodoModel, todo: Todo) -> None:
    model.title = todo.title
    model.description = todo.description
    model.status = todo.status
    model.priority = todo.priority
    model.category = todo.category
    model.deadline = todo.deadline
    model.assignee_user_id = todo.assignee_user_id
    model.source_fair_id = todo.source_fair_id
    model.updated_by = todo.updated_by
    model.archived_at = todo.archived_at
    model.completed_at = todo.completed_at
    model.updated_at = todo.updated_at
