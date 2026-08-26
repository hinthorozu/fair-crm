"""Adversarial tenant-isolation tests for participation-derived parent joins."""

from uuid import UUID

from sqlalchemy import select

from app.modules.customers.infrastructure.persistence.communication_query_helpers import (
    has_live_fair_participation_exists,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
from tests.conftest_helpers import pagination_from


def _create_customer(client, headers, name: str) -> str:
    response = client.post(
        "/api/v1/customers",
        headers=headers,
        json={"display_name": name, "status": "active"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_fair(client, headers, name: str) -> str:
    response = client.post(
        "/api/v1/fairs",
        headers=headers,
        json={"name": name, "status": "planned"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_participation(client, headers, customer_id: str, fair_id: str) -> str:
    response = client.post(
        "/api/v1/fair-participations",
        headers=headers,
        json={
            "customer_id": customer_id,
            "fair_id": fair_id,
            "hall": "A",
            "stand": "1",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_customer_participation_list_does_not_follow_foreign_fair(
    client,
    auth_headers,
    db_session,
    other_organization_id,
):
    owner_customer_id = _create_customer(client, auth_headers, "Owner Customer")
    owner_fair_id = _create_fair(client, auth_headers, "Owner Fair")
    participation_id = _create_participation(
        client,
        auth_headers,
        owner_customer_id,
        owner_fair_id,
    )

    other_headers = {**auth_headers, "X-Organization-Id": str(other_organization_id)}
    foreign_fair_id = _create_fair(client, other_headers, "FOREIGN FAIR")

    participation = db_session.get(CustomerFairParticipationModel, UUID(participation_id))
    assert participation is not None
    participation.fair_id = UUID(foreign_fair_id)
    db_session.commit()

    response = client.get(
        f"/api/v1/customers/{owner_customer_id}/fair-participations",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert "FOREIGN FAIR" not in response.text
    assert pagination_from(response.json())["totalItems"] == 0


def test_fair_participant_list_does_not_follow_foreign_customer(
    client,
    auth_headers,
    db_session,
    other_organization_id,
):
    owner_customer_id = _create_customer(client, auth_headers, "Temporary Owner Customer")
    owner_fair_id = _create_fair(client, auth_headers, "Owner Fair")
    participation_id = _create_participation(
        client,
        auth_headers,
        owner_customer_id,
        owner_fair_id,
    )

    other_headers = {**auth_headers, "X-Organization-Id": str(other_organization_id)}
    foreign_customer_id = _create_customer(client, other_headers, "FOREIGN CUSTOMER")

    participation = db_session.get(CustomerFairParticipationModel, UUID(participation_id))
    assert participation is not None
    participation.customer_id = UUID(foreign_customer_id)
    db_session.commit()

    response = client.get(
        f"/api/v1/fairs/{owner_fair_id}/participants",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert "FOREIGN CUSTOMER" not in response.text
    assert pagination_from(response.json())["totalItems"] == 0


def test_live_participation_helper_ignores_foreign_organization_rows(
    client,
    auth_headers,
    db_session,
    other_organization_id,
):
    owner_customer_id = _create_customer(client, auth_headers, "Helper Owner Customer")

    other_headers = {**auth_headers, "X-Organization-Id": str(other_organization_id)}
    foreign_customer_id = _create_customer(client, other_headers, "Foreign Helper Customer")
    foreign_fair_id = _create_fair(client, other_headers, "Foreign Helper Fair")
    foreign_participation_id = _create_participation(
        client,
        other_headers,
        foreign_customer_id,
        foreign_fair_id,
    )

    participation = db_session.get(
        CustomerFairParticipationModel,
        UUID(foreign_participation_id),
    )
    assert participation is not None
    participation.customer_id = UUID(owner_customer_id)
    db_session.commit()

    has_live = db_session.scalar(
        select(has_live_fair_participation_exists())
        .select_from(CustomerModel)
        .where(CustomerModel.id == UUID(owner_customer_id))
    )
    assert not has_live
