"""Tests for standard bulk enrichment candidate preview run logs."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.communication_models import CustomerWebsiteModel
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
from app.modules.scraper.core.scraper_run_logger import NullScraperRunLogger
from app.modules.scraper.dto.enrichment_result_dto import EnrichmentResultDto
from app.modules.scraper.services.enrichment_candidate_service import EnrichmentCandidate
from app.modules.scraper.services.enrichment_run_candidate_preview_logger import (
    enrichment_candidate_display_name,
    log_bulk_enrichment_candidate_preview,
)
from app.modules.scraper.services.enrichment_run_executor import execute_enrichment_run


class _CollectingRunLogger(NullScraperRunLogger):
    def __init__(self) -> None:
        self.entries: list[tuple[str, str, dict | None]] = []

    def info(self, step: str, message: str, *, metadata: dict | None = None) -> None:
        self.entries.append((step, message, metadata))

    def warning(self, step: str, message: str, *, metadata: dict | None = None) -> None:
        self.entries.append((step, message, metadata))


def _seed_customer(db_session, organization_id, *, display_name: str, website: str) -> CustomerModel:
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
    db_session.flush()
    return customer


def _not_found_result(candidate: EnrichmentCandidate) -> EnrichmentResultDto:
    return EnrichmentResultDto(
        customer_id=candidate.customer_id,
        company_name=candidate.company_name,
        website=candidate.website,
        status="not_found",
        social_links={"instagram": None, "facebook": None, "linkedin": None, "youtube": None},
    )


def test_enrichment_candidate_display_name_falls_back_to_website():
    candidate = EnrichmentCandidate(
        customer_id=uuid4(),
        company_name="   ",
        website="https://example.test",
    )
    assert enrichment_candidate_display_name(candidate) == "https://example.test"


def test_log_bulk_enrichment_candidate_preview_writes_count_and_numbered_list():
    run_logger = _CollectingRunLogger()
    candidates = [
        EnrichmentCandidate(uuid4(), "ABC Gıda", "https://abc.test"),
        EnrichmentCandidate(uuid4(), "XYZ Tarım", "https://xyz.test"),
    ]
    log_bulk_enrichment_candidate_preview(run_logger, candidates)

    messages = [entry[1] for entry in run_logger.entries]
    steps = [entry[0] for entry in run_logger.entries]
    assert messages[0] == "2 firma işleme alınacak."
    assert steps[1] == "candidates_list_header"
    assert messages[2] == "1. ABC Gıda"
    assert messages[3] == "2. XYZ Tarım"
    assert messages[4] == "Tarama başlatılıyor..."


def test_execute_enrichment_run_logs_preview_before_scan(monkeypatch, db_session, organization_id):
    _seed_customer(db_session, organization_id, display_name="ABC Gıda", website="https://abc.test")
    _seed_customer(db_session, organization_id, display_name="XYZ Tarım", website="https://xyz.test")
    db_session.commit()

    def _fake_enrich(candidate, **kwargs):
        return _not_found_result(candidate)

    monkeypatch.setattr(
        "app.modules.scraper.services.enrichment_run_executor.enrich_customer_website",
        _fake_enrich,
    )

    run_logger = _CollectingRunLogger()
    execute_enrichment_run(
        db_session,
        organization_id,
        run_logger=run_logger,
        requested_fields=["email"],
    )

    messages = [entry[1] for entry in run_logger.entries]
    assert "2 firma işleme alınacak." in messages
    assert "1. ABC Gıda" in messages
    assert "2. XYZ Tarım" in messages
    assert "Tarama başlatılıyor..." in messages
    assert "ABC Gıda taranıyor..." in messages
    assert "ABC Gıda tamamlandı." in messages

    count_idx = messages.index("2 firma işleme alınacak.")
    header_idx = messages.index("İşleme alınacak firmalar:")
    scan_start_idx = messages.index("Tarama başlatılıyor...")
    first_scan_idx = messages.index("ABC Gıda taranıyor...")
    assert count_idx < header_idx < scan_start_idx < first_scan_idx


def test_execute_enrichment_run_respects_limit_in_preview_list(monkeypatch, db_session, organization_id):
    for index in range(5):
        _seed_customer(
            db_session,
            organization_id,
            display_name=f"Firma {index + 1}",
            website=f"https://firma-{index + 1}.test",
        )
    db_session.commit()

    monkeypatch.setattr(
        "app.modules.scraper.services.enrichment_run_executor.enrich_customer_website",
        lambda candidate, **kwargs: _not_found_result(candidate),
    )

    run_logger = _CollectingRunLogger()
    execute_enrichment_run(
        db_session,
        organization_id,
        run_logger=run_logger,
        limit=2,
        requested_fields=["email"],
    )

    preview_messages = [
        message
        for step, message, _metadata in run_logger.entries
        if step == "candidate_preview"
    ]
    assert len(preview_messages) == 2
    assert any(message.startswith("1. Firma") for message in preview_messages)
    assert any(message.startswith("2. Firma") for message in preview_messages)
    assert "5 firma işleme alınacak." not in [entry[1] for entry in run_logger.entries]
    assert "2 firma işleme alınacak." in [entry[1] for entry in run_logger.entries]


def test_execute_enrichment_run_fair_scoped_uses_same_preview_logs(monkeypatch, db_session, organization_id):
    now = datetime.now(tz=UTC)
    fair = FairModel(
        id=uuid4(),
        organization_id=organization_id,
        name="Preview Fair",
        normalized_name="preview fair",
        status="planned",
        created_at=now,
        updated_at=now,
    )
    db_session.add(fair)
    db_session.flush()

    participant = _seed_customer(
        db_session,
        organization_id,
        display_name="Fair Participant",
        website="https://fair-participant.test",
    )
    outsider = _seed_customer(
        db_session,
        organization_id,
        display_name="Outsider",
        website="https://outsider.test",
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

    monkeypatch.setattr(
        "app.modules.scraper.services.enrichment_run_executor.enrich_customer_website",
        lambda candidate, **kwargs: _not_found_result(candidate),
    )

    run_logger = _CollectingRunLogger()
    execute_enrichment_run(
        db_session,
        organization_id,
        run_logger=run_logger,
        fair_id=fair.id,
        ignore_previous_scan_state=True,
        requested_fields=["email"],
    )

    preview_messages = [
        message for step, message, _metadata in run_logger.entries if step == "candidate_preview"
    ]
    assert preview_messages == ["1. Fair Participant"]
    assert "1 firma işleme alınacak." in [entry[1] for entry in run_logger.entries]
    assert outsider.display_name not in [entry[1] for entry in run_logger.entries]


def test_execute_enrichment_run_skips_preview_for_single_customer_ids_path(
    monkeypatch, db_session, organization_id
):
    customer = _seed_customer(
        db_session,
        organization_id,
        display_name="Single Customer",
        website="https://single.test",
    )
    db_session.commit()

    monkeypatch.setattr(
        "app.modules.scraper.services.enrichment_run_executor.enrich_customer_website",
        lambda candidate, **kwargs: _not_found_result(candidate),
    )

    run_logger = _CollectingRunLogger()
    execute_enrichment_run(
        db_session,
        organization_id,
        run_logger=run_logger,
        customer_ids=[customer.id],
        requested_fields=["email"],
    )

    steps = [entry[0] for entry in run_logger.entries]
    assert "candidates_to_process" not in steps
    assert "candidate_preview" not in steps
    assert "scan_batch_started" not in steps
    assert "customer_scan_started" not in steps
