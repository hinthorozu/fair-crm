from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.communication_models import (
    CustomerEmailModel,
    CustomerWebsiteModel,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
from app.modules.scraper.domain.customer_enrichment_state import CustomerEnrichmentScanStatus
from app.modules.scraper.infrastructure.persistence.models import CustomerEnrichmentStateModel
from app.modules.scraper.services.enrichment_candidate_service import list_enrichment_candidates


def _seed_customer(
    db_session,
    organization_id,
    *,
    display_name: str,
    address: str | None = None,
    city: str | None = None,
) -> CustomerModel:
    now = datetime.now(tz=UTC)
    customer = CustomerModel(
        id=uuid4(),
        organization_id=organization_id,
        display_name=display_name,
        normalized_name=display_name.lower(),
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        address=address,
        city=city,
        created_at=now,
        updated_at=now,
    )
    db_session.add(customer)
    db_session.flush()
    return customer


def _seed_website(db_session, organization_id, customer_id, website: str) -> None:
    now = datetime.now(tz=UTC)
    db_session.add(
        CustomerWebsiteModel(
            id=uuid4(),
            organization_id=organization_id,
            customer_id=customer_id,
            website=website,
            is_primary=True,
            created_at=now,
        )
    )


def test_list_enrichment_candidates_includes_website_without_email(db_session, organization_id):
    customer = _seed_customer(db_session, organization_id, display_name="Website Only Co")
    _seed_website(db_session, organization_id, customer.id, "https://website-only.test")
    db_session.commit()

    candidates = list_enrichment_candidates(db_session, organization_id)
    assert any(item.customer_id == customer.id for item in candidates)


def test_list_enrichment_candidates_excludes_customers_with_email(db_session, organization_id):
    customer = _seed_customer(db_session, organization_id, display_name="Has Email Co")
    now = datetime.now(tz=UTC)
    _seed_website(db_session, organization_id, customer.id, "https://has-email.test")
    db_session.add(
        CustomerEmailModel(
            id=uuid4(),
            organization_id=organization_id,
            customer_id=customer.id,
            email="info@has-email.test",
            is_primary=True,
            created_at=now,
        )
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


def _seed_enrichment_state(
    db_session,
    organization_id,
    customer_id,
    *,
    website: str,
    status: str,
    retry_after=None,
) -> None:
    """Seed a prior scan state with the SAME website as the customer's current one, so the
    `is_customer_scan_eligible` "website_changed" escape hatch does not mask the status check
    being tested (a changed website is intentionally always re-scanned regardless of status)."""
    now = datetime.now(tz=UTC)
    db_session.add(
        CustomerEnrichmentStateModel(
            id=uuid4(),
            organization_id=organization_id,
            customer_id=customer_id,
            website=website,
            last_email_scan_status=status,
            retry_after=retry_after,
            created_at=now,
            updated_at=now,
        )
    )


def test_fair_scoped_candidates_ignore_previous_state_but_org_wide_still_blocks(
    db_session, organization_id
):
    """Manual fair-scoped enrichment must re-check exactly this fair's participants,
    regardless of any earlier org-wide scan outcome (pending_merge, failed/email_not_found
    retry cooldowns). Org-wide dedup must stay untouched."""
    now = datetime.now(tz=UTC)
    fair = FairModel(
        id=uuid4(),
        organization_id=organization_id,
        name="Repeat Scan Fair",
        normalized_name="repeat scan fair",
        status="planned",
        created_at=now,
        updated_at=now,
    )
    db_session.add(fair)
    db_session.flush()

    pending_merge_customer = _seed_customer(db_session, organization_id, display_name="Pending Merge Co")
    failed_customer = _seed_customer(db_session, organization_id, display_name="Failed Co")
    already_emailed_customer = _seed_customer(db_session, organization_id, display_name="Already Emailed Co")

    for customer, website in (
        (pending_merge_customer, "https://pending-merge.test"),
        (failed_customer, "https://failed.test"),
        (already_emailed_customer, "https://already-emailed.test"),
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
                customer_id=customer.id,
                fair_id=fair.id,
                participation_status="exhibitor",
                created_at=now,
                updated_at=now,
            )
        )

    db_session.add(
        CustomerEmailModel(
            id=uuid4(),
            organization_id=organization_id,
            customer_id=already_emailed_customer.id,
            email="info@already-emailed.test",
            is_primary=True,
            created_at=now,
        )
    )

    _seed_enrichment_state(
        db_session,
        organization_id,
        pending_merge_customer.id,
        website="https://pending-merge.test",
        status=CustomerEnrichmentScanStatus.PENDING_MERGE.value,
    )
    _seed_enrichment_state(
        db_session,
        organization_id,
        failed_customer.id,
        website="https://failed.test",
        status=CustomerEnrichmentScanStatus.FAILED.value,
        retry_after=now + timedelta(days=7),
    )
    db_session.commit()

    fair_candidates = {item.customer_id for item in list_enrichment_candidates(
        db_session, organization_id, fair_id=fair.id, ignore_previous_scan_state=True
    )}
    assert fair_candidates == {pending_merge_customer.id, failed_customer.id}, (
        "manual fair-scoped run (ignore_previous_scan_state=True) must ignore pending_merge/failed "
        "retry state for its own participants"
    )

    fair_candidates_default = {item.customer_id for item in list_enrichment_candidates(
        db_session, organization_id, fair_id=fair.id
    )}
    assert fair_candidates_default == set(), (
        "fair-scoped queries must still respect scan state by default (ignore_previous_scan_state=False)"
    )

    org_candidates = {item.customer_id for item in list_enrichment_candidates(db_session, organization_id)}
    assert pending_merge_customer.id not in org_candidates, "org-wide run must still respect pending_merge"
    assert failed_customer.id not in org_candidates, "org-wide run must still respect the failed retry cooldown"
    assert already_emailed_customer.id not in org_candidates
    assert already_emailed_customer.id not in fair_candidates, (
        "a customer with a real CRM email must stay excluded when include_existing_email=False"
    )


def test_list_enrichment_candidates_includes_customers_with_email_when_flag_set(
    db_session, organization_id
):
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

    default_candidates = list_enrichment_candidates(db_session, organization_id)
    assert all(item.customer_id != customer.id for item in default_candidates)

    included_candidates = list_enrichment_candidates(
        db_session, organization_id, include_existing_email=True
    )
    assert any(item.customer_id == customer.id for item in included_candidates)


def test_fair_scoped_include_existing_email_adds_emailed_participants(db_session, organization_id):
    now = datetime.now(tz=UTC)
    fair = FairModel(
        id=uuid4(),
        organization_id=organization_id,
        name="Email Include Fair",
        normalized_name="email include fair",
        status="planned",
        created_at=now,
        updated_at=now,
    )
    db_session.add(fair)
    db_session.flush()

    no_email_customer = _seed_customer(db_session, organization_id, display_name="No Email Co")
    emailed_customer = _seed_customer(db_session, organization_id, display_name="Emailed Co")
    for customer, website in (
        (no_email_customer, "https://no-email.test"),
        (emailed_customer, "https://emailed.test"),
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
                customer_id=customer.id,
                fair_id=fair.id,
                participation_status="exhibitor",
                created_at=now,
                updated_at=now,
            )
        )
    db_session.add(
        CustomerEmailModel(
            id=uuid4(),
            organization_id=organization_id,
            customer_id=emailed_customer.id,
            email="info@emailed.test",
            is_primary=True,
            created_at=now,
        )
    )
    db_session.commit()

    default_fair_candidates = {
        item.customer_id
        for item in list_enrichment_candidates(
            db_session, organization_id, fair_id=fair.id, ignore_previous_scan_state=True
        )
    }
    assert default_fair_candidates == {no_email_customer.id}

    include_email_fair_candidates = {
        item.customer_id
        for item in list_enrichment_candidates(
            db_session,
            organization_id,
            fair_id=fair.id,
            ignore_previous_scan_state=True,
            include_existing_email=True,
        )
    }
    assert include_email_fair_candidates == {no_email_customer.id, emailed_customer.id}


