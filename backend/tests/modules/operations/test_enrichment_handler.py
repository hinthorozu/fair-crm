"""Unit tests for EnrichmentHandler validation and start/cancel wiring."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.modules.operations.domain.entities import Operation, OperationRun
from app.modules.operations.domain.exceptions import InvalidOperationConfigError
from app.modules.operations.domain.handler import HandlerExecutionContext
from app.modules.operations.domain.value_objects import (
    OperationStatus,
    OperationType,
    RunStatus,
    SourceKind,
)
from app.modules.operations.infrastructure.handlers.enrichment_handler import EnrichmentHandler
from app.modules.operations.infrastructure.handlers.scraper_operation_sync import (
    extract_scraper_run_id,
)
from app.modules.scraper.domain.enrichment_adapter import (
    CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY,
)


class _FakeEnrichmentUseCase:
    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.commands = []

    def execute(self, command):
        self.commands.append(command)
        if self.fail:
            raise RuntimeError("enrichment start blocked")
        return SimpleNamespace(
            id=uuid4(),
            adapter_key=command.adapter_key,
        )


class _FakeHistoryService:
    def __init__(self):
        self.cancels = []

    def request_cancel(self, run_id, *, organization_id, requested_by):
        self.cancels.append((run_id, organization_id, requested_by))


def _operation(*, fair_id=None, type_config=None, org_id=None):
    org = org_id or uuid4()
    source_kind = SourceKind.FAIR if fair_id else SourceKind.CUSTOMER
    source_config = {"source_ids": [str(fair_id)]} if fair_id else {}
    return Operation.create(
        organization_id=org,
        operation_type=OperationType.ENRICHMENT,
        title="Müşteri Zenginleştirme",
        created_by=uuid4(),
        now=datetime.now(tz=UTC),
        source_kind=source_kind,
        source_config=source_config,
        type_config=type_config
        or {
            "adapter_key": CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY,
            "requested_fields": ["email", "phone"],
            "limit": 5,
            "include_existing_email": False,
        },
        status=OperationStatus.READY,
    )


def test_validate_create_rejects_wrong_adapter():
    handler = EnrichmentHandler()
    result = handler.validate_create(
        source_kind=SourceKind.CUSTOMER,
        source_config={},
        type_config={
            "adapter_key": "tuyap_new",
            "requested_fields": ["email"],
        },
        run_settings={},
    )
    assert not result.ok
    assert any("adapter_key" in err for err in result.errors)


def test_validate_create_rejects_research_placeholder_fields_as_requested():
    handler = EnrichmentHandler()
    result = handler.validate_create(
        source_kind=SourceKind.CUSTOMER,
        source_config={},
        type_config={
            "adapter_key": CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY,
            "requested_fields": ["research_website"],
        },
        run_settings={},
    )
    assert not result.ok
    assert any("invalid requested_fields" in err for err in result.errors)


def test_validate_create_accepts_customer_source_without_fair():
    handler = EnrichmentHandler()
    result = handler.validate_create(
        source_kind=SourceKind.CUSTOMER,
        source_config={},
        type_config={
            "adapter_key": CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY,
            "requested_fields": ["email"],
            "limit": 3,
        },
        run_settings={},
    )
    assert result.ok


def test_on_start_links_scraper_run_id_and_schedules_job():
    use_case = _FakeEnrichmentUseCase()
    scheduled = []
    handler = EnrichmentHandler(
        run_enrichment_use_case=use_case,
        run_history_service=_FakeHistoryService(),
        job_scheduler=scheduled.append,
    )
    operation = _operation()
    run = OperationRun.create(
        organization_id=operation.organization_id,
        operation_id=operation.id,
        now=datetime.now(tz=UTC),
        triggered_by=uuid4(),
        status=RunStatus.QUEUED,
    )
    context = HandlerExecutionContext(user_id=uuid4(), access_token="token")

    result = handler.on_start(operation=operation, run=run, context=context)

    assert result.run_status == RunStatus.RUNNING
    assert extract_scraper_run_id(run) is not None
    assert result.result_payload["scraper_run_id"] == str(extract_scraper_run_id(run))
    assert len(scheduled) == 1
    assert scheduled[0].operation_id == operation.id
    assert scheduled[0].operation_run_id == run.id
    assert use_case.commands[0].organization_id == operation.organization_id


def test_on_start_returns_failed_when_enrichment_engine_cannot_start():
    handler = EnrichmentHandler(
        run_enrichment_use_case=_FakeEnrichmentUseCase(fail=True),
        job_scheduler=lambda _cmd: None,
    )
    operation = _operation()
    run = OperationRun.create(
        organization_id=operation.organization_id,
        operation_id=operation.id,
        now=datetime.now(tz=UTC),
        triggered_by=uuid4(),
        status=RunStatus.QUEUED,
    )
    result = handler.on_start(
        operation=operation,
        run=run,
        context=HandlerExecutionContext(user_id=uuid4(), access_token="token"),
    )
    assert result.run_status == RunStatus.FAILED
    assert "enrichment start blocked" in (result.message or "")


def test_on_start_requires_scheduler():
    handler = EnrichmentHandler(
        run_enrichment_use_case=_FakeEnrichmentUseCase(),
        job_scheduler=None,
    )
    operation = _operation()
    run = OperationRun.create(
        organization_id=operation.organization_id,
        operation_id=operation.id,
        now=datetime.now(tz=UTC),
        triggered_by=uuid4(),
        status=RunStatus.QUEUED,
    )
    with pytest.raises(InvalidOperationConfigError):
        handler.on_start(
            operation=operation,
            run=run,
            context=HandlerExecutionContext(user_id=uuid4(), access_token="token"),
        )


def test_on_cancel_requests_cancel_on_linked_run():
    history = _FakeHistoryService()
    use_case = _FakeEnrichmentUseCase()
    scheduled = []
    handler = EnrichmentHandler(
        run_enrichment_use_case=use_case,
        run_history_service=history,
        job_scheduler=scheduled.append,
    )
    operation = _operation()
    run = OperationRun.create(
        organization_id=operation.organization_id,
        operation_id=operation.id,
        now=datetime.now(tz=UTC),
        triggered_by=uuid4(),
        status=RunStatus.QUEUED,
    )
    context = HandlerExecutionContext(user_id=uuid4(), access_token="token")
    handler.on_start(operation=operation, run=run, context=context)
    linked = extract_scraper_run_id(run)
    assert linked is not None

    handler.on_cancel(operation=operation, run=run, context=context)
    assert history.cancels == [(linked, operation.organization_id, context.user_id)]


def test_handler_registered_in_registry():
    from app.modules.operations.infrastructure.handlers.registry import build_handler_registry

    registry = build_handler_registry()
    handler = registry.get(OperationType.ENRICHMENT)
    assert handler is not None
    assert handler.operation_type == OperationType.ENRICHMENT
