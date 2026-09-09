from datetime import UTC, datetime

import pytest

from app.integrations.kyrox_core.lifecycle import (
    OrganizationLifecycleGuard,
    OrganizationLifecycleSnapshot,
)


@pytest.fixture(autouse=True)
def allow_core_lifecycle_for_existing_webhook_tests(monkeypatch):
    """Existing webhook tests exercise ACTIVE-organization behavior by default."""

    def _allow(self, organization_id):
        return OrganizationLifecycleSnapshot(
            organization_id=organization_id,
            status="active",
            work_allowed=True,
            updated_at=datetime(2026, 9, 9, tzinfo=UTC),
        )

    monkeypatch.setattr(OrganizationLifecycleGuard, "require_work_allowed", _allow)
