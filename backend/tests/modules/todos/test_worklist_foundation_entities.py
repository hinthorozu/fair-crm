from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.todos.domain.entities import Todo
from app.modules.todos.domain.exceptions import (
    InvalidWorklistPrimaryStatusError,
    TodoSourceFairChangeNotAllowedError,
)
from app.modules.todos.domain.outcome_entities import TodoOutcomeDefinition
from app.modules.todos.domain.outcome_value_objects import OutcomePrimaryWorklistStatus
from app.modules.todos.domain.value_objects import TodoStatus
from app.modules.todos.domain.worklist_entities import TodoWorklistState
from app.modules.todos.domain.worklist_value_objects import (
    StoredWorklistPrimaryStatus,
    WorklistDisplayStatus,
    resolve_worklist_display_status,
)


def test_worklist_state_rejects_not_started_in_db():
    now = datetime.now(tz=UTC)
    with pytest.raises(InvalidWorklistPrimaryStatusError):
        TodoWorklistState.create(
            organization_id=uuid4(),
            todo_id=uuid4(),
            customer_id=uuid4(),
            primary_status="not_started",
            now=now,
        )


def test_worklist_state_accepts_stored_statuses():
    now = datetime.now(tz=UTC)
    for status in StoredWorklistPrimaryStatus:
        state = TodoWorklistState.create(
            organization_id=uuid4(),
            todo_id=uuid4(),
            customer_id=uuid4(),
            primary_status=status,
            now=now,
        )
        assert state.primary_status == status


def test_resolve_worklist_display_status_not_started_when_no_row():
    assert resolve_worklist_display_status(None) == WorklistDisplayStatus.NOT_STARTED


def test_outcome_definition_deactivate():
    now = datetime.now(tz=UTC)
    outcome = TodoOutcomeDefinition.create(
        organization_id=uuid4(),
        name="Ulaşıldı",
        code="ulasildi",
        primary_worklist_status=OutcomePrimaryWorklistStatus.CLOSED,
        now=now,
    )
    outcome.deactivate(now=now)
    assert outcome.is_active is False


def test_todo_source_fair_change_blocked_when_done():
    now = datetime.now(tz=UTC)
    user_id = uuid4()
    todo = Todo.create(
        organization_id=uuid4(),
        title="Done task",
        created_by=user_id,
        source_fair_id=uuid4(),
        now=now,
    )
    todo.complete(now=now, updated_by=user_id)

    with pytest.raises(TodoSourceFairChangeNotAllowedError):
        todo.ensure_source_fair_change_allowed(
            new_source_fair_id=uuid4(),
            has_worklist_states=False,
        )


def test_todo_source_fair_change_blocked_when_worklist_state_exists():
    now = datetime.now(tz=UTC)
    todo = Todo.create(
        organization_id=uuid4(),
        title="Active task",
        created_by=uuid4(),
        source_fair_id=uuid4(),
        now=now,
    )

    with pytest.raises(TodoSourceFairChangeNotAllowedError):
        todo.ensure_source_fair_change_allowed(
            new_source_fair_id=uuid4(),
            has_worklist_states=True,
        )


def test_todo_source_fair_change_allowed_when_open_and_no_state():
    now = datetime.now(tz=UTC)
    new_fair_id = uuid4()
    todo = Todo.create(
        organization_id=uuid4(),
        title="Active task",
        created_by=uuid4(),
        source_fair_id=uuid4(),
        now=now,
    )

    todo.ensure_source_fair_change_allowed(
        new_source_fair_id=new_fair_id,
        has_worklist_states=False,
    )
    todo.update_fields(
        now=now,
        updated_by=uuid4(),
        source_fair_id=new_fair_id,
        set_source_fair_id=True,
        has_worklist_states=False,
    )
    assert todo.source_fair_id == new_fair_id
    assert todo.status == TodoStatus.TODO
