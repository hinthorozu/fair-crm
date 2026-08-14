from uuid import uuid4

import httpx

from app.integrations.kyrox_core.client import HttpAuthorizationAdapter


class StubCoreClient:
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.calls: list[dict] = []

    def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        self.calls.append({"method": method, "path": path, **kwargs})
        return self.response


def test_accepts_core_super_admin_allow_for_unseeded_permission() -> None:
    organization_id = uuid4()
    permission_code = "fair_crm.future_module.unseeded"
    core = StubCoreClient(
        httpx.Response(
            200,
            json={"allowed": True, "permission_code": permission_code},
        )
    )

    allowed = HttpAuthorizationAdapter(http_client=core).check_permission(
        organization_id=organization_id,
        user_id=uuid4(),
        permission_code=permission_code,
        access_token="token",
    )

    assert allowed is True
    assert core.calls == [
        {
            "method": "POST",
            "path": f"/api/v1/organizations/{organization_id}/authorization/check",
            "access_token": "token",
            "organization_id": organization_id,
            "json": {"permission_code": permission_code},
        }
    ]
