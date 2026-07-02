"""Tests for import engine."""

from io import BytesIO
from uuid import UUID

import pytest
from openpyxl import Workbook

from tests.conftest_helpers import pagination_from
from tests.modules.imports.import_decision_helpers import apply_import_decisions

from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.value_objects import CustomerSource, CustomerStatus, CustomerType
from app.modules.customers.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)
from app.modules.imports.domain.services.company_name_normalizer import normalize_import_company_name
from app.modules.imports.domain.services.header_mapping import map_header_to_field


def build_xlsx(headers: list[str], rows: list[list[str | None]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def upload_xlsx(client, auth_headers, headers, rows, filename="import.xlsx"):
    content = build_xlsx(headers, rows)
    return client.post(
        "/api/v1/imports/customers/upload",
        headers=auth_headers,
        files={"file": (filename, content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )


def _create_customer(
    db_session,
    organization_id: UUID,
    *,
    display_name: str,
    email: str | None = None,
    phone: str | None = None,
    country: str | None = None,
) -> Customer:
    from datetime import UTC, datetime

    repo = SqlAlchemyCustomerRepository(db_session)
    now = datetime.now(tz=UTC)
    customer = Customer.create(
        organization_id=organization_id,
        display_name=display_name,
        email=email,
        phone=phone,
        country=country,
        source=CustomerSource.MANUAL,
        now=now,
    )
    return repo.add(customer)


def test_upload_xlsx_creates_batch(client, auth_headers):
    response = upload_xlsx(
        client,
        auth_headers,
        ["Firma Adı", "E-posta"],
        [["Acme Ltd", "info@acme.com"]],
    )
    assert response.status_code == 201
    data = response.json()
    assert data["file_name"] == "import.xlsx"
    assert data["source_type"] == "excel"
    assert data["total_rows"] == 1
    assert data["status"] == "previewed"


def test_company_name_only_row_is_valid(client, auth_headers):
    response = upload_xlsx(client, auth_headers, ["Firma Adı"], [["Solo Firma A.Ş."]])
    assert response.status_code == 201
    batch_id = response.json()["id"]
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    assert len(rows) == 1
    assert rows[0]["status"] == "ready_to_create"
    assert rows[0]["validation_errors_json"] is None
    assert rows[0]["normalized_data_json"]["company_name"] == "Solo Firma A.Ş."


def test_missing_optional_fields_not_invalid(client, auth_headers):
    response = upload_xlsx(
        client,
        auth_headers,
        ["Firma Adı", "Telefon", "E-posta", "Adres"],
        [["Sparse Co", None, "", "   "]],
    )
    assert response.status_code == 201
    batch_id = response.json()["id"]
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    assert rows[0]["status"] == "ready_to_create"
    normalized = rows[0]["normalized_data_json"]
    assert normalized["phone"] is None
    assert normalized["email"] is None
    assert normalized["address"] is None


def test_blank_rows_are_skipped(client, auth_headers):
    response = upload_xlsx(
        client,
        auth_headers,
        ["Firma Adı"],
        [["First Co"], [None], [""], ["Second Co"]],
    )
    assert response.status_code == 201
    data = response.json()
    assert data["total_rows"] == 2
    batch_id = data["id"]
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    assert len(rows) == 2
    assert rows[0]["normalized_data_json"]["company_name"] == "First Co"
    assert rows[1]["normalized_data_json"]["company_name"] == "Second Co"


def test_invalid_website_row_is_valid_in_company_name_only_mode(client, auth_headers):
    response = upload_xlsx(
        client,
        auth_headers,
        ["Firma Adı", "Web"],
        [["Web Co", "not a valid url!!!"]],
    )
    assert response.status_code == 201
    batch_id = response.json()["id"]
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    assert rows[0]["status"] == "ready_to_create"
    assert rows[0]["match_reason"] == "no_match"


def test_fuzzy_customer_match(client, auth_headers, db_session, organization_id):
    _create_customer(db_session, organization_id, display_name="Celik Makina Imalat")
    response = upload_xlsx(
        client,
        auth_headers,
        ["Firma Adı"],
        [["Celik Makina Iml"]],
    )
    assert response.status_code == 201
    batch_id = response.json()["id"]
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    assert rows[0]["status"] == "possible_duplicate"
    assert rows[0]["match_confidence"] >= 85
    assert rows[0]["match_reason"] == "fuzzy_name_candidate"


def test_header_alias_mapping(client, auth_headers):
    response = upload_xlsx(
        client,
        auth_headers,
        ["Şirket Adı", "Yetkili Adı", "Yetkili Soyadı"],
        [["Beta A.Ş.", "Ali", "Veli"]],
    )
    assert response.status_code == 201
    batch_id = response.json()["id"]
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    assert rows[0]["normalized_data_json"]["company_name"] == "Beta A.Ş."
    assert rows[0]["normalized_data_json"]["contact_first_name"] == "Ali"


def test_company_name_normalization():
    values = [
        "SİNAN ELEKTRONİK ANONİM ŞİRKETİ",
        "SINAN ELEKTRONIK A.Ş.",
        "Sinan Elektronik San. Tic. Ltd. Şti.",
    ]
    normalized = [normalize_import_company_name(value) for value in values]
    assert all(value == "sinan elektronik" for value in normalized)


def test_map_header_aliases():
    assert map_header_to_field("Firma Adı") == "company_name"
    assert map_header_to_field("EMAIL") == "email"
    assert map_header_to_field("company_name") == "company_name"


def test_multi_email_validation_in_import(client, auth_headers):
    response = upload_xlsx(
        client,
        auth_headers,
        ["Firma Adı", "E-posta"],
        [["Valid Co", "info@a.com; sales@a.com"]],
    )
    assert response.status_code == 201
    batch_id = response.json()["id"]
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    assert rows[0]["status"] == "ready_to_create"


def test_invalid_email_row_is_valid_in_company_name_only_mode(client, auth_headers):
    response = upload_xlsx(
        client,
        auth_headers,
        ["Firma Adı", "E-posta"],
        [["Bad Co", "not-an-email"]],
    )
    assert response.status_code == 201
    batch_id = response.json()["id"]
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    assert rows[0]["status"] == "ready_to_create"
    assert rows[0]["match_reason"] == "no_match"


def test_duplicate_within_same_batch(client, auth_headers):
    response = upload_xlsx(
        client,
        auth_headers,
        ["Firma Adı"],
        [["Sinan Elektronik A.Ş."], ["SINAN ELEKTRONIK LTD"]],
    )
    assert response.status_code == 201
    batch_id = response.json()["id"]
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    assert rows[0]["status"] == "ready_to_create"
    assert rows[1]["status"] == "invalid"
    assert "batch_duplicate_company_name" in rows[1]["validation_errors_json"]


def test_exact_customer_match(client, auth_headers, db_session, organization_id):
    _create_customer(db_session, organization_id, display_name="Sinan Elektronik A.Ş.")
    response = upload_xlsx(
        client,
        auth_headers,
        ["Firma Adı"],
        [["SİNAN ELEKTRONİK ANONİM ŞİRKETİ"]],
    )
    assert response.status_code == 201
    batch_id = response.json()["id"]
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    assert rows[0]["status"] == "possible_duplicate"
    assert rows[0]["match_confidence"] == 100
    assert rows[0]["match_reason"] == "exact_normalized_match"


def test_different_prefix_does_not_fuzzy_match(client, auth_headers, db_session, organization_id):
    _create_customer(db_session, organization_id, display_name="Alpha Endustri")
    response = upload_xlsx(
        client,
        auth_headers,
        ["Firma Adı"],
        [["Alfa Endustri"]],
    )
    assert response.status_code == 201
    batch_id = response.json()["id"]
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    assert rows[0]["status"] == "ready_to_create"
    assert rows[0]["match_reason"] == "no_match"


def test_decision_create_new(client, auth_headers):
    response = upload_xlsx(client, auth_headers, ["Firma Adı"], [["New Co"]])
    batch_id = response.json()["id"]
    row_id = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"][0]["id"]
    decision = client.patch(
        f"/api/v1/imports/{batch_id}/rows/{row_id}/decision",
        headers=auth_headers,
        json={"decision": "create_new"},
    )
    assert decision.status_code == 200
    assert decision.json()["decision"] == "create_new"
    applied = apply_import_decisions(client, auth_headers, batch_id, row_ids=[row_id])
    assert applied.status_code == 200
    assert applied.json()["processed_count"] == 1
    batch = client.get(f"/api/v1/imports/{batch_id}", headers=auth_headers).json()
    assert batch["created_rows"] == 1


def test_decision_update_existing(client, auth_headers, db_session, organization_id):
    customer = _create_customer(db_session, organization_id, display_name="Existing Co")
    response = upload_xlsx(client, auth_headers, ["Firma Adı"], [["Existing Company Ltd"]])
    batch_id = response.json()["id"]
    row_id = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"][0]["id"]
    decision = client.patch(
        f"/api/v1/imports/{batch_id}/rows/{row_id}/decision",
        headers=auth_headers,
        json={"decision": "update_existing", "match_customer_id": str(customer.id)},
    )
    assert decision.status_code == 200
    assert decision.json()["decision"] == "update_existing"
    applied = apply_import_decisions(client, auth_headers, batch_id, row_ids=[row_id])
    assert applied.status_code == 200
    assert applied.json()["processed_count"] == 1
    batch = client.get(f"/api/v1/imports/{batch_id}", headers=auth_headers).json()
    assert batch["updated_rows"] == 1


def test_decision_skip(client, auth_headers):
    response = upload_xlsx(client, auth_headers, ["Firma Adı"], [["Skip Co"]])
    batch_id = response.json()["id"]
    row_id = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"][0]["id"]
    decision = client.patch(
        f"/api/v1/imports/{batch_id}/rows/{row_id}/decision",
        headers=auth_headers,
        json={"decision": "skip"},
    )
    assert decision.status_code == 200
    assert decision.json()["decision"] == "skip"
    applied = apply_import_decisions(client, auth_headers, batch_id, row_ids=[row_id])
    assert applied.status_code == 200
    assert applied.json()["processed_count"] == 1
    batch = client.get(f"/api/v1/imports/{batch_id}", headers=auth_headers).json()
    assert batch["skipped_rows"] == 1


def test_apply_creates_customer(client, auth_headers):
    response = upload_xlsx(
        client,
        auth_headers,
        ["Firma Adı", "E-posta", "Yetkili Adı", "Yetkili Soyadı"],
        [["Created Co", "new@created.com", "Ayşe", "Yılmaz"]],
    )
    batch_id = response.json()["id"]
    row_id = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"][0]["id"]
    client.patch(
        f"/api/v1/imports/{batch_id}/rows/{row_id}/decision",
        headers=auth_headers,
        json={"decision": "create_new"},
    )
    apply_import_decisions(client, auth_headers, batch_id, row_ids=[row_id])
    batch = client.get(f"/api/v1/imports/{batch_id}", headers=auth_headers).json()
    assert batch["created_rows"] == 1

    customers = client.get("/api/v1/customers?search=Created", headers=auth_headers)
    assert customers.status_code == 200
    assert pagination_from(customers.json())["totalItems"] >= 1


def test_apply_updates_existing_empty_fields_only(client, auth_headers, db_session, organization_id):
    customer = _create_customer(
        db_session,
        organization_id,
        display_name="Merge Co",
        email=None,
        country=None,
    )
    response = upload_xlsx(
        client,
        auth_headers,
        ["Firma Adı", "E-posta", "Ülke"],
        [["Merge Co Ltd", "merge@co.com", "Türkiye"]],
    )
    batch_id = response.json()["id"]
    row_id = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"][0]["id"]
    client.patch(
        f"/api/v1/imports/{batch_id}/rows/{row_id}/decision",
        headers=auth_headers,
        json={"decision": "update_existing", "match_customer_id": str(customer.id)},
    )
    apply_import_decisions(client, auth_headers, batch_id, row_ids=[row_id])
    batch = client.get(f"/api/v1/imports/{batch_id}", headers=auth_headers).json()
    assert batch["updated_rows"] == 1

    detail = client.get(f"/api/v1/customers/{customer.id}", headers=auth_headers).json()
    assert detail["email"] == "merge@co.com"
    assert detail["country"] == "Türkiye"


def test_apply_does_not_overwrite_existing_filled_fields(client, auth_headers, db_session, organization_id):
    customer = _create_customer(
        db_session,
        organization_id,
        display_name="Keep Co",
        email="keep@co.com",
        country="Germany",
        phone="905551234567",
    )
    response = upload_xlsx(
        client,
        auth_headers,
        ["Firma Adı", "Ülke", "Telefon"],
        [["Keep Co", "Türkiye", "905559999999"]],
    )
    batch_id = response.json()["id"]
    row_id = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"][0]["id"]
    client.patch(
        f"/api/v1/imports/{batch_id}/rows/{row_id}/decision",
        headers=auth_headers,
        json={"decision": "update_existing", "match_customer_id": str(customer.id)},
    )
    apply_import_decisions(client, auth_headers, batch_id, row_ids=[row_id])
    detail = client.get(f"/api/v1/customers/{customer.id}", headers=auth_headers).json()
    assert detail["country"] == "Germany"
    assert detail["phone"] == "905551234567"


def test_apply_merges_multi_email(client, auth_headers, db_session, organization_id):
    customer = _create_customer(
        db_session,
        organization_id,
        display_name="Email Merge Co",
        email="a@co.com",
    )
    response = upload_xlsx(
        client,
        auth_headers,
        ["Firma Adı", "E-posta"],
        [["Email Merge Co", "b@co.com;a@co.com"]],
    )
    batch_id = response.json()["id"]
    row_id = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"][0]["id"]
    client.patch(
        f"/api/v1/imports/{batch_id}/rows/{row_id}/decision",
        headers=auth_headers,
        json={"decision": "update_existing", "match_customer_id": str(customer.id)},
    )
    apply_import_decisions(client, auth_headers, batch_id, row_ids=[row_id])
    detail = client.get(f"/api/v1/customers/{customer.id}", headers=auth_headers).json()
    assert detail["email"] == "a@co.com;b@co.com"


def test_apply_creates_contact_when_contact_fields_exist(client, auth_headers):
    response = upload_xlsx(
        client,
        auth_headers,
        ["Firma Adı", "Yetkili Adı", "Yetkili Soyadı", "Yetkili E-posta"],
        [["Contact Co", "Mehmet", "Demir", "mehmet@contact.com"]],
    )
    batch_id = response.json()["id"]
    row_id = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"][0]["id"]
    client.patch(
        f"/api/v1/imports/{batch_id}/rows/{row_id}/decision",
        headers=auth_headers,
        json={"decision": "create_new"},
    )
    apply_import_decisions(client, auth_headers, batch_id, row_ids=[row_id])

    customers = client.get("/api/v1/customers?search=Contact", headers=auth_headers).json()
    customer_id = customers["items"][0]["id"]
    contacts = client.get(f"/api/v1/customers/{customer_id}/contacts", headers=auth_headers).json()
    assert pagination_from(contacts)["totalItems"] == 1
    assert contacts["items"][0]["first_name"] == "Mehmet"


def test_invalid_rows_are_not_applied(client, auth_headers):
    response = upload_xlsx(
        client,
        auth_headers,
        ["Firma Adı", "E-posta"],
        [["", "bad"], ["Valid Co", "ok@valid.com"]],
    )
    batch_id = response.json()["id"]
    rows = client.get(f"/api/v1/imports/{batch_id}/rows", headers=auth_headers).json()["items"]
    valid_row = next(row for row in rows if row["status"] == "ready_to_create")
    client.patch(
        f"/api/v1/imports/{batch_id}/rows/{valid_row['id']}/decision",
        headers=auth_headers,
        json={"decision": "create_new"},
    )
    apply_import_decisions(client, auth_headers, batch_id, row_ids=[valid_row["id"]])
    batch = client.get(f"/api/v1/imports/{batch_id}", headers=auth_headers).json()
    assert batch["created_rows"] == 1
    assert batch["invalid_rows"] >= 1
