from app.modules.cost_catalog.api.dependencies import (
    CATEGORY_CREATE,
    CATEGORY_DELETE,
    CATEGORY_UPDATE,
    CATEGORY_VIEW,
    PRODUCT_CREATE,
    PRODUCT_DELETE,
    PRODUCT_UPDATE,
    PRODUCT_VIEW,
)


def test_cost_catalog_permission_codes_match_platform_decision() -> None:
    assert {
        CATEGORY_VIEW,
        CATEGORY_CREATE,
        CATEGORY_UPDATE,
        CATEGORY_DELETE,
        PRODUCT_VIEW,
        PRODUCT_CREATE,
        PRODUCT_UPDATE,
        PRODUCT_DELETE,
    } == {
        "fair_crm.cost_catalog.categories.read",
        "fair_crm.cost_catalog.categories.create",
        "fair_crm.cost_catalog.categories.update",
        "fair_crm.cost_catalog.categories.delete",
        "fair_crm.cost_catalog.products.read",
        "fair_crm.cost_catalog.products.create",
        "fair_crm.cost_catalog.products.update",
        "fair_crm.cost_catalog.products.delete",
    }
