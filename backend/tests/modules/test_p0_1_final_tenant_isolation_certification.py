"""TI-09 final adversarial tenant-isolation certification gaps."""

from datetime import UTC, datetime
from uuid import UUID

from tests.conftest_helpers import pagination_from

from app.modules.imports.domain.entities import ImportBatch, ImportRow
from app.modules.imports.domain.value_objects import ImportRowStatus, ImportSourceType
from app.modules.imports.infrastructure.repositories.import_repository import (
    SqlAlchemyImportBatchRepository,
    SqlAlchemyImportRowRepository,
)


def _seed_import_batch(
    db_session,
    organization_id: UUID,
    company_name: str,
) -> tuple[str, str]:
    now = datetime.now(tz=UTC)
    batch_repo = SqlAlchemyImportBatchRepository(db_session)
    row_repo = SqlAlchemyImportRowRepository(db_session)
    batch = batch_repo.add(
        ImportBatch.create_from_canonical(
            organization_id=organization_id,
            fair_id=None,
            source_type=ImportSourceType.EXCEL,
            file_name="tenant-certification.xlsx",
            total_rows=1,
            valid_rows=1,
            invalid_rows=0,
            raw_preview_json={"total_rows": 1},
            now=now,
        )
    )
    row = row_repo.add_many(
        [
            ImportRow.create(
                batch_id=batch.id,
                organization_id=organization_id,
                row_number=1,
                raw_data_json={"company_name": company_name},
                normalized_data_json={"company_name": company_name},
                status=ImportRowStatus.READY_TO_CREATE,
                validation_errors_json=None,
                match_customer_id=None,
                match_confidence=None,
                match_reason="no_match",
                now=now,
            )
        ]
    )[0]
    db_session.flush()
    return str(batch.id), str(row.id)


