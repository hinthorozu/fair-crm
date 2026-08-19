from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute
from fastapi.security import HTTPAuthorizationCredentials

from app.integrations.kyrox_core.ports import AuthContext
from app.modules.customers.api.dependencies import (
    PERMISSION_EXECUTE,
    require_execute_permission,
    require_read_permission,
)
from app.modules.customers.api.routes import router


class StubAuthorization:
    def __init__(self, allowed: bool) -> None:
        self.allowed = allowed
        self.permission_codes: list[str] = []

    def check_permission(
        self,
        *,
        organization_id,
        user_id,
        permission_code: str,
        access_token: str,
    ) -> bool:
        self.permission_codes.append(permission_code)
        return self.allowed


def auth_context() -> AuthContext:
    return AuthContext(
        user_id=uuid4(),
        email="permission-test@example.com",
        session_id=uuid4(),
        organization_id=uuid4(),
    )


def credentials() -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="access-token")


def test_customer_export_uses_execute_permission_dependency() -> None:
    export_route = next(
        route
        for route in router.routes
        if isinstance(route, APIRoute)
        and route.path == "/customers/export"
        and "GET" in route.methods
    )

    dependency_calls = {dependency.call for dependency in export_route.dependant.dependencies}

    assert PERMISSION_EXECUTE == "fair_crm.customers.execute"
    assert require_execute_permission in dependency_calls
    assert require_read_permission not in dependency_calls


def test_execute_permission_denies_when_core_denies(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.modules.customers.api.dependencies.dev_bypass_enabled",
        lambda: False,
    )
    authorization = StubAuthorization(allowed=False)

    with pytest.raises(HTTPException) as exc_info:
        require_execute_permission(
            auth=auth_context(),
            authorization=authorization,
            credentials=credentials(),
        )

    assert exc_info.value.status_code == 403
    assert authorization.permission_codes == ["fair_crm.customers.execute"]


def test_execute_permission_allows_when_core_allows(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.modules.customers.api.dependencies.dev_bypass_enabled",
        lambda: False,
    )
    authorization = StubAuthorization(allowed=True)
    auth = auth_context()

    result = require_execute_permission(
        auth=auth,
        authorization=authorization,
        credentials=credentials(),
    )

    assert result == auth
    assert authorization.permission_codes == ["fair_crm.customers.execute"]
