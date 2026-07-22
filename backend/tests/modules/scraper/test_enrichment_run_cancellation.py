"""Tests for cooperative enrichment run cancellation."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, sessionmaker

from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.communication_models import CustomerWebsiteModel
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.scraper.application.enrichment_run_job_runner import (
    EnrichmentRunJobCommand,
    EnrichmentRunJobRunner,
)
from app.modules.scraper.application.run_enrichment import RunEnrichmentCommand, RunEnrichmentUseCase
from app.modules.scraper.domain.customer_enrichment_state import CustomerEnrichmentScanStatus
from app.modules.scraper.domain.scraper_run_history import ScraperRunStatus
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.persistence.models import CustomerEnrichmentStateModel
from app.modules.scraper.services.enrichment_candidate_service import list_enrichment_candidates
from app.modules.scraper.services.enrichment_run_executor import EnrichmentRunExecution
from app.modules.scraper.services.scraper_run_cancellation import RunCancelChecker
from app.modules.scraper.services.scraper_run_history_service import create_run_history_service
from app.modules.scraper.services.scraper_run_log_service import create_run_log_service
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def _session_factory(db_session: Session):
    return sessionmaker(bind=db_session.bind)


def _start_run(db_session: Session, organization_id: UUID) -> UUID:
    service = create_run_history_service(db_session)
    run = RunEnrichmentUseCase(service, db_session).execute(
        RunEnrichmentCommand(
            organization_id=organization_id,
            adapter_key=ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
            limit=10,
        )
    )
    db_session.commit()
    return run.id


def test_request_cancel_sets_cancel_requested(db_session, organization_id, user_id):
    service = create_run_history_service(db_session)
    run = service.start_run(
        adapter_key=ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
        input_url=None,
        fair_name="Enrichment",
        fair_year=None,
        organization_id=organization_id,
    )
    db_session.commit()

    updated = service.request_cancel(
        run.id,
        organization_id=organization_id,
        requested_by=user_id,
    )
    db_session.commit()

    assert updated.status == ScraperRunStatus.CANCEL_REQUESTED
    assert updated.cancel_requested_by == user_id
    assert updated.cancel_requested_at is not None
    assert updated.error_message is None


def test_run_cancel_checker_detects_cancel_requested(db_session, organization_id, user_id):
    service = create_run_history_service(db_session)
    run = service.start_run(
        adapter_key=ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
        input_url=None,
        fair_name="Enrichment",
        fair_year=None,
        organization_id=organization_id,
    )
    service.request_cancel(run.id, organization_id=organization_id, requested_by=user_id)
    db_session.commit()

    checker = RunCancelChecker(_session_factory(db_session), run.id)
    assert checker.is_cancel_requested() is True


def test_run_cancel_checker_treats_missing_run_as_cancelled(db_session):
    checker = RunCancelChecker(_session_factory(db_session), uuid4())
    assert checker.is_cancel_requested() is True


def test_enrichment_job_finalizes_cancelled_with_partial_results(db_session, organization_id, user_id):
    customer_a = uuid4()
    customer_b = uuid4()
    processed_states: list[UUID] = []

    def _executor(_session, _organization_id, **kwargs):
        run_id = kwargs["run_id"]
        history = create_run_history_service(_session)
        history.request_cancel(run_id, organization_id=organization_id, requested_by=user_id)
        _session.commit()
        processed_states.append(customer_a)
        handoff = ScraperImportHandoff(
            canonical_rows=[{"company_name": "A Co", "email": "a@test.com", "website": "https://a.test"}],
            row_metadata=[{"customer_id": str(customer_a)}],
        )
        from app.modules.scraper.dto.enrichment_result_dto import EnrichmentResultDto

        result = EnrichmentResultDto(
            customer_id=customer_a,
            company_name="A Co",
            website="https://a.test",
            status="found",
            emails=[],
            phones=[],
            error=None,
        )
        return EnrichmentRunExecution(
            results=[result],
            handoff=handoff,
            cancelled=True,
            processed_count=1,
            total_candidates=2,
            last_processed_customer_id=customer_a,
        )

    run_id = _start_run(db_session, organization_id)
    runner = EnrichmentRunJobRunner(
        session_factory=_session_factory(db_session),
        executor=_executor,
    )
    runner.run_enrichment(
        EnrichmentRunJobCommand(
            run_id=run_id,
            organization_id=organization_id,
            adapter_key=ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
            user_id=user_id,
            limit=10,
            requested_fields=["email"],
            dry_run=True,
        )
    )
    db_session.expire_all()

    history = create_run_history_service(db_session).get_run(run_id)
    assert history is not None
    assert history.status == ScraperRunStatus.CANCELLED
    assert history.error_message is None

    logs = create_run_log_service(db_session).list_logs(run_id)
    steps = [log.step for log in logs]
    assert "cancelling" in steps
    assert "cancelled" in steps


def test_unprocessed_customer_has_no_state_after_cancelled_run(db_session, organization_id, user_id):
    now = datetime.now(tz=UTC)
    processed = CustomerModel(
        id=uuid4(),
        organization_id=organization_id,
        display_name="Processed Co",
        normalized_name="processed co",
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    untouched = CustomerModel(
        id=uuid4(),
        organization_id=organization_id,
        display_name="Untouched Co",
        normalized_name="untouched co",
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([processed, untouched])
    db_session.flush()
    db_session.add_all(
        [
            CustomerWebsiteModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=processed.id,
                website="https://processed.test",
                is_primary=True,
                created_at=now,
            ),
            CustomerWebsiteModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=untouched.id,
                website="https://untouched.test",
                is_primary=True,
                created_at=now,
            ),
        ]
    )
    db_session.commit()

    def _executor(session, _organization_id, **kwargs):
        from app.modules.scraper.dto.enrichment_result_dto import EnrichmentResultDto
        from app.modules.scraper.services.customer_enrichment_state_service import record_scan_result

        record_scan_result(
            session,
            organization_id=organization_id,
            run_id=kwargs["run_id"],
            result=EnrichmentResultDto(
                customer_id=processed.id,
                company_name="Processed Co",
                website="https://processed.test",
                status="not_found",
                emails=[],
                phones=[],
                error=None,
            ),
        )
        session.commit()
        return EnrichmentRunExecution(
            results=[],
            handoff=ScraperImportHandoff(canonical_rows=[], row_metadata=[]),
            cancelled=True,
            processed_count=1,
            total_candidates=2,
            last_processed_customer_id=processed.id,
        )

    run_id = _start_run(db_session, organization_id)
    runner = EnrichmentRunJobRunner(session_factory=_session_factory(db_session), executor=_executor)
    runner.run_enrichment(
        EnrichmentRunJobCommand(
            run_id=run_id,
            organization_id=organization_id,
            adapter_key=ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
            user_id=user_id,
            limit=10,
            requested_fields=["email"],
            dry_run=False,
        )
    )
    db_session.expire_all()

    processed_state = (
        db_session.query(CustomerEnrichmentStateModel)
        .filter(
            CustomerEnrichmentStateModel.organization_id == organization_id,
            CustomerEnrichmentStateModel.customer_id == processed.id,
        )
        .one_or_none()
    )
    untouched_state = (
        db_session.query(CustomerEnrichmentStateModel)
        .filter(
            CustomerEnrichmentStateModel.organization_id == organization_id,
            CustomerEnrichmentStateModel.customer_id == untouched.id,
        )
        .one_or_none()
    )
    # User cancel clears email_not_found/failed cooldowns from this run.
    assert processed_state is not None
    assert processed_state.last_email_scan_status == CustomerEnrichmentScanStatus.NOT_SCANNED
    assert processed_state.retry_after is None
    assert untouched_state is None

    candidate_ids = {item.customer_id for item in list_enrichment_candidates(db_session, organization_id)}
    assert processed.id in candidate_ids
    assert untouched.id in candidate_ids


def test_cancelled_run_does_not_block_candidates_after_failed_and_not_found(
    db_session, organization_id, user_id
):
    """380→378 style regression: cancel must not leave retry cooldowns on scanned rows."""
    now = datetime.now(tz=UTC)
    customers = []
    for name, website in (
        ("Not Found Co", "https://not-found.test"),
        ("Failed Co", "https://failed.test"),
        ("Untouched Co", "https://untouched.test"),
    ):
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
        customers.append(customer)
    db_session.commit()
    not_found_customer, failed_customer, untouched_customer = customers

    assert len(list_enrichment_candidates(db_session, organization_id)) == 3

    def _executor(session, _organization_id, **kwargs):
        from app.modules.scraper.dto.enrichment_result_dto import EnrichmentResultDto
        from app.modules.scraper.services.customer_enrichment_state_service import record_scan_result

        run_id = kwargs["run_id"]
        record_scan_result(
            session,
            organization_id=organization_id,
            run_id=run_id,
            result=EnrichmentResultDto(
                customer_id=not_found_customer.id,
                company_name="Not Found Co",
                website="https://not-found.test",
                status="not_found",
            ),
        )
        record_scan_result(
            session,
            organization_id=organization_id,
            run_id=run_id,
            result=EnrichmentResultDto(
                customer_id=failed_customer.id,
                company_name="Failed Co",
                website="https://failed.test",
                status="failed",
                error="timeout",
            ),
        )
        session.commit()
        return EnrichmentRunExecution(
            results=[],
            handoff=ScraperImportHandoff(canonical_rows=[], row_metadata=[]),
            cancelled=True,
            processed_count=2,
            total_candidates=3,
            last_processed_customer_id=failed_customer.id,
        )

    run_id = _start_run(db_session, organization_id)
    EnrichmentRunJobRunner(session_factory=_session_factory(db_session), executor=_executor).run_enrichment(
        EnrichmentRunJobCommand(
            run_id=run_id,
            organization_id=organization_id,
            adapter_key=ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
            user_id=user_id,
            limit=10,
            requested_fields=["email"],
            dry_run=False,
        )
    )
    db_session.expire_all()

    after_ids = {item.customer_id for item in list_enrichment_candidates(db_session, organization_id)}
    assert after_ids == {not_found_customer.id, failed_customer.id, untouched_customer.id}


def test_cancel_scraper_run_api_sets_cancel_requested(client, auth_headers, db_session, organization_id, user_id):
    service = create_run_history_service(db_session)
    run = service.start_run(
        adapter_key=ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
        input_url=None,
        fair_name="Enrichment",
        fair_year=None,
        organization_id=organization_id,
    )
    db_session.commit()

    response = client.post(f"/api/v1/scraper/runs/{run.id}/cancel", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "cancel_requested"
    assert payload["job_id"] == str(run.id)
    assert payload["cancel_requested_at"] is not None
    assert "İptal isteği alındı" in payload["message"]

    db_session.expire_all()
    logs = create_run_log_service(db_session).list_logs(run.id)
    assert any(log.step == "cancel_requested" for log in logs)
