from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.todos.application.get_todo_worklist_progress import GetTodoWorklistProgressUseCase
from app.modules.todos.application.list_todo_worklist import ListTodoWorklistUseCase
from app.modules.todos.infrastructure.repositories.todo_repository import SqlAlchemyTodoRepository
from app.modules.todos.infrastructure.repositories.worklist_query_repository import (
    SqlAlchemyTodoWorklistQueryRepository,
)


def get_todo_repository(db: Session = Depends(get_db)) -> SqlAlchemyTodoRepository:
    return SqlAlchemyTodoRepository(db)


def get_worklist_query_repository(
    db: Session = Depends(get_db),
) -> SqlAlchemyTodoWorklistQueryRepository:
    return SqlAlchemyTodoWorklistQueryRepository(db)


def get_list_todo_worklist_use_case(
    todo_repository: SqlAlchemyTodoRepository = Depends(get_todo_repository),
    worklist_query_repository: SqlAlchemyTodoWorklistQueryRepository = Depends(
        get_worklist_query_repository
    ),
) -> ListTodoWorklistUseCase:
    return ListTodoWorklistUseCase(todo_repository, worklist_query_repository)


def get_todo_worklist_progress_use_case(
    todo_repository: SqlAlchemyTodoRepository = Depends(get_todo_repository),
    worklist_query_repository: SqlAlchemyTodoWorklistQueryRepository = Depends(
        get_worklist_query_repository
    ),
) -> GetTodoWorklistProgressUseCase:
    return GetTodoWorklistProgressUseCase(todo_repository, worklist_query_repository)
