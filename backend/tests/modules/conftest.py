"""Module-test defaults for organization lifecycle-aware background work."""

from __future__ import annotations

from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def _active_organization_lifecycle_for_db_backed_module_tests(request, monkeypatch):
    """Keep legacy module tests on their injected DB and explicit ACTIVE lifecycle.

    OL07-04 adds a Core lifecycle dependency to background entrypoints. Existing
    module tests already inject ``db_session`` for product persistence and model
    normal, active-organization behavior unless a test says otherwise. Reuse that
    same session for the queued-work guard and stub the Core snapshot as ACTIVE.

    Focused OL07-04 tests that exercise suspended/unavailable behavior monkeypatch
    their target modules explicitly and therefore remain authoritative for those
    branches.
    """
    if "db_session" not in request.fixturenames:
        return

    db_session = request.getfixturevalue("db_session")

    import app.shared.queued_work_lifecycle as queued_work_lifecycle
    from app.integrations.kyrox_core.lifecycle import OrganizationLifecycleGuard

    monkeypatch.setattr(queued_work_lifecycle, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(
        OrganizationLifecycleGuard,
        "get_snapshot",
        lambda self, organization_id: SimpleNamespace(
            organization_id=organization_id,
            status="active",
            work_allowed=True,
        ),
    )
