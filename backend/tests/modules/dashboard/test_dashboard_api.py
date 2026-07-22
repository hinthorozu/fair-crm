"""Dashboard summary API tests."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.modules.activities.infrastructure.persistence.models import ActivityModel
from app.modules.customers.domain.value_objects import CustomerStatus
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.mail_send_operations.domain.value_objects import MailSendOperationStatus
from app.modules.mail_send_operations.domain.worker_constants import SENDING_TIMEOUT_ERROR_CODE
from app.modules.mail_send_operations.infrastructure.persistence.models import MailSendOperationModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
from app.modules.todos.domain.worklist_value_objects import StoredWorklistPrimaryStatus
from app.modules.todos.infrastructure.persistence.models import TodoModel, TodoWorklistStateModel


def _seed_customer(db_session, organization_id, *, name: str = "Acme Corp") -> CustomerModel:
    now = datetime.now(tz=UTC)
    customer = CustomerModel(
        id=uuid4(),
        organization_id=organization_id,
        display_name=name,
        normalized_name=name.lower(),
        customer_type="exhibitor",
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    db_session.add(customer)
    db_session.flush()
    return customer


def _seed_fair(db_session, organization_id, *, name: str = "Demo Fair") -> FairModel:
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


def test_dashboard_summary_returns_empty_sections(client, auth_headers, organization_id):
    response = client.get("/api/v1/dashboard/summary", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["overview"]["totalCustomers"] == 0
    assert body["overview"]["totalFairs"] == 0
    assert body["overview"]["openTodos"] == 0
    assert body["taskSummary"]["notStarted"] == 0
    assert body["recentActivities"] == []
    assert body["fairSummaries"] == []
    assert body["mailStatus"]["queued"] == 0


def test_dashboard_summary_counts(client, auth_headers, db_session, organization_id, user_id):
    now = datetime.now(tz=UTC)
    today_noon = now.replace(hour=12, minute=0, second=0, microsecond=0)

    customer = _seed_customer(db_session, organization_id)
    fair = _seed_fair(db_session, organization_id)

    participation = CustomerFairParticipationModel(
        id=uuid4(),
        organization_id=organization_id,
        customer_id=customer.id,
        fair_id=fair.id,
        created_at=now,
        updated_at=now,
    )
    db_session.add(participation)

    todo = TodoModel(
        id=uuid4(),
        organization_id=organization_id,
        title="Follow up",
        status="todo",
        priority="normal",
        category="genel_gorev",
        source_fair_id=fair.id,
        created_by=user_id,
        created_at=now,
        updated_at=now,
    )
    db_session.add(todo)

    activity = ActivityModel(
        id=uuid4(),
        organization_id=organization_id,
        customer_id=customer.id,
        activity_type="call",
        subject="Intro call",
        description="Short note about the call",
        activity_date=now,
        status="completed",
        source="manual",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(activity)

    worklist = TodoWorklistStateModel(
        id=uuid4(),
        organization_id=organization_id,
        todo_id=todo.id,
        customer_id=customer.id,
        participation_id=participation.id,
        primary_status=StoredWorklistPrimaryStatus.IN_FOLLOW_UP,
        last_activity_id=activity.id,
        last_note_summary="Follow up next week",
        last_activity_at=now,
        follow_up_at=today_noon,
        created_at=now,
        updated_at=now,
    )
    db_session.add(worklist)

    db_session.add(
        MailSendOperationModel(
            id=uuid4(),
            organization_id=organization_id,
            source_type="fair_bulk_email",
            status=MailSendOperationStatus.SENT.value,
            priority=100,
            recipient_email="a@example.com",
            subject="Hello",
            fair_id=fair.id,
            customer_id=customer.id,
            retry_count=0,
            max_retry_count=3,
            operation_logs=[],
            created_at=now,
            updated_at=now,
            sent_at=now,
        )
    )
    db_session.add(
        MailSendOperationModel(
            id=uuid4(),
            organization_id=organization_id,
            source_type="fair_bulk_email",
            status=MailSendOperationStatus.FAILED.value,
            priority=100,
            recipient_email="b@example.com",
            subject="Hello",
            fair_id=fair.id,
            customer_id=customer.id,
            retry_count=0,
            max_retry_count=3,
            error_code=SENDING_TIMEOUT_ERROR_CODE,
            operation_logs=[],
            created_at=now,
            updated_at=now,
            failed_at=now,
        )
    )
    db_session.add(
        MailSendOperationModel(
            id=uuid4(),
            organization_id=organization_id,
            source_type="fair_bulk_email",
            status=MailSendOperationStatus.QUEUED.value,
            priority=100,
            recipient_email="c@example.com",
            subject="Queued",
            retry_count=0,
            max_retry_count=3,
            operation_logs=[],
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()

    response = client.get("/api/v1/dashboard/summary", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()

    assert body["overview"]["totalCustomers"] == 1
    assert body["overview"]["totalFairs"] == 1
    assert body["overview"]["openTodos"] == 1
    assert body["overview"]["todayFollowUps"] == 1
    assert body["overview"]["sentMails"] == 1
    assert body["overview"]["failedMails"] == 1

    assert body["taskSummary"]["inFollowUp"] == 1
    assert body["taskSummary"]["notStarted"] == 0
    assert body["taskSummary"]["closed"] == 0

    assert len(body["recentActivities"]) == 1
    assert body["recentActivities"][0]["customerName"] == "Acme Corp"
    assert body["recentActivities"][0]["activityType"] == "call"

    assert len(body["fairSummaries"]) == 1
    fair_summary = body["fairSummaries"][0]
    assert fair_summary["fairName"] == "Demo Fair"
    assert fair_summary["customerCount"] == 1
    assert fair_summary["customersWithActivity"] == 1
    assert fair_summary["customersWithMailSent"] == 1
    assert fair_summary["failedMailCount"] == 1

    assert body["mailStatus"]["queued"] == 1
    assert body["mailStatus"]["sent"] == 1
    assert body["mailStatus"]["failed"] == 1
    assert body["mailStatus"]["timeout"] == 1


def test_dashboard_summary_org_isolation(
    client,
    auth_headers,
    db_session,
    organization_id,
    other_organization_id,
):
    _seed_customer(db_session, organization_id, name="Org A")
    _seed_customer(db_session, other_organization_id, name="Org B")
    db_session.commit()

    response = client.get("/api/v1/dashboard/summary", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["overview"]["totalCustomers"] == 1


def test_dashboard_summary_overdue_follow_ups(client, auth_headers, db_session, organization_id, user_id):
    now = datetime.now(tz=UTC)
    yesterday = now - timedelta(days=1)
    customer = _seed_customer(db_session, organization_id)
    fair = _seed_fair(db_session, organization_id)
    participation = CustomerFairParticipationModel(
        id=uuid4(),
        organization_id=organization_id,
        customer_id=customer.id,
        fair_id=fair.id,
        created_at=now,
        updated_at=now,
    )
    todo = TodoModel(
        id=uuid4(),
        organization_id=organization_id,
        title="Overdue task",
        status="todo",
        priority="normal",
        category="genel_gorev",
        source_fair_id=fair.id,
        created_by=user_id,
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([participation, todo])
    db_session.add(
        TodoWorklistStateModel(
            id=uuid4(),
            organization_id=organization_id,
            todo_id=todo.id,
            customer_id=customer.id,
            participation_id=participation.id,
            primary_status=StoredWorklistPrimaryStatus.IN_FOLLOW_UP,
            follow_up_at=yesterday,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()

    response = client.get("/api/v1/dashboard/summary", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["taskSummary"]["overdueFollowUps"] == 1


def test_dashboard_summary_unauthenticated(client, organization_id):
    response = client.get(
        "/api/v1/dashboard/summary",
        headers={"X-Organization-Id": str(organization_id)},
    )
    assert response.status_code == 401


def test_dashboard_summary_response_uses_camel_case_aliases(client, auth_headers):
    response = client.get("/api/v1/dashboard/summary", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "taskSummary" in body
    assert "recentActivities" in body
    assert "fairSummaries" in body
    assert "mailStatus" in body
    assert "totalCustomers" in body["overview"]


def test_dashboard_summary_mapper_accepts_snake_case_fields(db_session, organization_id):
    from app.modules.dashboard.application.mappers import dashboard_summary_to_response
    from app.modules.dashboard.domain.summary import (
        DashboardMailStatusSummary,
        DashboardOverviewCards,
        DashboardSummary,
        DashboardTaskSummary,
    )

    summary = DashboardSummary(
        overview=DashboardOverviewCards(
            total_customers=0,
            total_fairs=0,
            open_todos=0,
            today_follow_ups=0,
            sent_mails=0,
            failed_mails=0,
        ),
        task_summary=DashboardTaskSummary(
            not_started=0,
            in_follow_up=0,
            closed=0,
            overdue_follow_ups=0,
        ),
        recent_activities=[],
        fair_summaries=[],
        mail_status=DashboardMailStatusSummary(
            queued=0,
            sending=0,
            sent=0,
            failed=0,
            timeout=0,
        ),
    )
    response = dashboard_summary_to_response(summary)
    dumped = response.model_dump(by_alias=True)
    assert dumped["taskSummary"]["notStarted"] == 0


def test_dashboard_summary_allows_null_customer_recent_activity(
    client, auth_headers, db_session, organization_id
):
    """Independent Todo completion creates task_completed with customer_id NULL."""
    now = datetime.now(tz=UTC)
    db_session.add(
        ActivityModel(
            id=uuid4(),
            organization_id=organization_id,
            customer_id=None,
            activity_type="task_completed",
            subject="Görev tamamlandı: Independent",
            description="Dashboard null-customer note",
            activity_date=now,
            status="completed",
            source="system",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()

    response = client.get("/api/v1/dashboard/summary", headers=auth_headers)
    assert response.status_code == 200
    recent = response.json()["recentActivities"]
    assert len(recent) == 1
    assert recent[0]["customerId"] is None
    assert recent[0]["customerName"] == "—"
    assert recent[0]["activityType"] == "task_completed"
    assert "Dashboard null-customer note" in (recent[0]["noteSummary"] or "")
