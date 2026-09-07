"""OL-07 deterministic reactivation/resumption regression coverage."""

from types import SimpleNamespace
from uuid import uuid4

import app.shared.queued_work_lifecycle as lifecycle
from app.modules.imports.domain.value_objects import ImportJobStatus


def _registered_import_function():
    return None


_registered_import_function.__module__ = lifecycle._IMPORT_MODULE
_registered_import_function.__name__ = "run_analyze"


def test_reactivation_does_not_restart_terminalized_queued_work(monkeypatch):
    organization_id = uuid4()
    cancelled_job_id = uuid4()
    fresh_job_id = uuid4()
    cancelled_command = SimpleNamespace(
        organization_id=organization_id,
        job_id=cancelled_job_id,
    )
    fresh_command = SimpleNamespace(
        organization_id=organization_id,
        job_id=fresh_job_id,
    )
    statuses = {
        cancelled_job_id: ImportJobStatus.QUEUED,
        fresh_job_id: ImportJobStatus.QUEUED,
    }
    lifecycle_state = {"status": "suspended", "work_allowed": False}
    terminalized = []

    monkeypatch.setattr(
        lifecycle,
        "_is_locally_startable",
        lambda descriptor: statuses[descriptor.command.job_id] == ImportJobStatus.QUEUED,
    )

    class Guard:
        def get_snapshot(self, requested_id):
            assert requested_id == organization_id
            return SimpleNamespace(
                organization_id=requested_id,
                status=lifecycle_state["status"],
                work_allowed=lifecycle_state["work_allowed"],
            )

    monkeypatch.setattr(lifecycle, "OrganizationLifecycleGuard", Guard)

    def _terminalize(descriptor, *, reason):
        statuses[descriptor.command.job_id] = ImportJobStatus.CANCELLED
        terminalized.append((descriptor.command.job_id, reason))

    monkeypatch.setattr(lifecycle, "_terminalize", _terminalize)

    assert lifecycle.should_execute_queued_product_work(
        _registered_import_function,
        (cancelled_command,),
        {},
    ) is False
    assert statuses[cancelled_job_id] == ImportJobStatus.CANCELLED

    # Core reactivation does not resurrect the terminal local record. The old
    # callback remains non-startable, while newly queued work may start normally.
    lifecycle_state.update(status="active", work_allowed=True)

    assert lifecycle.should_execute_queued_product_work(
        _registered_import_function,
        (cancelled_command,),
        {},
    ) is False
    assert lifecycle.should_execute_queued_product_work(
        _registered_import_function,
        (fresh_command,),
        {},
    ) is True
    assert terminalized == [
        (
            cancelled_job_id,
            "organization_lifecycle_prestart_cancelled:suspended",
        )
    ]
