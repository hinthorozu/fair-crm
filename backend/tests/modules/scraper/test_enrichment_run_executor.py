"""Tests for enrichment run executor candidate query timing logs and scan state."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.communication_models import CustomerWebsiteModel
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.scraper.core.scraper_run_logger import NullScraperRunLogger
from app.modules.scraper.domain.customer_enrichment_state import CustomerEnrichmentScanStatus
from app.modules.scraper.dto.enrichment_result_dto import EnrichmentResultDto, SourcedValue
from app.modules.scraper.infrastructure.persistence.models import ScraperRunHistoryModel
from app.modules.scraper.services.customer_enrichment_state_service import load_state_map
from app.modules.scraper.services.enrichment_run_executor import execute_enrichment_run
from app.modules.scraper.types.scraper_site import ScraperSiteKey


class _CollectingRunLogger(NullScraperRunLogger):
    def __init__(self) -> None:
        self.entries: list[tuple[str, str, dict | None]] = []

    def info(self, step: str, message: str, *, metadata: dict | None = None) -> None:
        self.entries.append((step, message, metadata))

    def warning(self, step: str, message: str, *, metadata: dict | None = None) -> None:
        self.entries.append((step, message, metadata))


def _seed_website_customer(db_session, organization_id, *, display_name: str, website: str):
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
    db_session.commit()
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


def test_execute_enrichment_run_logs_candidate_query_finished(db_session, organization_id):
    run_logger = _CollectingRunLogger()
    execute_enrichment_run(
        db_session,
        organization_id,
        run_id=uuid4(),
        run_logger=run_logger,
        limit=5,
        requested_fields=["email"],
    )

    steps = [entry[0] for entry in run_logger.entries]
    assert "candidates_query_finished" in steps
    assert "candidates_loaded" in steps

    finished = next(entry for entry in run_logger.entries if entry[0] == "candidates_query_finished")
    assert finished[2] is not None
    assert "duration_ms" in finished[2]
    assert "candidates_count" in finished[2]

    loaded = next(entry for entry in run_logger.entries if entry[0] == "candidates_loaded")
    assert loaded[2] is not None
    assert "candidate_count" in loaded[2]


def test_execute_enrichment_run_dry_run_writes_no_scan_state(db_session, organization_id):
    customer = _seed_website_customer(
        db_session,
        organization_id,
        display_name="Dry Run Co",
        website="https://dry-run.example",
    )
    run = _seed_run(db_session, organization_id)

    def _fetcher(_url: str) -> str:
        return "<html><body>Contact info@dry-run.example</body></html>"

    execute_enrichment_run(
        db_session,
        organization_id,
        run_id=run.id,
        run_logger=_CollectingRunLogger(),
        limit=1,
        requested_fields=["email"],
        customer_ids=[customer.id],
        fetcher=_fetcher,
        dry_run=True,
    )
    db_session.commit()

    assert load_state_map(db_session, organization_id, [customer.id]) == {}


def test_execute_enrichment_run_found_email_does_not_set_email_found_without_batch(
    db_session, organization_id, monkeypatch
):
    customer = _seed_website_customer(
        db_session,
        organization_id,
        display_name="Found No Batch Co",
        website="https://found-no-batch.example",
    )
    run = _seed_run(db_session, organization_id)

    def _fake_enrich(candidate, **_kwargs):
        return EnrichmentResultDto(
            customer_id=candidate.customer_id,
            company_name=candidate.company_name,
            website=candidate.website,
            emails=[SourcedValue(value="info@found-no-batch.example", source_url=candidate.website)],
            status="found",
        )

    monkeypatch.setattr(
        "app.modules.scraper.services.enrichment_run_executor.enrich_customer_website",
        _fake_enrich,
    )

    execute_enrichment_run(
        db_session,
        organization_id,
        run_id=run.id,
        run_logger=_CollectingRunLogger(),
        limit=1,
        requested_fields=["email"],
        customer_ids=[customer.id],
        dry_run=False,
    )
    db_session.commit()

    state = load_state_map(db_session, organization_id, [customer.id])[customer.id]
    assert state.last_email_scan_status == CustomerEnrichmentScanStatus.NOT_SCANNED
    assert state.last_email_found == "info@found-no-batch.example"
