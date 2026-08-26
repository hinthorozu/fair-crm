"""Adversarial tenant-isolation tests for todo worklist derived joins."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
from app.modules.todos.domain.entities import Todo
from app.modules.todos.infrastructure.persistence.models import (
    TodoOutcomeDefinitionModel,
    TodoWorklistStateModel,
)
from app.modules.todos.infrastructure.repositories.todo_repository import SqlAlchemyTodoRepository
from tests.conftest_helpers import pagination_from


def _seed_customer(db_session, organization_id, *, name: str) -> CustomerModel:
    now = datetime.now(tz=UTC)
    customer = CustomerModel(
        id=uuid4(),
        organization_id=organization_id,
        display_name=name,
        normalized_name=name.lower(),
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    db_session.add(customer)
    db_session.flush()
    return customer


def _seed_fair(db_session, organization_id, *, name: str = "Owner Fair") -> FairModel:
    now = datetime.now(tz=UTC)
    fair = FairModel(
        id=uuid4(),
        organization_id=organization_id,
        name=name,
        normalized_name=name.lower(),
        status="planned",
        created_at=now,
        updated_at=now,
    )
    db_session.add(fair)
    db_session.flush()
    return fair


def _seed_todo(db_session, organization_id, user_id, *, title: str, source_fair_id=None):
    return SqlAlchemyTodoRepository(db_session).add(
        Todo.create(
            organization_id=organization_id,
            title=title,
            created_by=user_id,
            source_fair_id=source_fair_id,
            now=datetime.now(tz=UTC),
        )
    )


def _seed_participation(db_session, organization_id, *, fair_id, customer_id):
    now = datetime.now(tz=UTC)
    row = CustomerFairParticipationModel(
        id=uuid4(),
        organization_id=organization_id,
        customer_id=customer_id,
        fair_id=fair_id,
        participation_status="exhibitor",
        created_at=now,
        updated_at=now,
    )
    db_session.add(row)
    db_session.flush()
    return row


def _seed_foreign_outcome(db_session, organization_id, *, name: str):
    now = datetime.now(tz=UTC)
    row = TodoOutcomeDefinitionModel(
        id=uuid4(),
        organization_id=organization_id,
        name=name,
        code=f"foreign_{uuid4().hex}",
        description=None,
        is_active=True,
        sort_order=0,
        primary_worklist_status="in_follow_up",
        requires_action=False,
        marks_data_problem=False,
        created_at=now,
        updated_at=now,
    )
    db_session.add(row)
    db_session.flush()
    return row


def _seed_state(
    db_session,
    organization_id,
    *,
    todo_id,
    customer_id,
    participation_id=None,
    last_outcome_id=None,
    follow_up_at=None,
):
    now = datetime.now(tz=UTC)
    row = TodoWorklistStateModel(
        id=uuid4(),
        organization_id=organization_id,
        todo_id=todo_id,
        customer_id=customer_id,
        participation_id=participation_id,
        primary_status="in_follow_up",
        last_activity_id=None,
        last_outcome_id=last_outcome_id,
        follow_up_at=follow_up_at,
        last_note_summary=None,
        last_activity_at=None,
        last_actor_user_id=None,
        action_required=False,
        data_problem=False,
        created_at=now,
        updated_at=now,
    )
    db_session.add(row)
    db_session.flush()
    return row


def test_worklist_does_not_follow_foreign_participation_customer(
    client,
    auth_headers,
    db_session,
    organization_id,
    other_organization_id,
    user_id,
):
    fair = _seed_fair(db_session, organization_id)
    todo = _seed_todo(
        db_session,
        organization_id,
        user_id,
        title="Owner Worklist",
        source_fair_id=fair.id,
    )
    foreign_customer = _seed_customer(
        db_session,
        other_organization_id,
        name="FOREIGN WORKLIST CUSTOMER",
    )
    _seed_participation(
        db_session,
        organization_id,
        fair_id=fair.id,
        customer_id=foreign_customer.id,
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/todos/{todo.id}/worklist?filter=hepsi",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert "FOREIGN WORKLIST CUSTOMER" not in response.text
    assert pagination_from(response.json())["totalItems"] == 0


def test_worklist_does_not_expose_foreign_outcome_name(
    client,
    auth_headers,
    db_session,
    organization_id,
    other_organization_id,
    user_id,
):
    fair = _seed_fair(db_session, organization_id)
    customer = _seed_customer(db_session, organization_id, name="Owner Worklist Customer")
    participation = _seed_participation(
        db_session,
        organization_id,
        fair_id=fair.id,
        customer_id=customer.id,
    )
    todo = _seed_todo(
        db_session,
        organization_id,
        user_id,
        title="Owner Worklist",
        source_fair_id=fair.id,
    )
    foreign_outcome = _seed_foreign_outcome(
        db_session,
        other_organization_id,
        name="FOREIGN WORKLIST OUTCOME",
    )
    _seed_state(
        db_session,
        organization_id,
        todo_id=todo.id,
        customer_id=customer.id,
        participation_id=participation.id,
        last_outcome_id=foreign_outcome.id,
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/todos/{todo.id}/worklist?filter=hepsi",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert "FOREIGN WORKLIST OUTCOME" not in response.text
    assert pagination_from(response.json())["totalItems"] == 1
    assert response.json()["items"][0]["last_outcome_name"] is None


def test_follow_ups_do_not_follow_foreign_customer_or_todo(
    client,
    auth_headers,
    db_session,
    organization_id,
    other_organization_id,
    user_id,
):
    foreign_customer = _seed_customer(
        db_session,
        other_organization_id,
        name="FOREIGN FOLLOWUP CUSTOMER",
    )
    foreign_todo = _seed_todo(
        db_session,
        other_organization_id,
        user_id,
        title="FOREIGN FOLLOWUP TODO",
    )
    today = datetime.now(tz=UTC).replace(hour=10, minute=0, second=0, microsecond=0)
    _seed_state(
        db_session,
        organization_id,
        todo_id=foreign_todo.id,
        customer_id=foreign_customer.id,
        follow_up_at=today,
    )
    db_session.commit()

    response = client.get("/api/v1/follow-ups", headers=auth_headers)
    assert response.status_code == 200
    assert "FOREIGN FOLLOWUP CUSTOMER" not in response.text
    assert "FOREIGN FOLLOWUP TODO" not in response.text
    assert pagination_from(response.json())["totalItems"] == 0


def test_follow_ups_do_not_expose_foreign_outcome_name(
    client,
    auth_headers,
    db_session,
    organization_id,
    other_organization_id,
    user_id,
):
    customer = _seed_customer(db_session, organization_id, name="Owner Followup Customer")
    todo = _seed_todo(db_session, organization_id, user_id, title="Owner Followup Todo")
    foreign_outcome = _seed_foreign_outcome(
        db_session,
        other_organization_id,
        name="FOREIGN FOLLOWUP OUTCOME",
    )
    today = datetime.now(tz=UTC).replace(hour=10, minute=0, second=0, microsecond=0)
    _seed_state(
        db_session,
        organization_id,
        todo_id=todo.id,
        customer_id=customer.id,
        last_outcome_id=foreign_outcome.id,
        follow_up_at=today,
    )
    db_session.commit()

    response = client.get("/api/v1/follow-ups", headers=auth_headers)
    assert response.status_code == 200
    assert "FOREIGN FOLLOWUP OUTCOME" not in response.text
    assert pagination_from(response.json())["totalItems"] == 1
    assert response.json()["items"][0]["last_outcome_name"] is None
