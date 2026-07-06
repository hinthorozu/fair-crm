from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.todos.domain.entities import Todo
from app.modules.todos.domain.exceptions import (
    InvalidTodoCategoryError,
    InvalidTodoStatusError,
    InvalidTodoTitleError,
)
from app.modules.todos.domain.value_objects import TodoCategory, TodoPriority, TodoStatus


def test_todo_create_with_defaults():
    now = datetime.now(tz=UTC)
    user_id = uuid4()
    org_id = uuid4()

    todo = Todo.create(
        organization_id=org_id,
        title="Follow up with client",
        created_by=user_id,
        now=now,
    )

    assert todo.title == "Follow up with client"
    assert todo.status == TodoStatus.TODO
    assert todo.priority == TodoPriority.NORMAL
    assert todo.category == TodoCategory.GENEL_GOREV
    assert todo.created_by == user_id
    assert todo.updated_by is None
    assert todo.assignee_user_id is None


def test_todo_title_required():
    now = datetime.now(tz=UTC)
    with pytest.raises(InvalidTodoTitleError):
        Todo.create(
            organization_id=uuid4(),
            title="   ",
            created_by=uuid4(),
            now=now,
        )


def test_todo_invalid_status():
    now = datetime.now(tz=UTC)
    with pytest.raises(InvalidTodoStatusError):
        Todo.create(
            organization_id=uuid4(),
            title="Valid title",
            created_by=uuid4(),
            status="invalid",
            now=now,
        )


def test_todo_invalid_category():
    now = datetime.now(tz=UTC)
    with pytest.raises(InvalidTodoCategoryError):
        Todo.create(
            organization_id=uuid4(),
            title="Valid title",
            created_by=uuid4(),
            category="müşteri_güncelleme",
            now=now,
        )


def test_todo_update_fields():
    now = datetime.now(tz=UTC)
    user_id = uuid4()
    todo = Todo.create(
        organization_id=uuid4(),
        title="Original",
        created_by=user_id,
        now=now,
    )

    later = datetime.now(tz=UTC)
    updater_id = uuid4()
    todo.update_fields(
        now=later,
        updated_by=updater_id,
        title="Updated title",
        status=TodoStatus.IN_PROGRESS,
        category=TodoCategory.ARAMA,
        set_description=True,
        description="Details",
    )

    assert todo.title == "Updated title"
    assert todo.status == TodoStatus.IN_PROGRESS
    assert todo.category == TodoCategory.ARAMA
    assert todo.description == "Details"
    assert todo.updated_by == updater_id
