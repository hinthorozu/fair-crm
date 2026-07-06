from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.todos.domain.entities import Todo
from app.modules.todos.domain.outcome_entities import TodoOutcomeDefinition
from app.modules.todos.domain.outcome_value_objects import OutcomePrimaryWorklistStatus
from app.modules.todos.domain.worklist_entities import TodoWorklistState
from app.modules.todos.domain.worklist_value_objects import StoredWorklistPrimaryStatus
from app.modules.todos.infrastructure.repositories.outcome_definition_repository import (
    SqlAlchemyTodoOutcomeDefinitionRepository,
)
from app.modules.todos.infrastructure.repositories.todo_repository import SqlAlchemyTodoRepository
from app.modules.todos.infrastructure.repositories.worklist_state_repository import (
    SqlAlchemyTodoWorklistStateRepository,
)


def _seed_fair(db_session, organization_id):
    now = datetime.now(tz=UTC)
    fair = FairModel(
        id=uuid4(),
        organization_id=organization_id,
        name="Foodist",
        normalized_name="foodist",
        status="planned",
        created_at=now,
        updated_at=now,
    )
    db_session.add(fair)
    db_session.flush()
    return fair


def _seed_customer(db_session, organization_id):
    now = datetime.now(tz=UTC)
    customer = CustomerModel(
        id=uuid4(),
        organization_id=organization_id,
        display_name="Acme Co",
        normalized_name="acme co",
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    db_session.add(customer)
    db_session.flush()
    return customer


def _seed_todo(db_session, organization_id, *, source_fair_id=None) -> Todo:
    now = datetime.now(tz=UTC)
    todo = Todo.create(
        organization_id=organization_id,
        title="Call fair customers",
        created_by=uuid4(),
        source_fair_id=source_fair_id,
        now=now,
    )
    return SqlAlchemyTodoRepository(db_session).add(todo)


def test_outcome_repository_roundtrip_and_org_isolation(db_session, organization_id, other_organization_id):
    now = datetime.now(tz=UTC)
    repo = SqlAlchemyTodoOutcomeDefinitionRepository(db_session)
    outcome = TodoOutcomeDefinition.create(
        organization_id=organization_id,
        name="Teklif istiyor",
        code="teklif_istiyor",
        primary_worklist_status=OutcomePrimaryWorklistStatus.IN_FOLLOW_UP,
        requires_action=True,
        now=now,
    )
    saved = repo.add(outcome)

    loaded = repo.get_by_id(organization_id, saved.id)
    assert loaded is not None
    assert loaded.code == "teklif_istiyor"
    assert loaded.requires_action is True
    assert repo.get_by_id(other_organization_id, saved.id) is None
    assert repo.get_by_code(organization_id, "teklif_istiyor") is not None


def test_outcome_deactivate_persists(db_session, organization_id):
    now = datetime.now(tz=UTC)
    repo = SqlAlchemyTodoOutcomeDefinitionRepository(db_session)
    outcome = TodoOutcomeDefinition.create(
        organization_id=organization_id,
        name="İlgilenmiyor",
        code="ilgilenmiyor",
        primary_worklist_status=OutcomePrimaryWorklistStatus.CLOSED,
        now=now,
    )
    saved = repo.add(outcome)
    saved.deactivate(now=now)
    updated = repo.update(saved)
    assert updated.is_active is False


def test_worklist_state_repository_roundtrip(db_session, organization_id):
    now = datetime.now(tz=UTC)
    fair = _seed_fair(db_session, organization_id)
    customer = _seed_customer(db_session, organization_id)
    todo = _seed_todo(db_session, organization_id, source_fair_id=fair.id)

    state_repo = SqlAlchemyTodoWorklistStateRepository(db_session)
    state = TodoWorklistState.create(
        organization_id=organization_id,
        todo_id=todo.id,
        customer_id=customer.id,
        primary_status=StoredWorklistPrimaryStatus.IN_FOLLOW_UP,
        now=now,
    )
    saved = state_repo.add(state)

    loaded = state_repo.get_by_todo_and_customer(organization_id, todo.id, customer.id)
    assert loaded is not None
    assert loaded.id == saved.id
    assert loaded.primary_status == StoredWorklistPrimaryStatus.IN_FOLLOW_UP
    assert state_repo.exists_for_todo(organization_id, todo.id) is True
    assert state_repo.count_by_todo(organization_id, todo.id) == 1


def test_worklist_state_unique_per_todo_customer(db_session, organization_id):
    now = datetime.now(tz=UTC)
    fair = _seed_fair(db_session, organization_id)
    customer = _seed_customer(db_session, organization_id)
    todo = _seed_todo(db_session, organization_id, source_fair_id=fair.id)
    state_repo = SqlAlchemyTodoWorklistStateRepository(db_session)

    state_repo.add(
        TodoWorklistState.create(
            organization_id=organization_id,
            todo_id=todo.id,
            customer_id=customer.id,
            primary_status=StoredWorklistPrimaryStatus.CLOSED,
            now=now,
        )
    )

    with pytest.raises(IntegrityError):
        state_repo.add(
            TodoWorklistState.create(
                organization_id=organization_id,
                todo_id=todo.id,
                customer_id=customer.id,
                primary_status=StoredWorklistPrimaryStatus.IN_FOLLOW_UP,
                now=now,
            )
        )
        db_session.flush()


def test_todo_source_fair_id_persists(db_session, organization_id):
    fair = _seed_fair(db_session, organization_id)
    todo = _seed_todo(db_session, organization_id, source_fair_id=fair.id)
    loaded = SqlAlchemyTodoRepository(db_session).get_by_id(organization_id, todo.id)
    assert loaded is not None
    assert loaded.source_fair_id == fair.id
