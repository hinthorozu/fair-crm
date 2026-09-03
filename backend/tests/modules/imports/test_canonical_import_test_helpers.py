"""Regression coverage for the canonical import test helper."""

from tests.modules.imports.canonical_import_test_helpers import (
    IMPORTS_BASE,
    create_analyzed_import,
)


def test_create_analyzed_import_uses_production_wizard_lifecycle(client, auth_headers):
    batch = create_analyzed_import(
        client,
        auth_headers,
        ["Firma Adı", "E-posta"],
        [["Canonical Helper Co", "helper@example.com"]],
    )

    payload = batch.json()
    assert payload["status"] == "decision_required"
    assert payload["total_rows"] == 1

    rows = client.get(f"{IMPORTS_BASE}/{payload['id']}/rows", headers=auth_headers)
    assert rows.status_code == 200
    items = rows.json()["items"]
    assert len(items) == 1
    assert items[0]["normalized_data_json"]["company_name"] == "Canonical Helper Co"
    assert items[0]["status"] == "ready_to_create"
