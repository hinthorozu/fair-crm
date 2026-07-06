"""Tests for enrichment background job runner failure and completion paths."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.modules.scraper.application.enrichment_run_job_runner import (
    EnrichmentRunJobCommand,
    EnrichmentRunJobRunner,
)
from app.modules.scraper.application.run_enrichment import RunEnrichmentCommand, RunEnrichmentUseCase
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.services.enrichment_run_executor import EnrichmentRunExecution
from app.modules.scraper.services.scraper_run_history_service import create_run_history_service
from app.modules.scraper.services.scraper_run_log_service import create_run_log_service
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def _session_factory(db_session: Session):
    factory = sessionmaker(bind=db_session.bind)
    return factory


def _empty_handoff() -> ScraperImportHandoff:
    return ScraperImportHandoff(canonical_rows=[], row_metadata=[])


def _start_enrichment_run(db_session: Session, organization_id: UUID) -> UUID:
    service = create_run_history_service(db_session)
    use_case = RunEnrichmentUseCase(service, db_session)
    run = use_case.execute(
        RunEnrichmentCommand(
            organization_id=organization_id,
            adapter_key=ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
            limit=10,
        )
    )
    db_session.commit()
    return run.id


def _empty_execution() -> EnrichmentRunExecution:
    return EnrichmentRunExecution(results=[], handoff=_empty_handoff())


def test_enrichment_job_completes_with_zero_candidates(db_session, organization_id, user_id):
    def _executor(_session, _organization_id, **kwargs):
        return _empty_execution()

    run_id = _start_enrichment_run(db_session, organization_id)
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
    assert history.status.value == "completed"
    assert history.total_rows == 0
    assert history.duration_ms is not None

    logs = create_run_log_service(db_session).list_logs(run_id)
    steps = [log.step for log in logs]
    assert "started" in steps
    assert "candidates_query_started" in steps
    assert "run_finished" in steps


def test_enrichment_job_logs_candidate_query_timing(db_session, organization_id, user_id):
    def _executor(_session, _organization_id, **kwargs):
        run_logger = kwargs.get("run_logger")
        if run_logger is not None:
            run_logger.info(
                "candidates_query_finished",
                "Aday sorgusu tamamlandı",
                metadata={"duration_ms": 5, "candidates_count": 0},
            )
            run_logger.info(
                "candidates_loaded",
                "0 aday müşteri bulundu",
                metadata={"candidate_count": 0},
            )
        return _empty_execution()

    run_id = _start_enrichment_run(db_session, organization_id)
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

    logs = create_run_log_service(db_session).list_logs(run_id)
    steps = [log.step for log in logs]
    assert "candidates_query_started" in steps
    assert "candidates_query_finished" in steps
    assert "candidates_loaded" in steps


def test_enrichment_job_marks_failed_after_executor_error(db_session, organization_id, user_id):
    def _executor(_session, _organization_id, **kwargs):
        raise RuntimeError("candidate query failed")

    run_id = _start_enrichment_run(db_session, organization_id)
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
    assert history.status.value == "failed"
    assert history.error_message == "candidate query failed"
    assert history.finished_at is not None

    logs = create_run_log_service(db_session).list_logs(run_id)
    assert any(log.step == "failed" for log in logs)
