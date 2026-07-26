"""Unit tests for DuplicateCheckHandler validation."""

from uuid import uuid4

from app.modules.operations.infrastructure.handlers.duplicate_check_handler import (
    DuplicateCheckHandler,
)
from app.modules.operations.infrastructure.handlers.registry import build_handler_registry


def test_duplicate_check_handler_registered():
    registry = build_handler_registry()
    handler = registry.require("duplicate_check")
    assert isinstance(handler, DuplicateCheckHandler)


def test_duplicate_check_validate_analyze_job():
    handler = DuplicateCheckHandler()
    result = handler.validate_create(
        source_kind="none",
        source_config={},
        type_config={"job_key": "analyze_customers_without_fair"},
        run_settings={},
        organization_id=uuid4(),
    )
    assert result.ok


def test_duplicate_check_validate_requires_group_by():
    handler = DuplicateCheckHandler()
    result = handler.validate_create(
        source_kind="none",
        source_config={},
        type_config={"job_key": "duplicate_customer_analysis"},
        run_settings={},
    )
    assert not result.ok
    assert any("group_by" in err for err in result.errors)


def test_duplicate_check_validate_group_by_ok():
    handler = DuplicateCheckHandler()
    result = handler.validate_create(
        source_kind="none",
        source_config={},
        type_config={
            "job_key": "duplicate_customer_analysis",
            "group_by": "company_name",
        },
        run_settings={},
    )
    assert result.ok
