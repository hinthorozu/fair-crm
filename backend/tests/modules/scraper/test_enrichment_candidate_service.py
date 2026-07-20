from datetime import UTC, datetime
from uuid import uuid4

from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.communication_models import (
    CustomerEmailModel,
    CustomerWebsiteModel,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
from app.modules.scraper.services.enrichment_candidate_service import list_enrichment_candidates


def _seed_customer(db_session, organization_id, *, display_name: str) -> CustomerModel:
    now = datetime.now(tz=UTC)
    customer = CustomerModel(
        id=uuid4(),
        organization_id=organization_id,
        display_name=display_name,
        normalized_name=display_name.lower(),
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    db_session.add(customer)
    db_session.flush()
    return customer


def test_list_enrichment_candidates_includes_website_without_email(db_session, organization_id):
    customer = _seed_customer(db_session, organization_id, display_name="Website Only Co")
    now = datetime.now(tz=UTC)
    db_session.add(
        CustomerWebsiteModel(
            id=uuid4(),
            organization_id=organization_id,
            customer_id=customer.id,
            website="https://website-only.test",
            is_primary=True,
            created_at=now,
        )
    )
    db_session.commit()

    candidates = list_enrichment_candidates(db_session, organization_id)
    assert any(item.customer_id == customer.id for item in candidates)


def test_list_enrichment_candidates_excludes_customers_with_email(db_session, organization_id):
    customer = _seed_customer(db_session, organization_id, display_name="Has Email Co")
    now = datetime.now(tz=UTC)
    db_session.add_all(
        [
            CustomerWebsiteModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=customer.id,
                website="https://has-email.test",
                is_primary=True,
                created_at=now,
            ),
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=customer.id,
                email="info@has-email.test",
                is_primary=True,
                created_at=now,
            ),
        ]
    )
    db_session.commit()

    candidates = list_enrichment_candidates(db_session, organization_id)
    assert all(item.customer_id != customer.id for item in candidates)


def test_list_enrichment_candidates_for_fair_excludes_non_participants(db_session, organization_id):
    now = datetime.now(tz=UTC)
    fair = FairModel(
        id=uuid4(),
        organization_id=organization_id,
        name="Scoped Fair",
        normalized_name="scoped fair",
        status="planned",
        created_at=now,
        updated_at=now,
    )
    db_session.add(fair)
    db_session.flush()

    participant = _seed_customer(db_session, organization_id, display_name="Fair Participant")
    outsider = _seed_customer(db_session, organization_id, display_name="Outsider")
    for customer, website in (
        (participant, "https://participant.test"),
        (outsider, "https://outsider.test"),
    ):
        db_session.add(
            CustomerWebsiteModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=customer.id,
                website=website,
                is_primary=True,
                created_at=now,
            )
        )
    db_session.add(
        CustomerFairParticipationModel(
            id=uuid4(),
            organization_id=organization_id,
            customer_id=participant.id,
            fair_id=fair.id,
            participation_status="exhibitor",
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()

    fair_candidates = list_enrichment_candidates(db_session, organization_id, fair_id=fair.id)
    assert [item.customer_id for item in fair_candidates] == [participant.id]

    org_candidates = list_enrichment_candidates(db_session, organization_id)
    assert {item.customer_id for item in org_candidates} == {participant.id, outsider.id}