def test_list_enrichment_candidates_filters_by_company_name_contains(db_session, organization_id):
    sdk = _seed_customer(db_session, organization_id, display_name="SDK Yazılım A.Ş.")
    other = _seed_customer(db_session, organization_id, display_name="Acme Trading")
    _seed_website(db_session, organization_id, sdk.id, "https://sdk.test")
    _seed_website(db_session, organization_id, other.id, "https://acme.test")
    db_session.commit()

    candidates = list_enrichment_candidates(
        db_session, organization_id, company_name="SDK", company_name_match="contains"
    )
    assert {item.customer_id for item in candidates} == {sdk.id}


def test_list_enrichment_candidates_filters_by_company_name_starts_with(db_session, organization_id):
    starts = _seed_customer(db_session, organization_id, display_name="SDK Yazılım")
    contains = _seed_customer(db_session, organization_id, display_name="Super SDK Ltd")
    _seed_website(db_session, organization_id, starts.id, "https://starts.test")
    _seed_website(db_session, organization_id, contains.id, "https://contains.test")
    db_session.commit()

    candidates = list_enrichment_candidates(
        db_session, organization_id, company_name="SDK", company_name_match="starts_with"
    )
    assert {item.customer_id for item in candidates} == {starts.id}


def test_list_enrichment_candidates_filters_by_address_contains(db_session, organization_id):
    istanbul = _seed_customer(
        db_session,
        organization_id,
        display_name="Istanbul Co",
        address="Kadıköy, İstanbul",
    )
    ankara = _seed_customer(
        db_session,
        organization_id,
        display_name="Ankara Co",
        address="Çankaya",
        city="Ankara",
    )
    city_only = _seed_customer(
        db_session,
        organization_id,
        display_name="City Istanbul Co",
        city="İstanbul",
    )
    _seed_website(db_session, organization_id, istanbul.id, "https://istanbul.test")
    _seed_website(db_session, organization_id, ankara.id, "https://ankara.test")
    _seed_website(db_session, organization_id, city_only.id, "https://city-istanbul.test")
    db_session.commit()

    candidates = list_enrichment_candidates(
        db_session, organization_id, address_contains="İstanbul"
    )
    assert {item.customer_id for item in candidates} == {istanbul.id, city_only.id}