def _create_customer(client, headers, name: str) -> str:
    response = client.post(
        "/api/v1/customers",
        headers=headers,
        json={"display_name": name, "status": "active"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_fair(client, headers, name: str) -> str:
    response = client.post(
        "/api/v1/fairs",
        headers=headers,
        json={"name": name, "status": "planned"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_cost_category(client, headers, name: str) -> str:
    response = client.post(
        "/api/v1/cost-catalog/categories",
        headers=headers,
        json={
            "name": name,
            "slug": name.lower().replace(" ", "-"),
            "description": "P0.1 tenant certification",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_cost_product(client, headers, category_id: str, name: str) -> str:
    response = client.post(
        "/api/v1/cost-catalog/products",
        headers=headers,
        json={
            "category_id": category_id,
            "name": name,
            "slug": name.lower().replace(" ", "-"),
            "unit": "Adet",
            "unit_price": "12.50",
            "currency": "TL",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_mixed_organization_bulk_row_ids_fail_closed(
    client,
    auth_headers,
    db_session,
    organization_id,
    other_organization_id,
):
    owner_batch_id, owner_row_id = _seed_import_batch(
        db_session,
        organization_id,
        "Owner Bulk Row",
    )
    foreign_headers = {**auth_headers, "X-Organization-Id": str(other_organization_id)}
    foreign_batch_id, foreign_row_id = _seed_import_batch(
        db_session,
        other_organization_id,
        "Foreign Bulk Row",
    )

    response = client.patch(
        f"/api/v1/data-integration/imports/{owner_batch_id}/rows/bulk-decision",
        headers=auth_headers,
        json={
            "row_ids": [owner_row_id, foreign_row_id],
            "decision": "create_new",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["updated_count"] == 1
    assert body["skipped_count"] == 1
    assert [item["row_id"] for item in body["errors"]] == [foreign_row_id]

    owner_rows = client.get(
        f"/api/v1/data-integration/imports/{owner_batch_id}/rows",
        headers=auth_headers,
    ).json()["items"]
    foreign_rows = client.get(
        f"/api/v1/data-integration/imports/{foreign_batch_id}/rows",
        headers=foreign_headers,
    ).json()["items"]
    assert owner_rows[0]["decision"] == "create_new"
    assert foreign_rows[0]["decision"] is None


def test_participation_bulk_move_rejects_foreign_target_fair(
    client,
    auth_headers,
    other_organization_id,
):
    source_fair_id = _create_fair(client, auth_headers, "Owner Source Fair")
    owner_customer_id = _create_customer(client, auth_headers, "Owner Move Customer")
    created = client.post(
        "/api/v1/fair-participations",
        headers=auth_headers,
        json={"customer_id": owner_customer_id, "fair_id": source_fair_id},
    )
    assert created.status_code == 201, created.text

    foreign_headers = {**auth_headers, "X-Organization-Id": str(other_organization_id)}
    foreign_target_id = _create_fair(client, foreign_headers, "Foreign Target Fair")

    moved = client.post(
        f"/api/v1/fairs/{source_fair_id}/participants/move-to-fair",
        headers=auth_headers,
        json={"target_fair_id": foreign_target_id},
    )
    assert moved.status_code == 404, moved.text

    owner_source = client.get(
        f"/api/v1/fairs/{source_fair_id}/participants",
        headers=auth_headers,
    )
    foreign_target = client.get(
        f"/api/v1/fairs/{foreign_target_id}/participants",
        headers=foreign_headers,
    )
    assert owner_source.status_code == 200
    assert foreign_target.status_code == 200
    assert pagination_from(owner_source.json())["totalItems"] == 1
    assert pagination_from(foreign_target.json())["totalItems"] == 0


def test_body_and_query_organization_spoof_do_not_override_trusted_context(
    client,
    auth_headers,
    organization_id,
    other_organization_id,
):
    response = client.post(
        f"/api/v1/customers?organization_id={other_organization_id}",
        headers=auth_headers,
        json={
            "display_name": "Spoof-Proof Customer",
            "organization_id": str(other_organization_id),
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["organization_id"] == str(organization_id)

    foreign_headers = {**auth_headers, "X-Organization-Id": str(other_organization_id)}
    foreign_lookup = client.get(
        f"/api/v1/customers/{body['id']}",
        headers=foreign_headers,
    )
    assert foreign_lookup.status_code == 404


def test_missing_organization_context_fails_closed(client, auth_headers):
    headers_without_organization = {
        key: value
        for key, value in auth_headers.items()
        if key.lower() != "x-organization-id"
    }
    response = client.get(
        "/api/v1/customers",
        headers=headers_without_organization,
    )
    assert response.status_code == 422


def test_cost_catalog_direct_foreign_ids_fail_closed(
    client,
    auth_headers,
    other_organization_id,
):
    owner_category_id = _create_cost_category(client, auth_headers, "Owner Certification Category")
    owner_product_id = _create_cost_product(
        client,
        auth_headers,
        owner_category_id,
        "Owner Certification Product",
    )
    foreign_headers = {**auth_headers, "X-Organization-Id": str(other_organization_id)}

    foreign_categories = client.get(
        "/api/v1/cost-catalog/categories",
        headers=foreign_headers,
    )
    foreign_products = client.get(
        "/api/v1/cost-catalog/products",
        headers=foreign_headers,
    )
    assert foreign_categories.status_code == 200, foreign_categories.text
    assert foreign_products.status_code == 200, foreign_products.text
    assert owner_category_id not in {item["id"] for item in foreign_categories.json()["items"]}
    assert owner_product_id not in {item["id"] for item in foreign_products.json()["items"]}

    category_update = client.patch(
        f"/api/v1/cost-catalog/categories/{owner_category_id}",
        headers=foreign_headers,
        json={
            "name": "Foreign Category Overwrite",
            "slug": "foreign-category-overwrite",
            "description": None,
        },
    )
    product_update = client.patch(
        f"/api/v1/cost-catalog/products/{owner_product_id}",
        headers=foreign_headers,
        json={
            "category_id": owner_category_id,
            "name": "Foreign Product Overwrite",
            "slug": "foreign-product-overwrite",
            "unit": "Adet",
            "unit_price": "99.00",
            "currency": "TL",
        },
    )
    assert category_update.status_code == 404, category_update.text
    assert product_update.status_code == 404, product_update.text

    owner_categories = client.get(
        "/api/v1/cost-catalog/categories",
        headers=auth_headers,
    ).json()["items"]
    owner_products = client.get(
        "/api/v1/cost-catalog/products",
        headers=auth_headers,
    ).json()["items"]
    owner_category = next(item for item in owner_categories if item["id"] == owner_category_id)
    owner_product = next(item for item in owner_products if item["id"] == owner_product_id)
    assert owner_category["name"] == "Owner Certification Category"
    assert owner_product["name"] == "Owner Certification Product"


def test_cost_catalog_product_rejects_foreign_category_cross_link(
    client,
    auth_headers,
    other_organization_id,
):
    owner_category_id = _create_cost_category(client, auth_headers, "Owner Product Category")
    owner_product_id = _create_cost_product(
        client,
        auth_headers,
        owner_category_id,
        "Cross Link Guard Product",
    )
    foreign_headers = {**auth_headers, "X-Organization-Id": str(other_organization_id)}
    foreign_category_id = _create_cost_category(
        client,
        foreign_headers,
        "Foreign Product Category",
    )

    response = client.patch(
        f"/api/v1/cost-catalog/products/{owner_product_id}",
        headers=auth_headers,
        json={
            "category_id": foreign_category_id,
            "name": "Cross Link Guard Product",
            "slug": "cross-link-guard-product",
            "unit": "Adet",
            "unit_price": "12.50",
            "currency": "TL",
        },
    )
    assert response.status_code == 404, response.text

    owner_products = client.get(
        "/api/v1/cost-catalog/products",
        headers=auth_headers,
    )
    assert owner_products.status_code == 200, owner_products.text
    product = next(item for item in owner_products.json()["items"] if item["id"] == owner_product_id)
    assert product["category_id"] == owner_category_id
