"""Sort whitelist tests for list endpoints (Universal DataTable sorting rule)."""

import pytest

from app.modules.contacts.application.list_contacts_by_customer import ALLOWED_SORT_FIELDS as CONTACT_SORT
from app.modules.customers.application.list_customers import ALLOWED_SORT_FIELDS as CUSTOMER_SORT
from app.modules.data_integration.application.list_import_batches import ALLOWED_SORT_FIELDS as IMPORT_SORT
from app.modules.fairs.application.list_fairs import ALLOWED_SORT_FIELDS as FAIR_SORT
from app.modules.participations.application.list_by_customer import ALLOWED_SORT_FIELDS as PART_CUST_SORT
from app.modules.participations.application.list_by_fair import ALLOWED_SORT_FIELDS as PART_FAIR_SORT
from app.modules.system_admin.application.backup_service import BACKUP_ALLOWED_SORT_FIELDS
from app.core.pagination import resolve_sort_field


@pytest.mark.parametrize(
    ("allowed", "default", "invalid", "valid"),
    [
        (FAIR_SORT, "start_date", "DROP TABLE", "name"),
        (CUSTOMER_SORT, "name", "'; DELETE", "created_at"),
        (CONTACT_SORT, "first_name", "../etc", "full_name"),
        (PART_FAIR_SORT, "company_name", "evil", "email"),
        (PART_CUST_SORT, "fair_start_date", "hack", "hall"),
        (IMPORT_SORT, "created_at", "bad", "file_name"),
        (BACKUP_ALLOWED_SORT_FIELDS, "started_at", "bad", "file_size"),
    ],
)
def test_sort_field_whitelist_fallback(allowed, default, invalid, valid):
    assert resolve_sort_field(invalid, allowed, default) == default
    assert resolve_sort_field(valid, allowed, default) == valid


def test_list_fairs_rejects_invalid_sort(client, auth_headers):
    res = client.get("/api/v1/fairs?sort_by=not_a_column&sort_order=asc", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["sorting"]["field"] == "start_date"


def test_list_fairs_sort_by_sort_order(client, auth_headers):
    res = client.get("/api/v1/fairs?sort_by=organizer&sort_order=desc", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["sorting"]["field"] == "organizer"
    assert res.json()["sorting"]["direction"] == "desc"


def test_list_backups_sort_by_file_name(client, auth_headers):
    res = client.get("/api/v1/admin/backups?sort_by=file_name&sort_order=asc", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["sorting"]["field"] == "file_name"
    assert res.json()["sorting"]["direction"] == "asc"


def test_list_backups_direction_alias(client, auth_headers):
    res = client.get("/api/v1/admin/backups?sort_by=file_name&direction=asc", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["sorting"]["direction"] == "asc"


def test_list_backups_invalid_sort_fallback(client, auth_headers):
    res = client.get("/api/v1/admin/backups?sort_by=evil_field", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["sorting"]["field"] == "started_at"


def test_legacy_sort_direction_aliases_still_work(client, auth_headers):
    res = client.get("/api/v1/fairs?sort=name&direction=asc", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["sorting"]["field"] == "name"
