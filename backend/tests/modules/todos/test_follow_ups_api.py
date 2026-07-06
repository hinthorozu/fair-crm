from datetime import UTC, datetime, timedelta
from uuid import uuid4

from tests.conftest_helpers import pagination_from

from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
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

FOLLOW_UPS_BASE = "/api/v1/follow-ups"


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


def _seed_customer(db_session, organization_id, *, name: str = "Acme Co"):
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


def _seed_participation(db_session, organization_id, fair_id, customer_id):
    now = datetime.now(tz=UTC)
    participation = CustomerFairParticipationModel(
        id=uuid4(),
        organization_id=organization_id,
        customer_id=customer_id,
        fair_id=fair_id,
        participation_status="exhibitor",
        created_at=now,
        updated_at=now,
    )
    db_session.add(participation)
    db_session.flush()
    return participation


def _seed_follow_up_scenario(db_session, organization_id, user_id):
    fair = _seed_fair(db_session, organization_id)
    customer_today = _seed_customer(db_session, organization_id, name="Today Corp")
    customer_overdue = _seed_customer(db_session, organization_id, name="Overdue Corp")
    customer_action = _seed_customer(db_session, organization_id, name="Action Corp")
    customer_problem = _seed_customer(db_session, organization_id, name="Problem Corp")

    part_today = _seed_participation(db_session, organization_id, fair.id, customer_today.id)
    part_overdue = _seed_participation(db_session, organization_id, fair.id, customer_overdue.id)
    part_action = _seed_participation(db_session, organization_id, fair.id, customer_action.id)
    part_problem = _seed_participation(db_session, organization_id, fair.id, customer_problem.id)

    now = datetime.now(tz=UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    todo = SqlAlchemyTodoRepository(db_session).add(
        Todo.create(
            organization_id=organization_id,
            title="Fair follow-ups",
            created_by=user_id,
            source_fair_id=fair.id,
            now=now,
        )
    )
    state_repo = SqlAlchemyTodoWorklistStateRepository(db_session)
    outcome_repo = SqlAlchemyTodoOutcomeDefinitionRepository(db_session)
    outcome = outcome_repo.add(
        TodoOutcomeDefinition.create(
            organization_id=organization_id,
            name="Teklif istiyor",
            code="teklif_istiyor",
            primary_worklist_status=OutcomePrimaryWorklistStatus.IN_FOLLOW_UP,
            requires_action=True,
            marks_data_problem=True,
            now=now,
        )
    )

    state_repo.add(
        TodoWorklistState.create(
            organization_id=organization_id,
            todo_id=todo.id,
            customer_id=customer_today.id,
            participation_id=part_today.id,
            primary_status=StoredWorklistPrimaryStatus.IN_FOLLOW_UP,
            last_outcome_id=outcome.id,
            follow_up_at=today_start + timedelta(hours=10),
            last_note_summary="Bugün aranacak",
            now=now,
        )
    )
    state_repo.add(
        TodoWorklistState.create(
            organization_id=organization_id,
            todo_id=todo.id,
            customer_id=customer_overdue.id,
            participation_id=part_overdue.id,
            primary_status=StoredWorklistPrimaryStatus.IN_FOLLOW_UP,
            follow_up_at=today_start - timedelta(days=1),
            last_note_summary="Gecikmiş takip",
            now=now,
        )
    )
    state_repo.add(
        TodoWorklistState.create(
            organization_id=organization_id,
            todo_id=todo.id,
            customer_id=customer_action.id,
            participation_id=part_action.id,
            primary_status=StoredWorklistPrimaryStatus.IN_FOLLOW_UP,
            follow_up_at=today_start + timedelta(days=2),
            action_required=True,
            last_note_summary="Aksiyon gerekli",
            now=now,
        )
    )
    state_repo.add(
        TodoWorklistState.create(
            organization_id=organization_id,
            todo_id=todo.id,
            customer_id=customer_problem.id,
            participation_id=part_problem.id,
            primary_status=StoredWorklistPrimaryStatus.IN_FOLLOW_UP,
            follow_up_at=today_start + timedelta(days=3),
            data_problem=True,
            last_note_summary="Veri problemi",
            now=now,
        )
    )
    db_session.flush()

    return {
        "todo_id": str(todo.id),
        "todo_title": todo.title,
        "customers": {
            "today": customer_today,
            "overdue": customer_overdue,
            "action": customer_action,
            "problem": customer_problem,
        },
    }


def test_follow_ups_default_filter_is_bugun(client, auth_headers, db_session, organization_id, user_id):
    _seed_follow_up_scenario(db_session, organization_id, user_id)
    response = client.get(FOLLOW_UPS_BASE, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["filters"]["filter"] == "bugun"
    assert pagination_from(body)["totalItems"] == 1
    assert body["items"][0]["customer_name"] == "Today Corp"
    assert body["items"][0]["todo_title"] == "Fair follow-ups"


def test_follow_ups_filters(client, auth_headers, db_session, organization_id, user_id):
    _seed_follow_up_scenario(db_session, organization_id, user_id)

    bugun = client.get(f"{FOLLOW_UPS_BASE}?filter=bugun", headers=auth_headers)
    gecmis = client.get(f"{FOLLOW_UPS_BASE}?filter=gecmis", headers=auth_headers)
    action_required = client.get(f"{FOLLOW_UPS_BASE}?filter=action_required", headers=auth_headers)
    data_problem = client.get(f"{FOLLOW_UPS_BASE}?filter=data_problem", headers=auth_headers)
    hepsi = client.get(f"{FOLLOW_UPS_BASE}?filter=hepsi", headers=auth_headers)

    assert pagination_from(bugun.json())["totalItems"] == 1
    assert bugun.json()["items"][0]["customer_name"] == "Today Corp"
    assert pagination_from(gecmis.json())["totalItems"] == 1
    assert gecmis.json()["items"][0]["customer_name"] == "Overdue Corp"
    assert pagination_from(action_required.json())["totalItems"] == 1
    assert action_required.json()["items"][0]["action_required"] is True
    assert pagination_from(data_problem.json())["totalItems"] == 1
    assert data_problem.json()["items"][0]["data_problem"] is True
    assert pagination_from(hepsi.json())["totalItems"] == 4


def test_follow_ups_search_by_customer_name(client, auth_headers, db_session, organization_id, user_id):
    _seed_follow_up_scenario(db_session, organization_id, user_id)
    response = client.get(f"{FOLLOW_UPS_BASE}?filter=hepsi&search=Overdue", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert pagination_from(body)["totalItems"] == 1
    assert body["items"][0]["customer_name"] == "Overdue Corp"
