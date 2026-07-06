from datetime import UTC, datetime, timedelta
from uuid import uuid4

from tests.conftest_helpers import pagination_from

from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
from app.modules.todos.domain.outcome_entities import TodoOutcomeDefinition
from app.modules.todos.domain.outcome_value_objects import OutcomePrimaryWorklistStatus
from app.modules.todos.domain.worklist_entities import TodoWorklistState
from app.modules.todos.domain.worklist_value_objects import StoredWorklistPrimaryStatus
from app.modules.todos.infrastructure.repositories.outcome_definition_repository import (
    SqlAlchemyTodoOutcomeDefinitionRepository,
)
from app.modules.todos.domain.entities import Todo
from app.modules.todos.infrastructure.repositories.todo_repository import SqlAlchemyTodoRepository
from app.modules.todos.infrastructure.repositories.worklist_state_repository import (
    SqlAlchemyTodoWorklistStateRepository,
)

WORKLIST_BASE = "/api/v1/todos/{todo_id}/worklist"


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


def _seed_participation(db_session, organization_id, fair_id, customer_id, *, created_at=None):
    now = created_at or datetime.now(tz=UTC)
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


def _seed_worklist_scenario(db_session, organization_id, user_id):
    fair = _seed_fair(db_session, organization_id)
    customer_a = _seed_customer(db_session, organization_id, name="Alpha Corp")
    customer_b = _seed_customer(db_session, organization_id, name="Beta Corp")
    customer_c = _seed_customer(db_session, organization_id, name="Gamma Corp")
    part_a = _seed_participation(db_session, organization_id, fair.id, customer_a.id)
    part_b = _seed_participation(db_session, organization_id, fair.id, customer_b.id)
    part_c = _seed_participation(db_session, organization_id, fair.id, customer_c.id)

    now = datetime.now(tz=UTC)
    todo = SqlAlchemyTodoRepository(db_session).add(
        Todo.create(
            organization_id=organization_id,
            title="Fair worklist",
            created_by=user_id,
            source_fair_id=fair.id,
            now=now,
        )
    )
    todo_id = str(todo.id)
    state_repo = SqlAlchemyTodoWorklistStateRepository(db_session)
    outcome_repo = SqlAlchemyTodoOutcomeDefinitionRepository(db_session)
    outcome = outcome_repo.add(
        TodoOutcomeDefinition.create(
            organization_id=organization_id,
            name="Teklif istiyor",
            code="teklif_istiyor",
            primary_worklist_status=OutcomePrimaryWorklistStatus.IN_FOLLOW_UP,
            requires_action=True,
            now=now,
        )
    )
    state_repo.add(
        TodoWorklistState.create(
            organization_id=organization_id,
            todo_id=todo.id,
            customer_id=customer_b.id,
            participation_id=part_b.id,
            primary_status=StoredWorklistPrimaryStatus.IN_FOLLOW_UP,
            last_outcome_id=outcome.id,
            last_note_summary="Teklif gönderilecek",
            now=now,
            action_required=True,
        )
    )
    state_repo.add(
        TodoWorklistState.create(
            organization_id=organization_id,
            todo_id=todo.id,
            customer_id=customer_c.id,
            participation_id=part_c.id,
            primary_status=StoredWorklistPrimaryStatus.CLOSED,
            now=now,
        )
    )
    db_session.flush()

    return {
        "fair": fair,
        "todo_id": todo_id,
        "customers": {
            "alpha": customer_a,
            "beta": customer_b,
            "gamma": customer_c,
        },
        "participations": {
            "alpha": part_a,
            "beta": part_b,
            "gamma": part_c,
        },
        "outcome": outcome,
    }


