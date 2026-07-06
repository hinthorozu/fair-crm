from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.scraper.domain.customer_enrichment_state import (
    CustomerEnrichmentScanStatus,
    is_eligible_for_enrichment_scan,
)
from app.modules.scraper.dto.enrichment_result_dto import EnrichmentResultDto, SourcedValue
from app.modules.scraper.infrastructure.persistence.models import ScraperRunHistoryModel
from app.modules.scraper.services.customer_enrichment_state_service import (
    load_state_map,
    record_scan_result,
    reset_enrichment_states,
)
from app.modules.scraper.types.scraper_site import ScraperSiteKey


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


def _seed_run(db_session, organization_id) -> ScraperRunHistoryModel:
    now = datetime.now(tz=UTC)
    run = ScraperRunHistoryModel(
        id=uuid4(),
        adapter_key=ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
        status="running",
        started_at=now,
        organization_id=organization_id,
        run_source="enrichment",
    )
    db_session.add(run)
    db_session.flush()
    return run


def test_is_eligible_blocks_pending_merge_and_respects_retry():
    now = datetime(2026, 7, 6, tzinfo=UTC)
    assert is_eligible_for_enrichment_scan(
        status=CustomerEnrichmentScanStatus.PENDING_MERGE,
        retry_after=None,
        website_changed=False,
        now=now,
    ) is False
    assert is_eligible_for_enrichment_scan(
        status=CustomerEnrichmentScanStatus.EMAIL_NOT_FOUND,
        retry_after=now + timedelta(days=1),
        website_changed=False,
        now=now,
    ) is False
    assert is_eligible_for_enrichment_scan(
        status=CustomerEnrichmentScanStatus.EMAIL_NOT_FOUND,
        retry_after=now - timedelta(days=1),
        website_changed=False,
        now=now,
    ) is True
    assert is_eligible_for_enrichment_scan(
        status=CustomerEnrichmentScanStatus.EMAIL_FOUND,
        retry_after=None,
        website_changed=False,
        now=now,
    ) is False
    assert is_eligible_for_enrichment_scan(
        status=CustomerEnrichmentScanStatus.EMAIL_NOT_FOUND,
        retry_after=now + timedelta(days=1),
        website_changed=True,
        now=now,
    ) is True


def test_record_scan_result_persists_email_found_without_placeholder(db_session, organization_id):
    customer = _seed_customer(db_session, organization_id, display_name="Acme")
    run = _seed_run(db_session, organization_id)
    record_scan_result(
        db_session,
        organization_id=organization_id,
        run_id=run.id,
        result=EnrichmentResultDto(
            customer_id=customer.id,
            company_name="Acme",
            website="https://acme.test",
            emails=[SourcedValue(value="info@acme.test", source_url="https://acme.test/contact")],
            status="found",
        ),
    )
    db_session.commit()

    state = load_state_map(db_session, organization_id, [customer.id])[customer.id]
    assert state.last_email_scan_status == CustomerEnrichmentScanStatus.EMAIL_FOUND
    assert state.last_email_found == "info@acme.test"
    assert state.last_source_url == "https://acme.test/contact"
    assert state.retry_after is None


def test_record_scan_result_sets_retry_for_not_found(db_session, organization_id):
    customer = _seed_customer(db_session, organization_id, display_name="Empty")
    run = _seed_run(db_session, organization_id)
    record_scan_result(
        db_session,
        organization_id=organization_id,
        run_id=run.id,
        result=EnrichmentResultDto(
            customer_id=customer.id,
            company_name="Empty",
            website="https://empty.test",
            status="not_found",
        ),
    )
    db_session.commit()

    state = load_state_map(db_session, organization_id, [customer.id])[customer.id]
    assert state.last_email_scan_status == CustomerEnrichmentScanStatus.EMAIL_NOT_FOUND
    assert state.last_email_found is None
    assert state.retry_after is not None


def test_reset_enrichment_states(db_session, organization_id):
    customer = _seed_customer(db_session, organization_id, display_name="Reset Me")
    run = _seed_run(db_session, organization_id)
    record_scan_result(
        db_session,
        organization_id=organization_id,
        run_id=run.id,
        result=EnrichmentResultDto(
            customer_id=customer.id,
            company_name="Reset Me",
            website="https://reset.test",
            status="not_found",
        ),
    )
    db_session.commit()

    deleted = reset_enrichment_states(db_session, organization_id=organization_id, customer_ids=[customer.id])
    db_session.commit()
    assert deleted == 1
    assert load_state_map(db_session, organization_id, [customer.id]) == {}
