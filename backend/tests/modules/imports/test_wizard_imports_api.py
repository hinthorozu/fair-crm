"""Smart Import Wizard Phase 1 API tests."""

from io import BytesIO
from uuid import UUID

import pytest
from openpyxl import Workbook

from tests.conftest_helpers import pagination_from
from tests.modules.imports.import_decision_helpers import apply_import_decisions

from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.value_objects import CustomerSource
from app.modules.customers.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)
from app.modules.imports.application.column_mapper import validate_column_mapping
from app.modules.imports.domain.exceptions import InvalidColumnMappingError
from app.modules.participations.domain.entities import CustomerFairParticipation
from app.modules.participations.domain.value_objects import ParticipationStatus
from app.modules.participations.infrastructure.repositories.participation_repository import (
    SqlAlchemyParticipationRepository,
)


def build_xlsx(headers: list[str] | None, rows: list[list[str | None]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    if headers:
        sheet.append(headers)
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def build_headerless_xlsx(rows: list[list[str | None]]) -> bytes:
    return build_xlsx(None, rows)


def _create_fair(client, auth_headers, name="Wizard Fair"):
    response = client.post(
        "/api/v1/fairs",
        headers=auth_headers,
        json={"name": name, "location": "Istanbul", "start_date": "2026-06-05", "end_date": "2026-06-08"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _upload_wizard(client, auth_headers, fair_id, headers, rows, headerless=False):
    content = build_headerless_xlsx(rows) if headerless else build_xlsx(headers, rows)
    return client.post(
        "/api/v1/imports/upload",
        headers=auth_headers,
        data={"fair_id": fair_id},
        files={"file": ("import.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )


def _set_mapping(client, auth_headers, batch_id, has_header_row, mappings):
    return client.patch(
        f"/api/v1/imports/{batch_id}/column-mapping",
        headers=auth_headers,
        json={"has_header_row": has_header_row, "mappings": mappings},
    )


def _analyze(client, auth_headers, batch_id):
    return client.post(f"/api/v1/imports/{batch_id}/analyze-legacy", headers=auth_headers)


def _create_customer(db_session, organization_id: UUID, *, display_name: str) -> Customer:
    from datetime import UTC, datetime

    repo = SqlAlchemyCustomerRepository(db_session)
    now = datetime.now(tz=UTC)
    return repo.add(
        Customer.create(
            organization_id=organization_id,
            display_name=display_name,
            source=CustomerSource.MANUAL,
            now=now,
        )
    )


def test_upload_creates_batch_with_fair_id(client, auth_headers):
    fair_id = _create_fair(client, auth_headers)
    response = _upload_wizard(
        client, auth_headers, fair_id, ["Firma Adı"], [["Acme Ltd"]]
    )
    assert response.status_code == 201
    data = response.json()
    assert data["batch_id"]
    assert data["fair_id"] == fair_id
    assert data["total_rows"] >= 1
    assert data["raw_columns"]
    assert data["sample_rows"]
    assert data["mapping_columns"]
    assert len(data["mapping_columns"][0]["samples"]) <= 10


def test_mapping_preview_endpoint_respects_header_mode(client, auth_headers):
    fair_id = _create_fair(client, auth_headers, "Mapping Preview Fair")
    upload = _upload_wizard(
        client,
        auth_headers,
        fair_id,
        ["Firma Adı", "E-posta"],
        [["Acme Ltd", "a@test.com"], ["Beta Corp", "b@test.com"]],
    )
    batch_id = upload.json()["batch_id"]

    no_header = client.get(
        f"/api/v1/imports/{batch_id}/mapping-preview",
        headers=auth_headers,
        params={"header_mode": "no_header"},
    )
    assert no_header.status_code == 200
    data = no_header.json()
    assert data["columns"][0]["header"] is None
    assert data["columns"][0]["samples"][0] == "Firma Adı"

    manual = client.get(
        f"/api/v1/imports/{batch_id}/mapping-preview",
        headers=auth_headers,
        params={"header_mode": "manual_header_row", "header_row_index": 0},
    )
    assert manual.status_code == 200
    manual_data = manual.json()
    assert manual_data["columns"][0]["header"] == "Firma Adı"
    assert manual_data["columns"][0]["samples"][0] == "Acme Ltd"


def test_upload_returns_raw_preview(client, auth_headers):
    fair_id = _create_fair(client, auth_headers, "Preview Fair")
    response = _upload_wizard(
        client,
        auth_headers,
        fair_id,
        ["Firma Adı", "E-posta"],
        [["Test Co", "a@test.com"]],
    )
    assert response.status_code == 201
    data = response.json()
    assert "Firma" in str(data["detected_headers"]) or data["detected_headers"]
    assert data["suggested_mapping"]["mappings"].get("company_name") is not None


def test_fair_id_required(client, auth_headers):
    content = build_xlsx(["Firma Adı"], [["X"]])
    response = client.post(
        "/api/v1/imports/upload",
        headers=auth_headers,
        files={"file": ("import.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 422


def test_fair_name_mapping_rejected():
    with pytest.raises(InvalidColumnMappingError):
        validate_column_mapping(
            {
                "has_header_row": True,
                "mappings": {
                    "fair_name": {"type": "column_index", "value": 0},
                    "company_name": {"type": "column_index", "value": 1},
                },
            }
        )


def test_headerless_excel_manual_mapping(client, auth_headers):
    fair_id = _create_fair(client, auth_headers, "Headerless Fair")
    upload = _upload_wizard(client, auth_headers, fair_id, None, [["ABC Ltd", "info@abc.com"]], headerless=True)
    assert upload.status_code == 201
    batch_id = upload.json()["batch_id"]

    mapping = _set_mapping(
        client,
        auth_headers,
        batch_id,
        False,
        {
            "company_name": {"type": "column_index", "value": 0},
            "email": {"type": "column_index", "value": 1},
        },
    )
    assert mapping.status_code == 200

    analyze = _analyze(client, auth_headers, batch_id)
    assert analyze.status_code == 200
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    assert rows[0]["normalized_data_json"]["company_name"] == "ABC Ltd"


def test_analyze_fails_without_company_name_mapping(client, auth_headers):
    fair_id = _create_fair(client, auth_headers)
    upload = _upload_wizard(client, auth_headers, fair_id, ["Firma Adı"], [["Only Co"]])
    batch_id = upload.json()["batch_id"]

    bad_mapping = _set_mapping(
        client,
        auth_headers,
        batch_id,
        True,
        {"email": {"type": "column_index", "value": 1}},
    )
    assert bad_mapping.status_code == 400

    analyze = _analyze(client, auth_headers, batch_id)
    assert analyze.status_code == 400


def test_analyze_company_name_only(client, auth_headers):
    fair_id = _create_fair(client, auth_headers)
    upload = _upload_wizard(client, auth_headers, fair_id, ["Firma Adı"], [["Solo Co"]])
    batch_id = upload.json()["batch_id"]
    _set_mapping(
        client,
        auth_headers,
        batch_id,
        True,
        {"company_name": {"type": "column_index", "value": 0}},
    )
    analyze = _analyze(client, auth_headers, batch_id)
    assert analyze.status_code == 200
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    assert rows[0]["status"] == "ready_to_create"


def test_customer_duplicate_exact_match(client, auth_headers, db_session, organization_id):
    _create_customer(db_session, organization_id, display_name="Exact Match Co")
    fair_id = _create_fair(client, auth_headers)
    upload = _upload_wizard(client, auth_headers, fair_id, ["Firma Adı"], [["Exact Match Co"]])
    batch_id = upload.json()["batch_id"]
    _set_mapping(client, auth_headers, batch_id, True, {"company_name": {"type": "column_index", "value": 0}})
    _analyze(client, auth_headers, batch_id)
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    assert rows[0]["match_customer_id"] is not None
    assert rows[0]["participation_exists"] is False


def test_customer_duplicate_fuzzy_match(client, auth_headers, db_session, organization_id):
    _create_customer(db_session, organization_id, display_name="Celik Makina Imalat")
    fair_id = _create_fair(client, auth_headers)
    upload = _upload_wizard(client, auth_headers, fair_id, ["Firma Adı"], [["Celik Makina Iml"]])
    batch_id = upload.json()["batch_id"]
    _set_mapping(client, auth_headers, batch_id, True, {"company_name": {"type": "column_index", "value": 0}})
    _analyze(client, auth_headers, batch_id)
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    assert rows[0]["match_customer_id"] is not None
    assert rows[0]["match_confidence"] >= 85
    assert rows[0]["match_reason"] == "fuzzy_name_candidate"


def test_participation_duplicate_in_selected_fair(client, auth_headers, db_session, organization_id):
    from datetime import UTC, datetime

    customer = _create_customer(db_session, organization_id, display_name="Participated Co")
    fair_id = _create_fair(client, auth_headers, "Dup Part Fair")
    part_repo = SqlAlchemyParticipationRepository(db_session)
    now = datetime.now(tz=UTC)
    part_repo.add(
        CustomerFairParticipation.create(
            organization_id=organization_id,
            customer_id=customer.id,
            fair_id=UUID(fair_id),
            hall="A",
            stand="1",
            participation_status=ParticipationStatus.EXHIBITOR,
            now=now,
        )
    )
    upload = _upload_wizard(client, auth_headers, fair_id, ["Firma Adı"], [["Participated Co"]])
    batch_id = upload.json()["batch_id"]
    _set_mapping(client, auth_headers, batch_id, True, {"company_name": {"type": "column_index", "value": 0}})
    _analyze(client, auth_headers, batch_id)
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    assert rows[0]["participation_exists"] is True
    assert rows[0]["suggested_action"] == "update_participation"


def test_create_customer_and_participation(client, auth_headers):
    fair_id = _create_fair(client, auth_headers, "Create Part Fair")
    upload = _upload_wizard(
        client,
        auth_headers,
        fair_id,
        ["Firma Adı", "Salon", "Stand"],
        [["New Part Co", "B", "12"]],
    )
    batch_id = upload.json()["batch_id"]
    _set_mapping(
        client,
        auth_headers,
        batch_id,
        True,
        {
            "company_name": {"type": "column_index", "value": 0},
            "hall": {"type": "column_index", "value": 1},
            "stand": {"type": "column_index", "value": 2},
        },
    )
    _analyze(client, auth_headers, batch_id)
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    client.patch(
        f"/api/v1/imports/{batch_id}/rows/{rows[0]['id']}/decision",
        headers=auth_headers,
        json={"decision": "create_new"},
    )
    apply_import_decisions(client, auth_headers, batch_id, row_ids=[rows[0]["id"]])
    batch = client.get(f"/api/v1/imports/{batch_id}", headers=auth_headers).json()
    assert batch["created_rows"] == 1
    assert batch["created_participations"] == 1

    participants = client.get(f"/api/v1/fairs/{fair_id}/participants", headers=auth_headers).json()
    assert any(p["company_name"] == "New Part Co" for p in participants["items"])


def test_existing_customer_create_participation(client, auth_headers, db_session, organization_id):
    _create_customer(db_session, organization_id, display_name="Existing Link Co")
    fair_id = _create_fair(client, auth_headers, "Link Fair")
    upload = _upload_wizard(client, auth_headers, fair_id, ["Firma Adı", "Salon"], [["Existing Link Co", "C"]])
    batch_id = upload.json()["batch_id"]
    _set_mapping(
        client,
        auth_headers,
        batch_id,
        True,
        {"company_name": {"type": "column_index", "value": 0}, "hall": {"type": "column_index", "value": 1}},
    )
    _analyze(client, auth_headers, batch_id)
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    assert rows[0]["participation_exists"] is False
    client.patch(
        f"/api/v1/imports/{batch_id}/rows/{rows[0]['id']}/decision",
        headers=auth_headers,
        json={"decision": "update_existing"},
    )
    apply_import_decisions(client, auth_headers, batch_id, row_ids=[rows[0]["id"]])
    batch = client.get(f"/api/v1/imports/{batch_id}", headers=auth_headers).json()
    assert batch["created_participations"] == 1


def test_existing_participation_update(client, auth_headers, db_session, organization_id):
    from datetime import UTC, datetime

    customer = _create_customer(db_session, organization_id, display_name="Update Part Co")
    fair_id = _create_fair(client, auth_headers, "Update Part Fair")
    part_repo = SqlAlchemyParticipationRepository(db_session)
    now = datetime.now(tz=UTC)
    part_repo.add(
        CustomerFairParticipation.create(
            organization_id=organization_id,
            customer_id=customer.id,
            fair_id=UUID(fair_id),
            hall=None,
            stand=None,
            participation_status=ParticipationStatus.EXHIBITOR,
            now=now,
        )
    )
    upload = _upload_wizard(
        client, auth_headers, fair_id, ["Firma Adı", "Salon"], [["Update Part Co", "D"]]
    )
    batch_id = upload.json()["batch_id"]
    _set_mapping(
        client,
        auth_headers,
        batch_id,
        True,
        {"company_name": {"type": "column_index", "value": 0}, "hall": {"type": "column_index", "value": 1}},
    )
    _analyze(client, auth_headers, batch_id)
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    client.patch(
        f"/api/v1/imports/{batch_id}/rows/{rows[0]['id']}/decision",
        headers=auth_headers,
        json={"decision": "update_existing"},
    )
    apply_import_decisions(client, auth_headers, batch_id, row_ids=[rows[0]["id"]])
    batch = client.get(f"/api/v1/imports/{batch_id}", headers=auth_headers).json()
    assert batch["updated_participations"] == 1


def test_empty_incoming_does_not_overwrite_db(client, auth_headers, db_session, organization_id):
    from datetime import UTC, datetime

    repo = SqlAlchemyCustomerRepository(db_session)
    now = datetime.now(tz=UTC)
    customer = repo.add(
        Customer.create(
            organization_id=organization_id,
            display_name="Keep Country Co",
            country="Türkiye",
            source=CustomerSource.MANUAL,
            now=now,
        )
    )
    fair_id = _create_fair(client, auth_headers)
    upload = _upload_wizard(client, auth_headers, fair_id, ["Firma Adı", "Ülke"], [["Keep Country Co", ""]])
    batch_id = upload.json()["batch_id"]
    _set_mapping(
        client,
        auth_headers,
        batch_id,
        True,
        {"company_name": {"type": "column_index", "value": 0}, "country": {"type": "column_index", "value": 1}},
    )
    _analyze(client, auth_headers, batch_id)
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    client.patch(
        f"/api/v1/imports/{batch_id}/rows/{rows[0]['id']}/decision",
        headers=auth_headers,
        json={"decision": "update_existing"},
    )
    apply_import_decisions(client, auth_headers, batch_id, row_ids=[rows[0]["id"]])
    updated = client.get(f"/api/v1/customers/{customer.id}", headers=auth_headers).json()
    assert updated["country"] == "Türkiye"


def test_email_merge_canonical_format(client, auth_headers, db_session, organization_id):
    from datetime import UTC, datetime

    repo = SqlAlchemyCustomerRepository(db_session)
    now = datetime.now(tz=UTC)
    customer = repo.add(
        Customer.create(
            organization_id=organization_id,
            display_name="Email Merge Co",
            email="a@co.com",
            source=CustomerSource.MANUAL,
            now=now,
        )
    )
    fair_id = _create_fair(client, auth_headers)
    upload = _upload_wizard(
        client, auth_headers, fair_id, ["Firma Adı", "E-posta"], [["Email Merge Co", "b@co.com"]]
    )
    batch_id = upload.json()["batch_id"]
    _set_mapping(
        client,
        auth_headers,
        batch_id,
        True,
        {"company_name": {"type": "column_index", "value": 0}, "email": {"type": "column_index", "value": 1}},
    )
    _analyze(client, auth_headers, batch_id)
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    client.patch(
        f"/api/v1/imports/{batch_id}/rows/{rows[0]['id']}/decision",
        headers=auth_headers,
        json={"decision": "update_existing"},
    )
    apply_import_decisions(client, auth_headers, batch_id, row_ids=[rows[0]["id"]])
    updated = client.get(f"/api/v1/customers/{customer.id}", headers=auth_headers).json()
    assert "a@co.com" in updated["email"]
    assert "b@co.com" in updated["email"]


def test_hall_stand_on_participation(client, auth_headers):
    fair_id = _create_fair(client, auth_headers, "Hall Stand Fair")
    upload = _upload_wizard(
        client, auth_headers, fair_id, ["Firma Adı", "Salon", "Stand"], [["Hall Co", "E", "99"]]
    )
    batch_id = upload.json()["batch_id"]
    _set_mapping(
        client,
        auth_headers,
        batch_id,
        True,
        {
            "company_name": {"type": "column_index", "value": 0},
            "hall": {"type": "column_index", "value": 1},
            "stand": {"type": "column_index", "value": 2},
        },
    )
    _analyze(client, auth_headers, batch_id)
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    client.patch(
        f"/api/v1/imports/{batch_id}/rows/{rows[0]['id']}/decision",
        headers=auth_headers,
        json={"decision": "create_new"},
    )
    apply_import_decisions(client, auth_headers, batch_id, row_ids=[rows[0]["id"]])
    participants = client.get(f"/api/v1/fairs/{fair_id}/participants", headers=auth_headers).json()
    part = next(p for p in participants["items"] if p["company_name"] == "Hall Co")
    assert part["hall"] == "E"
    assert part["stand"] == "99"


def test_activity_source_import_created(client, auth_headers, db_session, organization_id):
    fair_id = _create_fair(client, auth_headers, "Activity Fair")
    upload = _upload_wizard(client, auth_headers, fair_id, ["Firma Adı"], [["Activity Co"]])
    batch_id = upload.json()["batch_id"]
    _set_mapping(client, auth_headers, batch_id, True, {"company_name": {"type": "column_index", "value": 0}})
    _analyze(client, auth_headers, batch_id)
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    client.patch(
        f"/api/v1/imports/{batch_id}/rows/{rows[0]['id']}/decision",
        headers=auth_headers,
        json={"decision": "create_new"},
    )
    apply_import_decisions(client, auth_headers, batch_id, row_ids=[rows[0]["id"]])
    customers = client.get("/api/v1/customers?search=Activity Co", headers=auth_headers).json()["items"]
    customer_id = customers[0]["id"]
    activities = client.get(f"/api/v1/customers/{customer_id}/activities", headers=auth_headers).json()["items"]
    assert any(a["source"] == "import" for a in activities)


def test_apply_summary_correct(client, auth_headers):
    fair_id = _create_fair(client, auth_headers, "Summary Fair")
    upload = _upload_wizard(client, auth_headers, fair_id, ["Firma Adı"], [["Sum Co", "Skip Co"]])
    batch_id = upload.json()["batch_id"]
    _set_mapping(client, auth_headers, batch_id, True, {"company_name": {"type": "column_index", "value": 0}})
    _analyze(client, auth_headers, batch_id)
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    client.patch(
        f"/api/v1/imports/{batch_id}/rows/{rows[0]['id']}/decision",
        headers=auth_headers,
        json={"decision": "create_new"},
    )
    row_ids = [rows[0]["id"]]
    if len(rows) > 1:
        client.patch(
            f"/api/v1/imports/{batch_id}/rows/{rows[1]['id']}/decision",
            headers=auth_headers,
            json={"decision": "skip"},
        )
        row_ids.append(rows[1]["id"])
    apply_import_decisions(client, auth_headers, batch_id, row_ids=row_ids)
    batch = client.get(f"/api/v1/imports/{batch_id}", headers=auth_headers).json()
    assert batch["created_rows"] >= 1
    assert batch["status"] in ("applied", "completed")


def test_list_rows_includes_merge_preview(client, auth_headers, db_session, organization_id):
    from datetime import UTC, datetime

    customer = _create_customer(db_session, organization_id, display_name="Preview Co")
    customer.country = "Türkiye"
    from app.modules.customers.infrastructure.repositories.customer_repository import (
        SqlAlchemyCustomerRepository,
    )

    SqlAlchemyCustomerRepository(db_session).update(customer)
    fair_id = _create_fair(client, auth_headers, "Merge Preview Fair")
    upload = _upload_wizard(
        client,
        auth_headers,
        fair_id,
        ["Firma Adı", "E-posta", "Website"],
        [["Preview Co", "new@co.com", "https://new.com"]],
    )
    batch_id = upload.json()["batch_id"]
    _set_mapping(
        client,
        auth_headers,
        batch_id,
        True,
        {
            "company_name": {"type": "column_index", "value": 0},
            "email": {"type": "column_index", "value": 1},
            "website": {"type": "column_index", "value": 2},
        },
    )
    _analyze(client, auth_headers, batch_id)
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    assert rows[0]["merge_preview"] is not None
    assert rows[0]["merge_preview"]["groups"]
    assert rows[0]["merge_preview"]["summary_lines"]
    email_group = rows[0]["merge_preview"]["groups"][0]
    assert any(f["field_key"] == "email" for f in email_group["fields"])


def test_apply_creates_contact_wizard(client, auth_headers):
    fair_id = _create_fair(client, auth_headers, "Contact Wizard Fair")
    upload = _upload_wizard(
        client,
        auth_headers,
        fair_id,
        ["Firma Adı", "Yetkili Adı", "Yetkili Soyadı", "Yetkili E-posta", "Yetkili Telefon"],
        [["Contact Wizard Co", "Mehmet", "Demir", "mehmet@contact.com", "5551234567"]],
    )
    batch_id = upload.json()["batch_id"]
    _set_mapping(
        client,
        auth_headers,
        batch_id,
        True,
        {
            "company_name": {"type": "column_index", "value": 0},
            "contact_first_name": {"type": "column_index", "value": 1},
            "contact_last_name": {"type": "column_index", "value": 2},
            "contact_email": {"type": "column_index", "value": 3},
            "contact_phone": {"type": "column_index", "value": 4},
        },
    )
    _analyze(client, auth_headers, batch_id)
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    assert any(g["entity"] == "contact" for g in rows[0]["merge_preview"]["groups"])
    client.patch(
        f"/api/v1/imports/{batch_id}/rows/{rows[0]['id']}/decision",
        headers=auth_headers,
        json={"decision": "create_new"},
    )
    apply_import_decisions(client, auth_headers, batch_id, row_ids=[rows[0]["id"]])
    batch = client.get(f"/api/v1/imports/{batch_id}", headers=auth_headers).json()
    assert batch["created_rows"] == 1
    customers = client.get("/api/v1/customers?search=Contact+Wizard+Co", headers=auth_headers).json()["items"]
    customer_id = customers[0]["id"]
    contacts = client.get(f"/api/v1/customers/{customer_id}/contacts", headers=auth_headers).json()
    assert pagination_from(contacts)["totalItems"] == 1
    assert contacts["items"][0]["first_name"] == "Mehmet"
    participants = client.get(f"/api/v1/fairs/{fair_id}/participants", headers=auth_headers).json()
    assert any(p["company_name"] == "Contact Wizard Co" for p in participants["items"])
    activities = client.get(f"/api/v1/customers/{customer_id}/activities", headers=auth_headers).json()["items"]
    assert any(a["source"] == "import" for a in activities)


def test_rows_filter_and_search(client, auth_headers):
    fair_id = _create_fair(client, auth_headers, "Filter Fair")
    upload = _upload_wizard(
        client,
        auth_headers,
        fair_id,
        ["Firma Adı"],
        [["Alpha Co"], ["Beta Co"]],
    )
    batch_id = upload.json()["batch_id"]
    _set_mapping(
        client,
        auth_headers,
        batch_id,
        True,
        {"company_name": {"type": "column_index", "value": 0}},
    )
    _analyze(client, auth_headers, batch_id)
    filtered = client.get(
        f"/api/v1/imports/{batch_id}/rows?search=Alpha",
        headers=auth_headers,
    ).json()
    assert pagination_from(filtered)["totalItems"] == 1
    assert filtered["items"][0]["normalized_data_json"]["company_name"] == "Alpha Co"

