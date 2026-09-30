from datetime import date
from uuid import uuid4

from app.integrations.kyrox_core.auth import create_test_token
from app.integrations.kyrox_core.super_admin import get_super_admin_reader
from app.modules.fairs.api.dependencies import get_sync_tobb_system_fairs_use_case
from app.modules.fairs.application.sync_tobb_system_fairs import (
    SyncTobbSystemFairsUseCase,
    TobbSyncResult,
)
from app.modules.fairs.domain.exceptions import TobbCalendarReadError
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
from app.modules.fairs.infrastructure.tobb_calendar import TobbCalendarClient, TobbFairRow


def _headers(user_id, organization_id):
    return {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(organization_id),
    }


def _as_super_admin(client) -> None:
    client.app.dependency_overrides[get_super_admin_reader] = lambda: (
        lambda _access_token, _organization_id: True
    )


class _Reader:
    def __init__(self, rows: list[TobbFairRow]) -> None:
        self.rows = rows
        self.years: list[int] = []

    def read(self, year: int) -> list[TobbFairRow]:
        self.years.append(year)
        return self.rows


class _FixedResultUseCase(SyncTobbSystemFairsUseCase):
    def __init__(self) -> None:
        self.years: list[int] = []

    def execute(self, year: int) -> TobbSyncResult:
        self.years.append(year)
        return TobbSyncResult(inserted=120, updated=35, conflicts=2)


class _FailingUseCase(SyncTobbSystemFairsUseCase):
    def __init__(self) -> None:
        self.called = False

    def execute(self, year: int) -> TobbSyncResult:
        self.called = True
        raise TobbCalendarReadError("TOBB calendar request timed out")


def test_sync_dependency_builds_existing_use_case(db_session):
    use_case = get_sync_tobb_system_fairs_use_case(SqlAlchemyFairRepository(db_session))

    assert isinstance(use_case, SyncTobbSystemFairsUseCase)
    assert isinstance(use_case._reader, TobbCalendarClient)


def test_super_admin_sync_calls_existing_use_case_with_explicit_year(
    client, db_session, auth_headers
):
    reader = _Reader(
        rows=[
            TobbFairRow(
                sequence_no="7",
                name="Win Eurasia",
                organizer="TÜYAP",
                venue="Tüyap",
                city="İstanbul",
                start_date=date(2026, 9, 1),
                end_date=date(2026, 9, 5),
                website="https://example.test",
            )
        ]
    )
    use_case = SyncTobbSystemFairsUseCase(SqlAlchemyFairRepository(db_session), reader)
    client.app.dependency_overrides[get_sync_tobb_system_fairs_use_case] = lambda: use_case
    _as_super_admin(client)

    response = client.post(
        "/api/v1/fairs/system/tobb/sync",
        headers=auth_headers,
        json={"year": 2026},
    )

    assert response.status_code == 200
    assert response.json() == {"inserted": 1, "updated": 0, "conflicts": 0}
    assert reader.years == [2026]
    saved = db_session.query(FairModel).filter(FairModel.external_id == "2026:7").one()
    assert saved.origin == "system"
    assert saved.source == "tobb"
    assert saved.organization_id is None


def test_sync_response_maps_use_case_counts(client, auth_headers):
    use_case = _FixedResultUseCase()
    client.app.dependency_overrides[get_sync_tobb_system_fairs_use_case] = lambda: use_case
    _as_super_admin(client)

    response = client.post(
        "/api/v1/fairs/system/tobb/sync",
        headers=auth_headers,
        json={"year": 2024},
    )

    assert response.status_code == 200
    assert response.json() == {"inserted": 120, "updated": 35, "conflicts": 2}
    assert use_case.years == [2024]


def test_organization_admin_cannot_sync_tobb_fairs(client, auth_headers):
    use_case = _FailingUseCase()
    client.app.dependency_overrides[get_sync_tobb_system_fairs_use_case] = lambda: use_case

    response = client.post(
        "/api/v1/fairs/system/tobb/sync",
        headers=auth_headers,
        json={"year": 2026},
    )

    assert response.status_code == 403
    assert use_case.called is False


def test_organization_user_cannot_sync_tobb_fairs(client, organization_id):
    use_case = _FailingUseCase()
    client.app.dependency_overrides[get_sync_tobb_system_fairs_use_case] = lambda: use_case
    headers = _headers(uuid4(), organization_id)

    response = client.post(
        "/api/v1/fairs/system/tobb/sync",
        headers=headers,
        json={"year": 2026},
    )

    assert response.status_code == 403
    assert use_case.called is False


def test_tobb_sync_failure_returns_api_error(client, auth_headers):
    use_case = _FailingUseCase()
    client.app.dependency_overrides[get_sync_tobb_system_fairs_use_case] = lambda: use_case
    _as_super_admin(client)

    response = client.post(
        "/api/v1/fairs/system/tobb/sync",
        headers=auth_headers,
        json={"year": 2026},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "TOBB calendar request timed out"
    assert use_case.called is True
