from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.communication_models import CustomerWebsiteModel
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.scraper.domain.customer_enrichment_state import CustomerEnrichmentScanStatus
from app.modules.scraper.infrastructure.persistence.models import CustomerEnrichmentStateModel
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


def test_list_enrichment_candidates_excludes_pending_merge(db_session, organization_id):
    customer = _seed_customer(db_session, organization_id, display_name="Pending Merge Co")
    now = datetime.now(tz=UTC)
    db_session.add_all(
        [
            CustomerWebsiteModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=customer.id,
                website="https://pending.test",
                is_primary=True,
                created_at=now,
            ),
            CustomerEnrichmentStateModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=customer.id,
                website="https://pending.test",
                last_enrichment_run_id=None,
                last_email_scan_at=now,
                last_email_scan_status=CustomerEnrichmentScanStatus.PENDING_MERGE,
                last_email_found="found@pending.test",
                last_source_url="https://pending.test",
                last_error=None,
                retry_after=None,
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    db_session.commit()

    candidates = list_enrichment_candidates(db_session, organization_id)
    assert all(item.customer_id != customer.id for item in candidates)


def test_list_enrichment_candidates_includes_retry_eligible(db_session, organization_id):
    customer = _seed_customer(db_session, organization_id, display_name="Retry Ready Co")
    now = datetime.now(tz=UTC)
    db_session.add_all(
        [
            CustomerWebsiteModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=customer.id,
                website="https://retry.test",
                is_primary=True,
                created_at=now,
            ),
            CustomerEnrichmentStateModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=customer.id,
                website="https://retry.test",
                last_enrichment_run_id=None,
                last_email_scan_at=now,
                last_email_scan_status=CustomerEnrichmentScanStatus.EMAIL_NOT_FOUND,
                last_email_found=None,
                last_source_url="https://retry.test",
                last_error=None,
                retry_after=now - timedelta(days=1),
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    db_session.commit()

    candidates = list_enrichment_candidates(db_session, organization_id)
    assert any(item.customer_id == customer.id for item in candidates)
