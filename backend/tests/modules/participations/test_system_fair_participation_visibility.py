from datetime import UTC, datetime
from uuid import uuid4

from app.integrations.kyrox_core.auth import create_test_token
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fairs.domain.entities import Fair
from app.modules.fairs.domain.services.normalizers import compute_normalized_name
from app.modules.fairs.domain.value_objects import FairStatus
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.handoff_storage import resolve_handoff_path, write_handoff_json
from app.modules.scraper.infrastructure.persistence.models import ScraperRunHistoryModel
from tests.conftest_helpers import pagination_from
from tests.modules.imports.import_decision_helpers import apply_import_decisions


def _system_fair(name: str) -> Fair:
    now = datetime.now(tz=UTC)
    return Fair(
        id=uuid4(),
        organization_id=None,
        name=name,
        organizer=None,
        venue=None,
        city=None,
        country="Türkiye",
        start_date=None,
        end_date=None,
        website=None,
        status=FairStatus.PLANNED,
        description=None,
        normalized_name=compute_normalized_name(name=name),
        created_at=now,
        updated_at=now,
        deleted_at=None,
        origin="system",
        source="tobb",
        external_id=f"2026:{uuid4().hex[:8]}",
    )


def _headers(user_id, organization_id) -> dict[str, str]:
    token = create_test_token(user_id=user_id)
    return {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": str(organization_id),
    }


def _write_completed_run(db_session, fair_id, company_name: str, *, finished_at=None):
    finished = finished_at or datetime(2026, 3, 15, tzinfo=UTC)
    run = ScraperRunHistoryModel(
        id=uuid4(),
        adapter_key="tuyap_new",
        status="completed",
        started_at=finished,
        finished_at=finished,
        organization_id=None,
        fair_id=fair_id,
        total_rows=1,
        website_count=0,
        email_count=0,
        phone_count=0,
        instagram_count=0,
        linkedin_count=0,
        facebook_count=0,
        youtube_count=0,
        x_count=0,
        run_source="fair_automation",
    )
    db_session.add(run)
    db_session.flush()
    path = write_handoff_json(
        ScraperImportHandoff(
            canonical_rows=[{"company_name": company_name, "website": "", "email": "", "phone": ""}],
            row_metadata=[{}],
        ),
        run.id,
        adapter_key="tuyap_new",
        fair_id=fair_id,
        source_url="https://foodist.test/brands",
    )
    run.output_json_path = path
    db_session.flush()
    return run


def _apply_compare(client, headers, fair_id):
    created = client.post(f"/api/v1/fairs/{fair_id}/compare-import", headers=headers)
    assert created.status_code == 201, created.text
    batch_id = created.json()["batch_id"]
    rows = client.get(
        f"/api/v1/data-integration/imports/{batch_id}/rows",
        headers=headers,
    )
    assert rows.status_code == 200, rows.text
    row_id = rows.json()["items"][0]["id"]
    decision = client.patch(
        f"/api/v1/data-integration/imports/{batch_id}/rows/{row_id}/decision",
        headers=headers,
        json={"decision": "create_new"},
    )
    assert decision.status_code == 200, decision.text
    applied = apply_import_decisions(client, headers, batch_id, row_ids=[row_id])
    assert applied.status_code == 200, applied.text
    return batch_id


def _customer(db_session, organization_id, display_name: str) -> CustomerModel:
    return (
        db_session.query(CustomerModel)
        .filter(
            CustomerModel.organization_id == organization_id,
            CustomerModel.display_name == display_name,
        )
        .one()
    )


def _participations(db_session, fair_id):
    return (
        db_session.query(CustomerFairParticipationModel)
        .filter(CustomerFairParticipationModel.fair_id == fair_id)
        .all()
    )


def test_system_fair_apply_is_visible_to_the_same_organization(
    client, auth_headers, db_session, organization_id
):
    fair = SqlAlchemyFairRepository(db_session).add(_system_fair("Visible System Fair"))
    run = _write_completed_run(db_session, fair.id, "Alpha Co")
    try:
        _apply_compare(client, auth_headers, fair.id)
        stored = _participations(db_session, fair.id)
        assert len(stored) == 1
        assert stored[0].organization_id == organization_id
        assert stored[0].fair_id == fair.id
        assert fair.organization_id is None

        customer = _customer(db_session, organization_id, "Alpha Co")
        customer_fairs = client.get(
            f"/api/v1/customers/{customer.id}/fair-participations",
            headers=auth_headers,
        )
        assert customer_fairs.status_code == 200
        assert pagination_from(customer_fairs.json())["totalItems"] == 1
        assert customer_fairs.json()["items"][0]["fair_name"] == "Visible System Fair"

        participants = client.get(f"/api/v1/fairs/{fair.id}/participants", headers=auth_headers)
        assert participants.status_code == 200
        assert pagination_from(participants.json())["totalItems"] == 1
        assert participants.json()["items"][0]["company_name"] == "Alpha Co"
    finally:
        resolve_handoff_path(run.id).unlink(missing_ok=True)


