from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from app.integrations.kyrox_core.tombstone import (
    EXPECTED_SUSPENSION_EPISODE_HEADER,
    CoreOrganizationTombstoneConflictError,
    CoreOrganizationTombstoneUnavailableError,
    KyroxCoreOrganizationTombstoneAdapter,
)


class FakeHttpClient:
    def __init__(self, *, status_code: int = 204, error: Exception | None = None) -> None:
        self.status_code = status_code
        self.error = error
        self.calls: list[dict[str, object]] = []

    def request(self, method: str, path: str, **kwargs: object):
        self.calls.append({"method": method, "path": path, **kwargs})
        if self.error is not None:
            raise self.error
        return SimpleNamespace(status_code=self.status_code)


def test_conditional_tombstone_sends_exact_suspension_episode_header() -> None:
    organization_id = uuid4()
    episode = datetime(2026, 9, 10, 1, 23, 45, 678901, tzinfo=UTC)
    http = FakeHttpClient(status_code=204)
    adapter = KyroxCoreOrganizationTombstoneAdapter(http_client=http)

    adapter.delete_suspended_episode(
        organization_id=organization_id,
        expected_suspension_updated_at=episode,
        access_token="access-token",
    )

    assert http.calls == [
        {
            "method": "DELETE",
            "path": f"/api/v1/organizations/{organization_id}",
            "access_token": "access-token",
            "organization_id": organization_id,
            "extra_headers": {
                EXPECTED_SUSPENSION_EPISODE_HEADER: episode.isoformat(),
            },
        }
    ]


@pytest.mark.parametrize("status_code", [404, 409, 400, 403])
def test_conditional_tombstone_rejection_is_fail_closed(status_code: int) -> None:
    adapter = KyroxCoreOrganizationTombstoneAdapter(
        http_client=FakeHttpClient(status_code=status_code)
    )

    with pytest.raises(CoreOrganizationTombstoneConflictError):
        adapter.delete_suspended_episode(
            organization_id=uuid4(),
            expected_suspension_updated_at=datetime(2026, 9, 10, tzinfo=UTC),
            access_token="access-token",
        )


@pytest.mark.parametrize("status_code", [500, 503])
def test_conditional_tombstone_server_failure_is_unavailable(status_code: int) -> None:
    adapter = KyroxCoreOrganizationTombstoneAdapter(
        http_client=FakeHttpClient(status_code=status_code)
    )

    with pytest.raises(CoreOrganizationTombstoneUnavailableError):
        adapter.delete_suspended_episode(
            organization_id=uuid4(),
            expected_suspension_updated_at=datetime(2026, 9, 10, tzinfo=UTC),
            access_token="access-token",
        )


def test_conditional_tombstone_transport_failure_is_unavailable() -> None:
    request = httpx.Request("DELETE", "http://core.test/api/v1/organizations/example")
    adapter = KyroxCoreOrganizationTombstoneAdapter(
        http_client=FakeHttpClient(error=httpx.ConnectError("offline", request=request))
    )

    with pytest.raises(CoreOrganizationTombstoneUnavailableError):
        adapter.delete_suspended_episode(
            organization_id=uuid4(),
            expected_suspension_updated_at=datetime(2026, 9, 10, tzinfo=UTC),
            access_token="access-token",
        )
