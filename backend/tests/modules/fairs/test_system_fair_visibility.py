from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from app.integrations.kyrox_core.auth import create_test_token
from app.modules.fairs.domain.entities import Fair
from app.modules.fairs.domain.value_objects import FairStatus
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository


def _other_headers(user_id, organization_id) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(organization_id),
    }


def _system_fair(
    name: str = "Shared System Fair",
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    external_id: str | None = None,
) -> Fair:
    now = datetime.now(tz=UTC)
    return Fair(
        id=uuid4(),
        organization_id=None,
        name=name,
        organizer=None,
        venue="System Hall",
        city="Ankara",
        country=None,
        start_date=start_date,
        end_date=end_date,
        website=None,
        status=FairStatus.PLANNED,
        description=None,
        normalized_name=name.lower(),
        created_at=now,
        updated_at=now,
        deleted_at=None,
        origin="system",
        source="tobb",
        external_id=external_id or str(uuid4()),
        adapter_key="tobb_calendar",
        source_url="https://fuarlar.tobb.org.tr/FuarTakvimi",
    )


def _naive(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


def _row_snapshot(db_session, fair_id) -> tuple:
    model = db_session.get(FairModel, fair_id)
    return (
        model.name,
        model.status,
        _naive(model.deleted_at),
        _naive(model.updated_at),
        model.organization_id,
        model.origin,
    )


def test_organization_fair_create_keeps_organization_origin(client, auth_headers, organization_id):
    response = client.post(
        "/api/v1/fairs",
        json={"name": "Customer Owned Fair"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["origin"] == "organization"
    assert body["organization_id"] == str(organization_id)
    assert "source" not in body
    assert "external_id" not in body


def test_own_fair_remains_visible_and_other_organization_stays_hidden(
    client, auth_headers, db_session, organization_id, other_organization_id, user_id
):
    own = client.post(
        "/api/v1/fairs",
        json={"name": "Own Organization Fair"},
        headers=auth_headers,
    )
    assert own.status_code == 201
    own_id = own.json()["id"]

    other = SqlAlchemyFairRepository(db_session).add(
        Fair.create(
            organization_id=other_organization_id,
            name="Other Organization Fair",
            now=datetime.now(tz=UTC),
        )
    )

    listed = client.get("/api/v1/fairs", headers=auth_headers)
    assert listed.status_code == 200
    listed_ids = {item["id"] for item in listed.json()["items"]}
    assert own_id in listed_ids
    assert str(other.id) not in listed_ids

    detail = client.get(f"/api/v1/fairs/{own_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["origin"] == "organization"

    other_headers = _other_headers(user_id, organization_id)
    hidden = client.get(f"/api/v1/fairs/{other.id}", headers=other_headers)
    assert hidden.status_code == 404
    assert client.patch(
        f"/api/v1/fairs/{other.id}",
        json={"name": "Stolen"},
        headers=other_headers,
    ).status_code == 404
    assert client.delete(f"/api/v1/fairs/{other.id}", headers=other_headers).status_code == 404
    assert client.post(
        f"/api/v1/fairs/{other.id}/restore",
        headers=other_headers,
    ).status_code == 404


def test_system_fair_is_visible_and_read_only(
    client, auth_headers, db_session, organization_id
):
    system = SqlAlchemyFairRepository(db_session).add(_system_fair())
    before = _row_snapshot(db_session, system.id)

    listed = client.get("/api/v1/fairs", headers=auth_headers)
    assert listed.status_code == 200
    matched = next(item for item in listed.json()["items"] if item["id"] == str(system.id))
    assert matched["origin"] == "system"
    assert matched["organization_id"] is None
    assert matched["adapter_key"] == "tobb_calendar"
    assert matched["source_url"] == "https://fuarlar.tobb.org.tr/FuarTakvimi"
    assert "source" not in matched
    assert "external_id" not in matched

    detail = client.get(f"/api/v1/fairs/{system.id}", headers=auth_headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["origin"] == "system"
    assert body["organization_id"] is None
    assert "source" not in body
    assert "external_id" not in body

    assert client.patch(
        f"/api/v1/fairs/{system.id}",
        json={"name": "Renamed System Fair"},
        headers=auth_headers,
    ).status_code == 403
    assert client.delete(f"/api/v1/fairs/{system.id}", headers=auth_headers).status_code == 403
    assert client.post(
        f"/api/v1/fairs/{system.id}/restore",
        headers=auth_headers,
    ).status_code == 403

    db_session.expire_all()
    assert _row_snapshot(db_session, system.id) == before


def test_archived_system_fair_restore_is_forbidden(client, auth_headers, db_session):
    system = SqlAlchemyFairRepository(db_session).add(_system_fair("Archived System Fair"))
    model = db_session.get(FairModel, system.id)
    archived_at = datetime.now(tz=UTC)
    model.deleted_at = archived_at
    db_session.flush()
    before = _row_snapshot(db_session, system.id)

    response = client.post(f"/api/v1/fairs/{system.id}/restore", headers=auth_headers)
    assert response.status_code == 403

    db_session.expire_all()
    assert _row_snapshot(db_session, system.id) == before


def test_system_fair_list_and_detail_status_follow_dates(
    client, auth_headers, db_session, organization_id
):
    repo = SqlAlchemyFairRepository(db_session)
    past = repo.add(
        _system_fair(
            "January System Fair",
            start_date=date(2020, 1, 6),
            end_date=date(2020, 1, 9),
        )
    )
    current = repo.add(
        _system_fair(
            "Spanning System Fair",
            start_date=date(2000, 1, 1),
            end_date=date(2099, 12, 31),
        )
    )
    future = repo.add(
        _system_fair(
            "Future System Fair",
            start_date=date(2099, 10, 5),
            end_date=date(2099, 10, 8),
        )
    )
    organization = client.post(
        "/api/v1/fairs",
        json={
            "name": "Past Organization Fair",
            "status": "active",
            "start_date": "2020-01-06",
            "end_date": "2020-01-09",
        },
        headers=auth_headers,
    )
    assert organization.status_code == 201
    assert organization.json()["status"] == "active"

    listed = client.get("/api/v1/fairs", headers=auth_headers)
    assert listed.status_code == 200
    by_id = {item["id"]: item["status"] for item in listed.json()["items"]}
    assert by_id[str(past.id)] == "completed"
    assert by_id[str(current.id)] == "active"
    assert by_id[str(future.id)] == "planned"
    assert by_id[organization.json()["id"]] == "active"

    detail = client.get(f"/api/v1/fairs/{past.id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "completed"

    completed = client.get("/api/v1/fairs?status=completed", headers=auth_headers)
    completed_ids = {item["id"] for item in completed.json()["items"]}
    assert str(past.id) in completed_ids
    assert str(future.id) not in completed_ids
    assert organization.json()["id"] not in completed_ids

    db_session.expire_all()
    assert db_session.get(FairModel, past.id).status == FairStatus.PLANNED.value
    assert db_session.get(FairModel, UUID(organization.json()["id"])).status == FairStatus.ACTIVE.value
