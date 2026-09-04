from types import SimpleNamespace
from uuid import uuid4

import app.shared.queued_work_lifecycle as lifecycle


def _registered_import_function():
    return None


_registered_import_function.__module__ = lifecycle._IMPORT_MODULE
_registered_import_function.__name__ = "run_analyze"


def _command(organization_id):
    return SimpleNamespace(organization_id=organization_id, job_id=uuid4())


def test_suspended_queued_work_is_terminalized_before_start(monkeypatch):
    organization_id = uuid4()
    command = _command(organization_id)
    terminalized = []

    monkeypatch.setattr(lifecycle, "_is_locally_startable", lambda descriptor: True)
    monkeypatch.setattr(
        lifecycle,
        "OrganizationLifecycleGuard",
        lambda: SimpleNamespace(
            get_snapshot=lambda requested_id: SimpleNamespace(
                organization_id=requested_id,
                status="suspended",
                work_allowed=False,
            )
        ),
    )
    monkeypatch.setattr(
        lifecycle,
        "_terminalize",
        lambda descriptor, *, reason: terminalized.append((descriptor, reason)),
    )

    allowed = lifecycle.should_execute_queued_product_work(
        _registered_import_function,
        (command,),
        {},
    )

    assert allowed is False
    assert len(terminalized) == 1
    descriptor, reason = terminalized[0]
    assert descriptor.organization_id == organization_id
    assert descriptor.command is command
    assert reason == "organization_lifecycle_prestart_cancelled:suspended"


def test_active_queued_work_starts_without_terminalization(monkeypatch):
    organization_id = uuid4()
    command = _command(organization_id)
    terminalized = []

    monkeypatch.setattr(lifecycle, "_is_locally_startable", lambda descriptor: True)
    monkeypatch.setattr(
        lifecycle,
        "OrganizationLifecycleGuard",
        lambda: SimpleNamespace(
            get_snapshot=lambda requested_id: SimpleNamespace(
                organization_id=requested_id,
                status="active",
                work_allowed=True,
            )
        ),
    )
    monkeypatch.setattr(
        lifecycle,
        "_terminalize",
        lambda descriptor, *, reason: terminalized.append((descriptor, reason)),
    )

    assert lifecycle.should_execute_queued_product_work(
        _registered_import_function,
        (command,),
        {},
    ) is True
    assert terminalized == []


def test_lifecycle_unavailable_fails_closed_without_terminalizing(monkeypatch):
    organization_id = uuid4()
    command = _command(organization_id)
    terminalized = []

    class UnavailableGuard:
        def get_snapshot(self, requested_id):
            assert requested_id == organization_id
            raise lifecycle.OrganizationLifecycleUnavailableError("unavailable")

    monkeypatch.setattr(lifecycle, "_is_locally_startable", lambda descriptor: True)
    monkeypatch.setattr(lifecycle, "OrganizationLifecycleGuard", UnavailableGuard)
    monkeypatch.setattr(
        lifecycle,
        "_terminalize",
        lambda descriptor, *, reason: terminalized.append((descriptor, reason)),
    )

    assert lifecycle.should_execute_queued_product_work(
        _registered_import_function,
        (command,),
        {},
    ) is False
    assert terminalized == []


def test_decision_keeps_organization_scope(monkeypatch):
    active_org = uuid4()
    suspended_org = uuid4()
    terminalized_orgs = []

    class ScopedGuard:
        def get_snapshot(self, requested_id):
            return SimpleNamespace(
                organization_id=requested_id,
                status="active" if requested_id == active_org else "suspended",
                work_allowed=requested_id == active_org,
            )

    monkeypatch.setattr(lifecycle, "_is_locally_startable", lambda descriptor: True)
    monkeypatch.setattr(lifecycle, "OrganizationLifecycleGuard", ScopedGuard)
    monkeypatch.setattr(
        lifecycle,
        "_terminalize",
        lambda descriptor, *, reason: terminalized_orgs.append(descriptor.organization_id),
    )

    assert lifecycle.should_execute_queued_product_work(
        _registered_import_function,
        (_command(active_org),),
        {},
    ) is True
    assert lifecycle.should_execute_queued_product_work(
        _registered_import_function,
        (_command(suspended_org),),
        {},
    ) is False
    assert terminalized_orgs == [suspended_org]
