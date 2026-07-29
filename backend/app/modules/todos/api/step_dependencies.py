from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.todos.api.dependencies import (
    get_authorization_adapter,
    get_todo_repository,
)
from app.modules.todos.application.delete_todo_step import DeleteTodoStepUseCase
from app.modules.todos.application.list_todo_steps import ListTodoStepsUseCase
from app.modules.todos.application.replace_todo_steps import ReplaceTodoStepsUseCase
from app.modules.todos.application.update_todo_step import UpdateTodoStepUseCase
from app.modules.todos.infrastructure.repositories.todo_repository import SqlAlchemyTodoRepository
from app.modules.todos.infrastructure.repositories.todo_step_repository import (
    SqlAlchemyTodoStepRepository,
)
from app.integrations.kyrox_core.ports import AuthorizationPort


def get_todo_step_repository(db: Session = Depends(get_db)) -> SqlAlchemyTodoStepRepository:
    return SqlAlchemyTodoStepRepository(db)


def get_list_todo_steps_use_case(
    todo_repository: SqlAlchemyTodoRepository = Depends(get_todo_repository),
    step_repository: SqlAlchemyTodoStepRepository = Depends(get_todo_step_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> ListTodoStepsUseCase:
    return ListTodoStepsUseCase(todo_repository, step_repository, authorization)


def get_replace_todo_steps_use_case(
    todo_repository: SqlAlchemyTodoRepository = Depends(get_todo_repository),
    step_repository: SqlAlchemyTodoStepRepository = Depends(get_todo_step_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> ReplaceTodoStepsUseCase:
    return ReplaceTodoStepsUseCase(todo_repository, step_repository, authorization)


def get_update_todo_step_use_case(
    todo_repository: SqlAlchemyTodoRepository = Depends(get_todo_repository),
    step_repository: SqlAlchemyTodoStepRepository = Depends(get_todo_step_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> UpdateTodoStepUseCase:
    return UpdateTodoStepUseCase(todo_repository, step_repository, authorization)


def get_delete_todo_step_use_case(
    todo_repository: SqlAlchemyTodoRepository = Depends(get_todo_repository),
    step_repository: SqlAlchemyTodoStepRepository = Depends(get_todo_step_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> DeleteTodoStepUseCase:
    return DeleteTodoStepUseCase(todo_repository, step_repository, authorization)
