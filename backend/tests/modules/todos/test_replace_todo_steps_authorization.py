"""Authorization regression tests for replacing todo steps."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import ForbiddenError
from app.modules.todos.application.replace_todo_steps import ReplaceTodoStepsUseCase
from app.modules.todos.application.step_commands import ReplaceTodoStepsCommand


def _command() -> ReplaceTodoStepsCommand:
    return ReplaceTodoStepsCommand(
        organization_id=uuid4(),
        user_id=uuid4(),
        access_token="token",
        todo_id=uuid4(),
        steps=[],
    )


def test_replace_todo_steps_requires_update_permission():
    todo_repository = MagicMock()
    step_repository = MagicMock()
    authorization = MagicMock()
    authorization.check_permission.return_value = False
    use_case = ReplaceTodoStepsUseCase(todo_repository, step_repository, authorization)
    command = _command()

    with pytest.raises(ForbiddenError):
        use_case.execute(command)

    authorization.check_permission.assert_called_once_with(
        organization_id=command.organization_id,
        user_id=command.user_id,
        permission_code="fair_crm.todos.update",
        access_token=command.access_token,
    )
    todo_repository.get_by_id.assert_not_called()
    step_repository.list_by_todo.assert_not_called()


def test_replace_todo_steps_with_update_permission_reaches_repositories():
    todo_repository = MagicMock()
    todo_repository.get_by_id.return_value = object()
    step_repository = MagicMock()
    step_repository.list_by_todo.return_value = []
    authorization = MagicMock()
    authorization.check_permission.return_value = True
    use_case = ReplaceTodoStepsUseCase(todo_repository, step_repository, authorization)
    command = _command()

    result = use_case.execute(command)

    assert result == []
    authorization.check_permission.assert_called_once_with(
        organization_id=command.organization_id,
        user_id=command.user_id,
        permission_code="fair_crm.todos.update",
        access_token=command.access_token,
    )
    todo_repository.get_by_id.assert_called_once_with(command.organization_id, command.todo_id)
    step_repository.list_by_todo.assert_called_once_with(command.organization_id, command.todo_id)
    step_repository.delete_ids.assert_called_once_with(command.organization_id, command.todo_id, [])