def test_worklist_default_filter_is_yapilmadi(client, auth_headers, db_session, organization_id, user_id):
    scenario = _seed_worklist_scenario(db_session, organization_id, user_id)
    response = client.get(
        WORKLIST_BASE.format(todo_id=scenario["todo_id"]),
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["filters"]["filter"] == "yapilmadi"
    assert pagination_from(body)["totalItems"] == 1
    assert body["items"][0]["customer_name"] == "Alpha Corp"
    assert body["items"][0]["primary_status"] == "not_started"


def test_worklist_filters(client, auth_headers, db_session, organization_id, user_id):
    scenario = _seed_worklist_scenario(db_session, organization_id, user_id)
    todo_id = scenario["todo_id"]
    base = WORKLIST_BASE.format(todo_id=todo_id)

    yapilmadi = client.get(f"{base}?filter=yapilmadi", headers=auth_headers)
    takipte = client.get(f"{base}?filter=takipte", headers=auth_headers)
    kapandi = client.get(f"{base}?filter=konu_kapandi", headers=auth_headers)
    hepsi = client.get(f"{base}?filter=hepsi", headers=auth_headers)

    assert pagination_from(yapilmadi.json())["totalItems"] == 1
    assert pagination_from(takipte.json())["totalItems"] == 1
    assert takipte.json()["items"][0]["primary_status"] == "in_follow_up"
    assert takipte.json()["items"][0]["last_outcome_name"] == "Teklif istiyor"
    assert pagination_from(kapandi.json())["totalItems"] == 1
    assert kapandi.json()["items"][0]["primary_status"] == "closed"
    assert pagination_from(hepsi.json())["totalItems"] == 3


def test_worklist_progress_counts(client, auth_headers, db_session, organization_id, user_id):
    scenario = _seed_worklist_scenario(db_session, organization_id, user_id)
    response = client.get(
        f"{WORKLIST_BASE.format(todo_id=scenario['todo_id'])}/progress",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["not_started"] == 1
    assert body["in_follow_up"] == 1
    assert body["closed"] == 1
    assert body["not_started"] + body["in_follow_up"] + body["closed"] == body["total"]


def test_worklist_dynamic_customer_without_state_row(client, auth_headers, db_session, organization_id, user_id):
    scenario = _seed_worklist_scenario(db_session, organization_id, user_id)
    new_customer = _seed_customer(db_session, organization_id, name="Delta Corp")
    _seed_participation(db_session, organization_id, scenario["fair"].id, new_customer.id)
    db_session.flush()

    response = client.get(
        f"{WORKLIST_BASE.format(todo_id=scenario['todo_id'])}?filter=yapilmadi",
        headers=auth_headers,
    )
    assert response.status_code == 200
    names = {item["customer_name"] for item in response.json()["items"]}
    assert names == {"Alpha Corp", "Delta Corp"}


def test_worklist_missing_source_fair_returns_400(client, auth_headers):
    create = client.post(
        "/api/v1/todos",
        json={"title": "No fair"},
        headers=auth_headers,
    )
    assert create.status_code == 201
    todo_id = create.json()["id"]

    response = client.get(WORKLIST_BASE.format(todo_id=todo_id), headers=auth_headers)
    assert response.status_code == 400


def test_worklist_org_isolation(client, auth_headers, db_session, organization_id, other_organization_id, user_id):
    scenario = _seed_worklist_scenario(db_session, organization_id, user_id)
    other_headers = {**auth_headers, "X-Organization-Id": str(other_organization_id)}
    response = client.get(
        WORKLIST_BASE.format(todo_id=scenario["todo_id"]),
        headers=other_headers,
    )
    assert response.status_code == 404


def test_worklist_search(client, auth_headers, db_session, organization_id, user_id):
    scenario = _seed_worklist_scenario(db_session, organization_id, user_id)
    response = client.get(
        f"{WORKLIST_BASE.format(todo_id=scenario['todo_id'])}?filter=hepsi&search=Beta",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert pagination_from(body)["totalItems"] == 1
    assert body["items"][0]["customer_name"] == "Beta Corp"


def test_worklist_added_after_completion(client, auth_headers, db_session, organization_id, user_id):
    fair = _seed_fair(db_session, organization_id)
    early_customer = _seed_customer(db_session, organization_id, name="Early Corp")
    _seed_participation(db_session, organization_id, fair.id, early_customer.id)

    now = datetime.now(tz=UTC)
    todo_repo = SqlAlchemyTodoRepository(db_session)
    todo = todo_repo.add(
        Todo.create(
            organization_id=organization_id,
            title="Completed fair task",
            created_by=user_id,
            source_fair_id=fair.id,
            now=now,
        )
    )
    todo.complete(now=now, updated_by=user_id)
    todo_repo.update(todo)
    todo_id = str(todo.id)

    late_customer = _seed_customer(db_session, organization_id, name="Late Corp")
    _seed_participation(
        db_session,
        organization_id,
        fair.id,
        late_customer.id,
        created_at=datetime.now(tz=UTC) + timedelta(hours=1),
    )
    db_session.flush()

    response = client.get(
        f"{WORKLIST_BASE.format(todo_id=todo_id)}?filter=hepsi",
        headers=auth_headers,
    )
    assert response.status_code == 200
    flags = {item["customer_name"]: item["added_after_completion"] for item in response.json()["items"]}
    assert flags["Early Corp"] is False
    assert flags["Late Corp"] is True


def test_worklist_inactive_outcome_still_resolves(client, auth_headers, db_session, organization_id, user_id):
    fair = _seed_fair(db_session, organization_id)
    customer = _seed_customer(db_session, organization_id, name="Outcome Corp")
    part = _seed_participation(db_session, organization_id, fair.id, customer.id)
    now = datetime.now(tz=UTC)
    todo = SqlAlchemyTodoRepository(db_session).add(
        Todo.create(
            organization_id=organization_id,
            title="Outcome resolve",
            created_by=user_id,
            source_fair_id=fair.id,
            now=now,
        )
    )
    todo_id = str(todo.id)
    outcome_repo = SqlAlchemyTodoOutcomeDefinitionRepository(db_session)
    outcome = outcome_repo.add(
        TodoOutcomeDefinition.create(
            organization_id=organization_id,
            name="Eski sonuç",
            code="eski_sonuc",
            primary_worklist_status=OutcomePrimaryWorklistStatus.CLOSED,
            now=now,
        )
    )
    outcome.deactivate(now=now)
    outcome_repo.update(outcome)
    SqlAlchemyTodoWorklistStateRepository(db_session).add(
        TodoWorklistState.create(
            organization_id=organization_id,
            todo_id=todo.id,
            customer_id=customer.id,
            participation_id=part.id,
            primary_status=StoredWorklistPrimaryStatus.CLOSED,
            last_outcome_id=outcome.id,
            now=now,
        )
    )
    db_session.flush()

    response = client.get(
        f"{WORKLIST_BASE.format(todo_id=todo_id)}?filter=konu_kapandi",
        headers=auth_headers,
    )
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["last_outcome_name"] == "Eski sonuç"
