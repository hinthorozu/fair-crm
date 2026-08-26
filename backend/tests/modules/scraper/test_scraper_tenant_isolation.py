"""P0.1 tenant-isolation tests for scraper background execution."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.modules.scraper.application.adapter_test_run_job_runner import (
    AdapterTestRunJobCommand,
    AdapterTestRunJobRunner,
)
from app.modules.scraper.application.enrichment_run_job_runner import (
    EnrichmentRunJobCommand,
    EnrichmentRunJobRunner,
)
from app.modules.scraper.application.fair_scraper_job_runner import (
    FairScraperJobCommand,
    FairScraperJobRunner,
)
from app.modules.scraper.domain.scraper_run_history import ScraperRunStatus
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import (
    ScraperRunHistoryRepository,
)
from app.modules.scraper.services.scraper_run_cancellation import RunCancelChecker
from app.modules.scraper.services.scraper_run_history_service import create_run_history_service
from app.modules.scraper.services.scraper_run_log_service import create_run_log_service
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def _session_factory(db_session: Session):
    return sessionmaker(bind=db_session.bind)


def _start_run(db_session: Session, organization_id: UUID, *, adapter_key: str) -> UUID:
    run = create_run_history_service(db_session).start_run(
        adapter_key=adapter_key,
        input_url="https://tenant-isolation.test",
        fair_name="Tenant Isolation",
        fair_year=2026,
        organization_id=organization_id,
    )
    db_session.commit()
    return run.id


def _assert_run_untouched(db_session: Session, run_id: UUID, organization_id: UUID) -> None:
    db_session.expire_all()
    run = create_run_history_service(db_session).get_run(
        run_id,
        organization_id=organization_id,
    )
    assert run is not None
    assert run.status == ScraperRunStatus.RUNNING
    assert run.error_message is None
    assert create_run_log_service(db_session).list_logs(run_id) == []


def test_run_state_mutations_fail_closed_for_foreign_organization(db_session):
    organization_a = uuid4()
    organization_b = uuid4()
    run_id = _start_run(
        db_session,
        organization_b,
        adapter_key=ScraperSiteKey.TUYAP_NEW,
    )
    service = create_run_history_service(db_session)

    assert service.get_run(run_id, organization_id=organization_a) is None
    assert service.complete_run(
        run_id,
        handoff=ScraperImportHandoff(canonical_rows=[], row_metadata=[]),
        organization_id=organization_a,
    ) is None
    assert service.fail_run(
        run_id,
        error_message="foreign tenant must not mutate",
        organization_id=organization_a,
    ) is None
    assert service.mark_cancelling(run_id, organization_id=organization_a) is None
    assert service.touch_heartbeat(run_id, organization_id=organization_a) is None
    assert service.complete_cancelled_run(run_id, organization_id=organization_a) is None
    assert service.cancel_run(run_id, organization_id=organization_a) is None

    with pytest.raises(KeyError):
        service.request_cancel(
            run_id,
            organization_id=organization_a,
            requested_by=uuid4(),
        )

    _assert_run_untouched(db_session, run_id, organization_b)


def test_repository_scoped_update_rejects_foreign_organization(db_session):
    organization_a = uuid4()
    organization_b = uuid4()
    run_id = _start_run(
        db_session,
        organization_b,
        adapter_key=ScraperSiteKey.TUYAP_NEW,
    )
    repository = ScraperRunHistoryRepository(db_session)
    run = repository.get_by_id(run_id, organization_id=organization_b)
    assert run is not None

    with pytest.raises(KeyError):
        repository.update(run, organization_id=organization_a)

    _assert_run_untouched(db_session, run_id, organization_b)


def test_cancel_checker_treats_foreign_run_as_cancelled_without_heartbeat(db_session):
    organization_a = uuid4()
    organization_b = uuid4()
    run_id = _start_run(
        db_session,
        organization_b,
        adapter_key=ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
    )
    service = create_run_history_service(db_session)
    before = service.get_run(run_id, organization_id=organization_b)
    assert before is not None

    checker = RunCancelChecker(
        _session_factory(db_session),
        run_id,
        organization_id=organization_a,
    )
    assert checker.is_cancel_requested() is True
    assert checker.current_status() is None
    checker.touch_heartbeat_if_active()

    db_session.expire_all()
    after = service.get_run(run_id, organization_id=organization_b)
    assert after is not None
    assert after.status == ScraperRunStatus.RUNNING
    assert after.last_heartbeat_at == before.last_heartbeat_at


def test_adapter_test_worker_rejects_foreign_run_before_side_effects(db_session):
    organization_a = uuid4()
    organization_b = uuid4()
    run_id = _start_run(db_session, organization_b, adapter_key=ScraperSiteKey.TUYAP_NEW)

    def _must_not_execute(**_kwargs):
        raise AssertionError("foreign adapter-test job reached scraper executor")

    AdapterTestRunJobRunner(
        session_factory=_session_factory(db_session),
        scrape_executor=_must_not_execute,
    ).run_adapter_test(
        AdapterTestRunJobCommand(
            run_id=run_id,
            organization_id=organization_a,
            adapter_key=ScraperSiteKey.TUYAP_NEW,
            input_url="https://tenant-a.test",
        )
    )

    _assert_run_untouched(db_session, run_id, organization_b)


def test_enrichment_worker_rejects_foreign_run_before_side_effects(db_session):
    organization_a = uuid4()
    organization_b = uuid4()
    run_id = _start_run(
        db_session,
        organization_b,
        adapter_key=ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
    )

    def _must_not_execute(*_args, **_kwargs):
        raise AssertionError("foreign enrichment job reached executor")

    EnrichmentRunJobRunner(
        session_factory=_session_factory(db_session),
        executor=_must_not_execute,
    ).run_enrichment(
        EnrichmentRunJobCommand(
            run_id=run_id,
            organization_id=organization_a,
            adapter_key=ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
            user_id=uuid4(),
            requested_fields=["email"],
            dry_run=True,
        )
    )

    _assert_run_untouched(db_session, run_id, organization_b)


def test_fair_worker_rejects_foreign_run_before_side_effects(db_session):
    organization_a = uuid4()
    organization_b = uuid4()
    run_id = _start_run(db_session, organization_b, adapter_key=ScraperSiteKey.TUYAP_NEW)

    def _must_not_execute(**_kwargs):
        raise AssertionError("foreign fair scraper job reached scraper executor")

    FairScraperJobRunner(
        session_factory=_session_factory(db_session),
        scrape_executor=_must_not_execute,
    ).run_fair_scraper(
        FairScraperJobCommand(
            run_id=run_id,
            organization_id=organization_a,
            fair_id=uuid4(),
            user_id=uuid4(),
        )
    )

    _assert_run_untouched(db_session, run_id, organization_b)
