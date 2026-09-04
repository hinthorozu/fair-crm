from unittest.mock import Mock
from uuid import uuid4

import pytest

import app.modules.data_integration.application.import_job_runner as runner_module
from app.modules.data_integration.application.import_job_runner import (
    AnalyzeJobCommand,
    ApplyJobCommand,
    BulkDecisionJobCommand,
    ImportJobRunner,
)


def _ids():
    return {
        "organization_id": uuid4(),
        "user_id": uuid4(),
        "batch_id": uuid4(),
        "job_id": uuid4(),
    }


@pytest.mark.parametrize(
    ("public_method", "internal_method", "command"),
    [
        (
            "run_analyze",
            "_run_analyze",
            lambda: AnalyzeJobCommand(access_token="token", **_ids()),
        ),
        (
            "run_apply",
            "_run_apply",
            lambda: ApplyJobCommand(access_token="token", **_ids()),
        ),
        (
            "run_bulk_decision",
            "_run_bulk_decision",
            lambda: BulkDecisionJobCommand(
                access_token="token",
                action_type="skip_all",
                **_ids(),
            ),
        ),
    ],
)
def test_import_runner_does_not_enter_running_path_when_prestart_gate_denies(
    monkeypatch,
    public_method,
    internal_method,
    command,
):
    runner = ImportJobRunner(session_factory=lambda: pytest.fail("runner must not open a session"))
    inner = Mock()
    monkeypatch.setattr(runner, internal_method, inner)
    gate_calls = []

    def deny(func, args, kwargs):
        gate_calls.append((func.__name__, args, kwargs))
        return False

    monkeypatch.setattr(runner_module, "should_execute_queued_product_work", deny)
    cmd = command()

    getattr(runner, public_method)(cmd)

    assert gate_calls == [(public_method, (cmd,), {})]
    inner.assert_not_called()


@pytest.mark.parametrize(
    ("public_method", "internal_method", "command"),
    [
        (
            "run_analyze",
            "_run_analyze",
            lambda: AnalyzeJobCommand(access_token="token", **_ids()),
        ),
        (
            "run_apply",
            "_run_apply",
            lambda: ApplyJobCommand(access_token="token", **_ids()),
        ),
        (
            "run_bulk_decision",
            "_run_bulk_decision",
            lambda: BulkDecisionJobCommand(
                access_token="token",
                action_type="skip_all",
                **_ids(),
            ),
        ),
    ],
)
def test_import_runner_enters_running_path_only_after_prestart_gate_allows(
    monkeypatch,
    public_method,
    internal_method,
    command,
):
    runner = ImportJobRunner()
    inner = Mock()
    monkeypatch.setattr(runner, internal_method, inner)
    monkeypatch.setattr(
        runner_module,
        "should_execute_queued_product_work",
        lambda func, args, kwargs: True,
    )
    cmd = command()

    getattr(runner, public_method)(cmd)

    inner.assert_called_once_with(cmd)