def test_list_enrichment_candidates_combines_filters_and_limit(db_session, organization_id):
    now = datetime.now(tz=UTC)
    fair = FairModel(
        id=uuid4(),
        organization_id=organization_id,
        name="Filter Fair",
        normalized_name="filter fair",
        status="planned",
        created_at=now,
        updated_at=now,
    )
    db_session.add(fair)
    db_session.flush()

    match = _seed_customer(
        db_session,
        organization_id,
        display_name="SDK Istanbul",
        address="Maslak İstanbul",
    )
    name_only = _seed_customer(
        db_session,
        organization_id,
        display_name="SDK Ankara",
        address="Çankaya Ankara",
    )
    outsider = _seed_customer(
        db_session,
        organization_id,
        display_name="SDK Outsider",
        address="İstanbul",
    )
    for customer, website in (
        (match, "https://match.test"),
        (name_only, "https://name-only.test"),
        (outsider, "https://outsider.test"),
    ):
        _seed_website(db_session, organization_id, customer.id, website)
    for customer in (match, name_only):
        db_session.add(
            CustomerFairParticipationModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=customer.id,
                fair_id=fair.id,
                participation_status="exhibitor",
                created_at=now,
                updated_at=now,
            )
        )
    db_session.commit()

    candidates = list_enrichment_candidates(
        db_session,
        organization_id,
        fair_id=fair.id,
        company_name="SDK",
        company_name_match="contains",
        address_contains="İstanbul",
        limit=10,
    )
    assert {item.customer_id for item in candidates} == {match.id}
