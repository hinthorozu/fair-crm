from fastapi.routing import APIRoute

from app.modules.customers.api.dependencies import (
    PERMISSION_EXECUTE,
    require_execute_permission,
    require_read_permission,
)
from app.modules.customers.api.routes import router


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
