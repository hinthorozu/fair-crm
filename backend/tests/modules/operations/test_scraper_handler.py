"""Unit tests for ScraperHandler validation and start/cancel wiring."""

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
from app.modules.operations.infrastructure.handlers.scraper_handler import ScraperHandler
from app.modules.operations.infrastructure.handlers.scraper_operation_sync import (
    extract_scraper_run_id,
)
from app.modules.scraper.domain.enrichment_adapter import (
    CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY,
)
from app.modules.scraper.domain.scraper_run_source import ScraperRunSource


class _FakeFair:
    def __init__(self, **kwargs):
        self.id = kwargs["id"]
        self.organization_id = kwargs["organization_id"]
        self.name = kwargs.get("name", "Test Fair")
        self.adapter_key = kwargs.get("adapter_key", "tuyap_new")
        self.source_url = kwargs.get("source_url", "https://example.com/list")
        self.scraper_config = kwargs.get("scraper_config", {"max_pages": 2})
        self.start_date = kwargs.get("start_date")
        self.deleted_at = kwargs.get("deleted_at")
        self.status = kwargs.get("status", "active")


class _FakeFairRepo:
    def __init__(self, fair: _FakeFair | None):
        self._fair = fair

    def get_by_id(self, organization_id, fair_id):
        if self._fair is None:
            return None
        if self._fair.organization_id != organization_id or self._fair.id != fair_id:
            return None
        return self._fair


class _FakeAdapterService:
    def __init__(self, *, active: bool = True, supports: object | None = None):
        self._active = active
        self._supports = supports or SimpleNamespace(
            list_scraping=True,
            phone=True,
            email=True,
            address=True,
            website=True,
            detail_scraping=True,
            description=True,
        )

    def get_adapter(self, organization_id, adapter_key):
        from app.modules.scraper.domain.scraper_adapter_exceptions import AdapterNotFoundError

        _ = organization_id
        if adapter_key == "missing":
            raise AdapterNotFoundError(adapter_key)
        return SimpleNamespace(adapter_key=adapter_key, is_active=self._active)

    def get_merged_manifest(self, organization_id, adapter_key):
        _ = organization_id, adapter_key
        return SimpleNamespace(supports=self._supports)


class _FakeHistoryService:
    def __init__(self):
        self.started = []
        self.cancels = []

    def start_run(self, **kwargs):
        run_id = uuid4()
        self.started.append(kwargs)
        return SimpleNamespace(id=run_id, **kwargs)

    def request_cancel(self, run_id, *, organization_id, requested_by):
        self.cancels.append((run_id, organization_id, requested_by))


def _operation(*, fair_id, adapter_key="tuyap_new", type_config=None, org_id=None):
    org = org_id or uuid4()
    return Operation.create(
        organization_id=org,
        operation_type=OperationType.SCRAPER,
        title="Scraper op",
        created_by=uuid4(),
        now=datetime.now(tz=UTC),
        source_kind=SourceKind.FAIR,
        source_config={"source_ids": [str(fair_id)]},
        type_config=type_config
        or {
            "adapter_key": adapter_key,
            "requested_fields": ["customerName", "email"],
            "max_pages": 3,
            "use_http": True,
            "scrape_detail": False,
        },
        status=OperationStatus.READY,
    )


def test_validate_create_rejects_enrichment_adapter():
    handler = ScraperHandler()
    result = handler.validate_create(
        source_kind=SourceKind.FAIR,
        source_config={"source_ids": [str(uuid4())]},
        type_config={
            "adapter_key": CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY,
            "requested_fields": ["email"],
        },
        run_settings={},
    )
    assert result.ok is False
    assert any("enrichment" in err for err in result.errors)


def test_validate_create_requires_requested_fields_and_single_fair():
    handler = ScraperHandler()
    result = handler.validate_create(
        source_kind=SourceKind.FAIR,
        source_config={"source_ids": [str(uuid4()), str(uuid4())]},
        type_config={"adapter_key": "tuyap_new"},
        run_settings={},
    )
    assert result.ok is False
    assert any("exactly one fair" in err for err in result.errors)
    assert any("requested_fields" in err for err in result.errors)


def test_validate_create_allows_adapter_override_different_from_fair():
    fair_id = uuid4()
    org_id = uuid4()
    fair = _FakeFair(
        id=fair_id,
        organization_id=org_id,
        adapter_key="tuyap_old",
        source_url="https://example.com/list",
    )
    handler = ScraperHandler(
        fair_repository=_FakeFairRepo(fair),
        adapter_service=_FakeAdapterService(),
    )
    result = handler.validate_create(
        source_kind=SourceKind.FAIR,
        source_config={"source_ids": [str(fair_id)]},
        type_config={
            "adapter_key": "tuyap_new",
            "requested_fields": ["customerName", "email"],
            "source_url": "https://example.com/override",
            "scraper_config": {"max_pages": 1},
        },
        run_settings={},
        organization_id=org_id,
    )
    assert result.ok is True


