from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.modules.cost_catalog.api import dependencies, routes


class FakeAuthorization:
    def __init__(self, allowed: set[str]) -> None:
        self.allowed = allowed
        self.checked: list[str] = []

    def check_permission(
        self,
        *,
        organization_id,
        user_id,
        permission_code: str,
        access_token: str,
    ) -> bool:
        self.checked.append(permission_code)
        return permission_code in self.allowed


def auth_context():
    return SimpleNamespace(organization_id=uuid4(), user_id=uuid4())


def credentials() -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token")


def test_require_any_permission_accepts_writer_without_read(monkeypatch) -> None:
    monkeypatch.setattr(dependencies, "dev_bypass_enabled", lambda: False)
    authorization = FakeAuthorization({dependencies.PRODUCT_CREATE})
    dependency = dependencies.require_any_permission(
        dependencies.PRODUCT_VIEW,
        dependencies.PRODUCT_CREATE,
        dependencies.PRODUCT_UPDATE,
    )

    result = dependency(
        auth=auth_context(),
        authorization=authorization,
        credentials=credentials(),
    )

    assert result is not None
    assert authorization.checked == [dependencies.PRODUCT_VIEW, dependencies.PRODUCT_CREATE]


def test_require_any_permission_denies_when_no_permission_matches(monkeypatch) -> None:
    monkeypatch.setattr(dependencies, "dev_bypass_enabled", lambda: False)
    authorization = FakeAuthorization(set())
    dependency = dependencies.require_any_permission(
        dependencies.PRODUCT_VIEW,
        dependencies.PRODUCT_CREATE,
        dependencies.PRODUCT_UPDATE,
    )

    with pytest.raises(HTTPException) as exc_info:
        dependency(
            auth=auth_context(),
            authorization=authorization,
            credentials=credentials(),
        )

    assert exc_info.value.status_code == 403
    assert authorization.checked == [
        dependencies.PRODUCT_VIEW,
        dependencies.PRODUCT_CREATE,
        dependencies.PRODUCT_UPDATE,
    ]


def test_require_any_permission_rejects_empty_permission_set() -> None:
    with pytest.raises(ValueError, match="At least one permission code"):
        dependencies.require_any_permission()


def test_category_options_support_product_read_create_or_update_only() -> None:
    route = next(
        route
        for route in routes.router.routes
        if getattr(route, "path", "") == "/cost-catalog/products/category-options"
    )
    dependency = route.dependant.dependencies[1].call

    assert dependency is not None
    assert dependency.__name__ == "dependency"

    # The normal product list remains a separate PRODUCT_VIEW-only endpoint.
    list_route = next(
        route
        for route in routes.router.routes
        if getattr(route, "path", "") == "/cost-catalog/products"
        and "GET" in getattr(route, "methods", set())
    )
    assert list_route.dependant.dependencies[1].call is not dependency