def test_two_organizations_see_only_their_system_fair_participants(
    client, db_session, organization_id, other_organization_id, user_id
):
    fair = SqlAlchemyFairRepository(db_session).add(_system_fair("Shared Visible Fair"))
    run_a = _write_completed_run(db_session, fair.id, "Alpha Co")
    headers_a = _headers(user_id, organization_id)
    headers_b = _headers(user_id, other_organization_id)
    try:
        _apply_compare(client, headers_a, fair.id)
        run_b = _write_completed_run(
            db_session,
            fair.id,
            "Beta Co",
            finished_at=datetime(2026, 6, 1, tzinfo=UTC),
        )
        try:
            _apply_compare(client, headers_b, fair.id)
            stored = _participations(db_session, fair.id)
            by_org = {row.organization_id: row for row in stored}
            assert set(by_org) == {organization_id, other_organization_id}
            assert by_org[organization_id].fair_id == fair.id
            assert by_org[other_organization_id].fair_id == fair.id

            participants_a = client.get(f"/api/v1/fairs/{fair.id}/participants", headers=headers_a)
            participants_b = client.get(f"/api/v1/fairs/{fair.id}/participants", headers=headers_b)
            assert participants_a.status_code == 200
            assert participants_b.status_code == 200
            names_a = {item["company_name"] for item in participants_a.json()["items"]}
            names_b = {item["company_name"] for item in participants_b.json()["items"]}
            assert names_a == {"Alpha Co"}
            assert names_b == {"Beta Co"}

            customer_a = _customer(db_session, organization_id, "Alpha Co")
            customer_b = _customer(db_session, other_organization_id, "Beta Co")
            fairs_a = client.get(
                f"/api/v1/customers/{customer_a.id}/fair-participations",
                headers=headers_a,
            )
            fairs_b = client.get(
                f"/api/v1/customers/{customer_b.id}/fair-participations",
                headers=headers_b,
            )
            hidden_a = client.get(
                f"/api/v1/customers/{customer_b.id}/fair-participations",
                headers=headers_a,
            )
            hidden_b = client.get(
                f"/api/v1/customers/{customer_a.id}/fair-participations",
                headers=headers_b,
            )
            assert pagination_from(fairs_a.json())["totalItems"] == 1
            assert pagination_from(fairs_b.json())["totalItems"] == 1
            assert hidden_a.status_code == 404
            assert hidden_b.status_code == 404
        finally:
            resolve_handoff_path(run_b.id).unlink(missing_ok=True)
    finally:
        resolve_handoff_path(run_a.id).unlink(missing_ok=True)


def test_other_organization_fair_participants_stay_not_found(
    client, auth_headers, db_session, other_organization_id
):
    now = datetime.now(tz=UTC)
    fair = SqlAlchemyFairRepository(db_session).add(
        Fair.create(organization_id=other_organization_id, name="Hidden Org Fair", now=now)
    )
    response = client.get(f"/api/v1/fairs/{fair.id}/participants", headers=auth_headers)
    assert response.status_code == 404


def test_organization_adds_customer_to_system_fair_without_editing_the_fair(
    client, auth_headers, db_session, organization_id
):
    fair = SqlAlchemyFairRepository(db_session).add(_system_fair("Manual System Fair"))
    customer = client.post(
        "/api/v1/customers",
        json={"display_name": "Manual Co", "status": "active"},
        headers=auth_headers,
    )
    assert customer.status_code == 201
    response = client.post(
        "/api/v1/fair-participations",
        headers=auth_headers,
        json={"customer_id": customer.json()["id"], "fair_id": str(fair.id), "hall": "A"},
    )
    assert response.status_code == 201, response.text
    stored = _participations(db_session, fair.id)
    assert len(stored) == 1
    assert stored[0].organization_id == organization_id
    assert stored[0].fair_id == fair.id

    removed = client.delete(
        f"/api/v1/fair-participations/{response.json()['id']}",
        headers=auth_headers,
    )
    assert removed.status_code == 200, removed.text
    db_session.expire_all()
    stored = _participations(db_session, fair.id)
    assert len(stored) == 1
    assert stored[0].deleted_at is not None
    participants = client.get(f"/api/v1/fairs/{fair.id}/participants", headers=auth_headers)
    assert participants.status_code == 200
    assert pagination_from(participants.json())["totalItems"] == 0

    unchanged = SqlAlchemyFairRepository(db_session).get_visible(organization_id, fair.id)
    assert unchanged is not None
    assert unchanged.origin == "system"
    assert unchanged.organization_id is None
    assert unchanged.name == "Manual System Fair"

    edited = client.patch(
        f"/api/v1/fairs/{fair.id}",
        headers=auth_headers,
        json={"name": "Changed Name"},
    )
    archived = client.delete(f"/api/v1/fairs/{fair.id}", headers=auth_headers)
    assert edited.status_code == 403
    assert archived.status_code == 403


def test_organization_fair_participation_lists_stay_available(client, auth_headers):
    customer = client.post(
        "/api/v1/customers",
        json={"display_name": "Org Fair Co", "status": "active"},
        headers=auth_headers,
    )
    fair = client.post(
        "/api/v1/fairs",
        json={"name": "Own Organization Fair", "status": "planned"},
        headers=auth_headers,
    )
    assert customer.status_code == 201
    assert fair.status_code == 201
    created = client.post(
        "/api/v1/fair-participations",
        headers=auth_headers,
        json={"customer_id": customer.json()["id"], "fair_id": fair.json()["id"], "hall": "B"},
    )
    assert created.status_code == 201
    customer_fairs = client.get(
        f"/api/v1/customers/{customer.json()['id']}/fair-participations",
        headers=auth_headers,
    )
    participants = client.get(
        f"/api/v1/fairs/{fair.json()['id']}/participants",
        headers=auth_headers,
    )
    assert customer_fairs.status_code == 200
    assert participants.status_code == 200
    assert pagination_from(customer_fairs.json())["totalItems"] == 1
    assert customer_fairs.json()["items"][0]["fair_name"] == "Own Organization Fair"
    assert participants.json()["items"][0]["company_name"] == "Org Fair Co"