def test_validate_create_accepts_source_url_override_when_fair_url_missing():
    fair_id = uuid4()
    org_id = uuid4()
    fair = _FakeFair(
        id=fair_id,
        organization_id=org_id,
        adapter_key="tuyap_new",
        source_url=None,
    )
    handler = ScraperHandler(
        fair_repository=_FakeFairRepo(fair),
        adapter_service=_FakeAdapterService(),
    )
    result = handler.validate_create(
        source_kind=SourceKind.FAIR,
        source_config={"source_ids": [str(fair_id)]},
        type_config={
            "adapter_key": "tuyap_new",
            "requested_fields": ["customerName", "email"],
            "source_url": "https://example.com/override",
        },
        run_settings={},
        organization_id=org_id,
    )
    assert result.ok is True


def test_on_start_schedules_job_and_links_scraper_run():
    fair_id = uuid4()
    org_id = uuid4()
    user_id = uuid4()
    fair = _FakeFair(id=fair_id, organization_id=org_id, adapter_key="tuyap_new")
    history = _FakeHistoryService()
    scheduled = []

    handler = ScraperHandler(
        fair_repository=_FakeFairRepo(fair),
        adapter_service=_FakeAdapterService(),
        run_history_service=history,
        job_scheduler=scheduled.append,
    )
    operation = _operation(fair_id=fair_id, org_id=org_id)
    run = OperationRun.create(
        organization_id=org_id,
        operation_id=operation.id,
        now=datetime.now(tz=UTC),
        triggered_by=user_id,
        status=RunStatus.QUEUED,
    )
    result = handler.on_start(
        operation=operation,
        run=run,
        context=HandlerExecutionContext(user_id=user_id, access_token="token"),
    )

    assert result.run_status == RunStatus.RUNNING
    assert extract_scraper_run_id(run) is not None
    assert result.result_payload["adapter_key"] == "tuyap_new"
    assert result.result_payload["requested_fields"] == ["customerName", "email"]
    assert len(scheduled) == 1
    command = scheduled[0]
    assert command.operation_id == operation.id
    assert command.operation_run_id == run.id
    assert command.requested_fields == ["customerName", "email"]
    assert command.option_overrides == {
        "max_pages": 3,
        "use_http": True,
        "scrape_detail": False,
    }
    assert command.adapter_key == "tuyap_new"
    assert command.source_url == "https://example.com/list"
    assert history.started[0]["run_source"] == ScraperRunSource.FAIR_AUTOMATION


def test_on_cancel_requests_scraper_cancel():
    fair_id = uuid4()
    org_id = uuid4()
    user_id = uuid4()
    fair = _FakeFair(id=fair_id, organization_id=org_id)
    history = _FakeHistoryService()
    handler = ScraperHandler(
        fair_repository=_FakeFairRepo(fair),
        adapter_service=_FakeAdapterService(),
        run_history_service=history,
        job_scheduler=lambda _cmd: None,
    )
    operation = _operation(fair_id=fair_id, org_id=org_id)
    run = OperationRun.create(
        organization_id=org_id,
        operation_id=operation.id,
        now=datetime.now(tz=UTC),
        triggered_by=user_id,
        status=RunStatus.RUNNING,
    )
    start = handler.on_start(
        operation=operation,
        run=run,
        context=HandlerExecutionContext(user_id=user_id, access_token="token"),
    )
    scraper_run_id = extract_scraper_run_id(run)
    assert scraper_run_id is not None
    assert start.result_payload is not None

    handler.on_cancel(
        operation=operation,
        run=run,
        context=HandlerExecutionContext(user_id=user_id, access_token="token"),
    )
    assert history.cancels == [(scraper_run_id, org_id, user_id)]


def test_on_start_without_scheduler_raises():
    fair_id = uuid4()
    org_id = uuid4()
    fair = _FakeFair(id=fair_id, organization_id=org_id)
    handler = ScraperHandler(
        fair_repository=_FakeFairRepo(fair),
        adapter_service=_FakeAdapterService(),
        run_history_service=_FakeHistoryService(),
        job_scheduler=None,
    )
    operation = _operation(fair_id=fair_id, org_id=org_id)
    run = OperationRun.create(
        organization_id=org_id,
        operation_id=operation.id,
        now=datetime.now(tz=UTC),
        triggered_by=uuid4(),
        status=RunStatus.QUEUED,
    )
    with pytest.raises(InvalidOperationConfigError, match="scheduler"):
        handler.on_start(
            operation=operation,
            run=run,
            context=HandlerExecutionContext(user_id=uuid4(), access_token="token"),
        )
