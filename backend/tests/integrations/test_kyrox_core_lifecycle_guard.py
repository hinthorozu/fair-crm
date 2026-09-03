from uuid import UUID, uuid4

import httpx
import pytest

from app.integrations.kyrox_core.lifecycle import (
    KyroxCoreLifecycleClient,
    OrganizationLifecycleGuard,
    OrganizationLifecycleUnavailableError,
    OrganizationWorkNotAllowedError,
)


class StubLifecycleClient:
    def __init__(
        self,
        response: httpx.Response | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.calls: list[UUID] = []

    def get_snapshot(self, organization_id: UUID) -> httpx.Response:
        self.calls.append(organization_id)
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


def test_lifecycle_http_client_uses_dedicated_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    organization_id = uuid4()
    captured: dict[str, object] = {}

    class CapturingHttpClient:
        def __init__(self, *, timeout: float) -> None:
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            _ = (exc_type, exc, tb)

        def get(self, url: str, *, headers: dict[str, str]) -> httpx.Response:
            captured["url"] = url
            captured["headers"] = headers
            return httpx.Response(
                200,
                json={
                    "organization_id": str(organization_id),
                    "status": "active",
                    "work_allowed": True,
                },
            )

    monkeypatch.setattr(
        "app.integrations.kyrox_core.lifecycle.httpx.Client",
        CapturingHttpClient,
    )

    response = KyroxCoreLifecycleClient(
        base_url="http://core.example/",
        lifecycle_token="lifecycle-secret",
    ).get_snapshot(organization_id)

    assert response.status_code == 200
    assert captured["url"] == (
        f"http://core.example/api/v1/organizations/{organization_id}/lifecycle-snapshot"
    )
    assert captured["headers"] == {
        "X-Kyrox-Product-Lifecycle-Token": "lifecycle-secret",
        "Accept": "application/json",
    }
    assert captured["timeout"] == 10.0


def test_allows_active_organization() -> None:
    organization_id = uuid4()
    client = StubLifecycleClient(
        response=httpx.Response(
            200,
            json={
                "organization_id": str(organization_id),
                "status": "active",
                "work_allowed": True,
            },
        )
    )

    snapshot = OrganizationLifecycleGuard(client=client).require_work_allowed(organization_id)

    assert snapshot.organization_id == organization_id
    assert snapshot.status == "active"
    assert snapshot.work_allowed is True
    assert client.calls == [organization_id]


def test_denies_suspended_organization() -> None:
    organization_id = uuid4()
    client = StubLifecycleClient(
        response=httpx.Response(
            200,
            json={
                "organization_id": str(organization_id),
                "status": "suspended",
                "work_allowed": False,
            },
        )
    )

    with pytest.raises(OrganizationWorkNotAllowedError):
        OrganizationLifecycleGuard(client=client).require_work_allowed(organization_id)


def test_fails_closed_when_core_is_unreachable() -> None:
    organization_id = uuid4()
    request = httpx.Request("GET", "http://core/lifecycle")
    client = StubLifecycleClient(error=httpx.ConnectError("unreachable", request=request))

    with pytest.raises(OrganizationLifecycleUnavailableError):
        OrganizationLifecycleGuard(client=client).require_work_allowed(organization_id)


def test_fails_closed_on_inconsistent_snapshot() -> None:
    organization_id = uuid4()
    client = StubLifecycleClient(
        response=httpx.Response(
            200,
            json={
                "organization_id": str(organization_id),
                "status": "suspended",
                "work_allowed": True,
            },
        )
    )

    with pytest.raises(OrganizationLifecycleUnavailableError):
        OrganizationLifecycleGuard(client=client).require_work_allowed(organization_id)


def test_fails_closed_when_snapshot_is_for_another_organization() -> None:
    organization_id = uuid4()
    client = StubLifecycleClient(
        response=httpx.Response(
            200,
            json={
                "organization_id": str(uuid4()),
                "status": "active",
                "work_allowed": True,
            },
        )
    )

    with pytest.raises(OrganizationLifecycleUnavailableError):
        OrganizationLifecycleGuard(client=client).require_work_allowed(organization_id)


def test_fails_closed_on_unhashable_malformed_status() -> None:
    organization_id = uuid4()
    client = StubLifecycleClient(
        response=httpx.Response(
            200,
            json={
                "organization_id": str(organization_id),
                "status": ["active"],
                "work_allowed": True,
            },
        )
    )

    with pytest.raises(OrganizationLifecycleUnavailableError):
        OrganizationLifecycleGuard(client=client).require_work_allowed(organization_id)
