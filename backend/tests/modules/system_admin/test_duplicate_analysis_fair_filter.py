"""Duplicate customer analysis optional fair scope."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.communication_models import CustomerEmailModel
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel


def _create_fair(client, auth_headers, name: str) -> str:
    res = client.post(
        "/api/v1/fairs",
        headers=auth_headers,
        json={
            "name": name,
            "location": "Istanbul",
            "start_date": "2026-06-01",
            "end_date": "2026-06-03",
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


def _seed_customer_with_email(db_session, organization_id, *, display_name: str, email: str):
    now = datetime.now(tz=UTC)
    customer_id = uuid4()
    customer = CustomerModel(
        id=customer_id,
        organization_id=organization_id,
        display_name=display_name,
        normalized_name=display_name.lower(),
        customer_type=CustomerType.EXHIBITOR.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    db_session.add(customer)
    db_session.flush()
    db_session.add(
        CustomerEmailModel(
            id=uuid4(),
            organization_id=organization_id,
            customer_id=customer_id,
            email=email,
            is_primary=True,
            created_at=now,
        )
    )
    db_session.flush()
    return customer_id


def _seed_participation(db_session, organization_id, *, fair_id, customer_id):
    now = datetime.now(tz=UTC)
    db_session.add(
        CustomerFairParticipationModel(
            id=uuid4(),
            organization_id=organization_id,
            fair_id=UUID(str(fair_id)),
            customer_id=customer_id,
            is_active=True,
            participation_status="exhibitor",
            created_at=now,
            updated_at=now,
        )
    )
    db_session.flush()


def _run_duplicate_analysis(client, auth_headers, *, group_by: str, fair_id: str | None = None):
    payload: dict = {"group_by": group_by}
    if fair_id:
        payload["fair_id"] = fair_id
    create = client.post(
        "/api/v1/admin/data-operations/duplicate_customer_analysis/run",
        headers=auth_headers,
        json=payload,
    )
    assert create.status_code == 202
    run_id = create.json()["id"]
    detail = client.get(f"/api/v1/admin/data-operations/runs/{run_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "completed"
    return detail.json()


def test_duplicate_analysis_fair_filter_scopes_customers(
    client, auth_headers, db_session, organization_id
):
    shared_email = "fair-scope-dup@example.com"
    intermob_id = _create_fair(client, auth_headers, "Intermob Fair Filter")
    other_fair_id = _create_fair(client, auth_headers, "Other Fair Filter")

    inter_a = _seed_customer_with_email(
        db_session, organization_id, display_name="Intermob Dup A", email=shared_email
    )
    inter_b = _seed_customer_with_email(
        db_session, organization_id, display_name="Intermob Dup B", email=shared_email
    )
    other_same_name = _seed_customer_with_email(
        db_session, organization_id, display_name="Intermob Dup A Other Fair", email="other@example.com"
    )

    _seed_participation(db_session, organization_id, fair_id=intermob_id, customer_id=inter_a)
    _seed_participation(db_session, organization_id, fair_id=intermob_id, customer_id=inter_b)
    _seed_participation(db_session, organization_id, fair_id=other_fair_id, customer_id=other_same_name)
    db_session.commit()

    global_run = _run_duplicate_analysis(client, auth_headers, group_by="email")
    assert global_run["summary_json"]["duplicate_groups"] >= 1
    assert global_run["summary_json"].get("fair_id") is None
    assert global_run["summary_json"].get("fair_name") is None

    scoped_run = _run_duplicate_analysis(
        client, auth_headers, group_by="email", fair_id=intermob_id
    )
    summary = scoped_run["summary_json"]
    assert summary["fair_id"] == intermob_id
    assert summary["fair_name"] == "Intermob Fair Filter"
    assert summary["total_customers"] == 2
    assert summary["duplicate_groups"] == 1
    assert summary["customers_in_duplicate_groups"] == 2

    groups = client.get(
        f"/api/v1/admin/data-operations/runs/{scoped_run['id']}/dataset/duplicate-groups",
        headers=auth_headers,
        params={"page": 1, "page_size": 25},
    ).json()["items"]
    assert len(groups) == 1

    customers = client.get(
        f"/api/v1/admin/data-operations/runs/{scoped_run['id']}/dataset/duplicate-customers",
        headers=auth_headers,
        params={"page": 1, "page_size": 50},
    ).json()["items"]
    member_ids = {row["id"] for row in customers}
    assert str(other_same_name) not in member_ids
    assert str(inter_a) in member_ids
    assert str(inter_b) in member_ids
