from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.integrations.kyrox_core.ports import AuthContext
from app.modules.organization_closure.api.routes import (
    _assert_target_context,
    _normalize_idempotency_key,
    router,
)


def _auth(organization_id):
    return AuthContext(
        user_id=uuid4(),
        email="platform-admin@example.com",
        session_id=uuid4(),
        organization_id=organization_id,
    )


def test_foreign_organization_target_is_denied_before_service_mutation() -> None:
    auth = _auth(uuid4())

    with pytest.raises(HTTPException) as exc_info:
        _assert_target_context(auth, uuid4())

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Organization context mismatch"


def test_idempotency_key_is_required_to_be_stable_and_bounded() -> None:
    assert _normalize_idempotency_key("  closure-123  ") == "closure-123"

    for invalid in ("   ", "x" * 201):
        with pytest.raises(HTTPException) as exc_info:
            _normalize_idempotency_key(invalid)
        assert exc_info.value.status_code == 422


def test_ol08_01_public_contract_has_only_start_status_and_retry() -> None:
    operations = {
        (method, route.path)
        for route in router.routes
        for method in getattr(route, "methods", set())
    }

    assert operations == {
        ("POST", "/system-admin/organizations/{organization_id}/closure-executions"),
        (
            "GET",
            "/system-admin/organizations/{organization_id}/closure-executions/{execution_id}",
        ),
        (
            "POST",
            "/system-admin/organizations/{organization_id}/closure-executions/{execution_id}/retry",
        ),
    }
    assert all(method != "DELETE" for method, _ in operations)
    assert all("complete" not in path and "tombstone" not in path for _, path in operations)
