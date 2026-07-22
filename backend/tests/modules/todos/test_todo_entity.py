from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.todos.domain.entities import Todo
from app.modules.todos.domain.exceptions import (
    InvalidTodoCategoryError,
    InvalidTodoStatusError,
    InvalidTodoStatusTransitionError,
    InvalidTodoTitleError,
)
from app.modules.todos.domain.overdue import is_todo_overdue
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


def test_todo_create_rejects_legacy_system_category():
    now = datetime.now(tz=UTC)
    with pytest.raises(InvalidTodoCategoryError):
        Todo.create(
            organization_id=uuid4(),
            title="Valid title",
            created_by=uuid4(),
            category=TodoCategory.TOPLU_MAIL,
            now=now,
        )


def test_todo_update_rejects_legacy_system_category():
    now = datetime.now(tz=UTC)
    todo = Todo.create(
        organization_id=uuid4(),
        title="Original",
        created_by=uuid4(),
        now=now,
    )
    with pytest.raises(InvalidTodoCategoryError):
        todo.update_fields(
            now=now,
            updated_by=uuid4(),
            category=TodoCategory.SMS,
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


def test_todo_complete_sets_done_and_completed_at():
    now = datetime.now(tz=UTC)
    user_id = uuid4()
    todo = Todo.create(
        organization_id=uuid4(),
        title="Complete me",
        created_by=user_id,
        now=now,
    )
    todo.complete(now=now, updated_by=user_id)
    assert todo.status == TodoStatus.DONE
    assert todo.completed_at == now


def test_todo_archive_sets_archived_and_archived_at():
    now = datetime.now(tz=UTC)
    user_id = uuid4()
    todo = Todo.create(
        organization_id=uuid4(),
        title="Archive me",
        created_by=user_id,
        now=now,
    )
    todo.archive(now=now, updated_by=user_id)
    assert todo.status == TodoStatus.ARCHIVED
    assert todo.archived_at == now


def test_todo_update_rejects_done_status():
    now = datetime.now(tz=UTC)
    todo = Todo.create(
        organization_id=uuid4(),
        title="Todo",
        created_by=uuid4(),
        now=now,
    )
    with pytest.raises(InvalidTodoStatusTransitionError):
        todo.update_fields(now=now, updated_by=uuid4(), status=TodoStatus.DONE)


def test_is_todo_overdue_for_past_deadline():
    now = datetime.now(tz=UTC)
    todo = Todo.create(
        organization_id=uuid4(),
        title="Overdue",
        created_by=uuid4(),
        deadline=datetime(2020, 1, 1, tzinfo=UTC),
        now=now,
    )
    assert is_todo_overdue(todo, now=now) is True


def test_is_todo_overdue_false_for_done_and_archived():
    now = datetime.now(tz=UTC)
    past_deadline = datetime(2020, 1, 1, tzinfo=UTC)
    done = Todo.create(
        organization_id=uuid4(),
        title="Done",
        created_by=uuid4(),
        deadline=past_deadline,
        now=now,
    )
    done.complete(now=now, updated_by=uuid4())
    archived = Todo.create(
        organization_id=uuid4(),
        title="Archived",
        created_by=uuid4(),
        deadline=past_deadline,
        now=now,
    )
    archived.archive(now=now, updated_by=uuid4())
    assert is_todo_overdue(done, now=now) is False
    assert is_todo_overdue(archived, now=now) is False
