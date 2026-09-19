from app.modules.fair_stand.api.dependencies import (
    PERMISSION_CATALOG_ARCHIVE,
    PERMISSION_CATALOG_CREATE,
    PERMISSION_CATALOG_READ,
    PERMISSION_CATALOG_UPDATE,
    PERMISSION_PREVIEWS_ARCHIVE,
    PERMISSION_PREVIEWS_CREATE,
    PERMISSION_PREVIEWS_READ,
    PERMISSION_PREVIEWS_UPDATE,
)
from app.modules.fair_stand.infrastructure.seed_catalog import seed_fair_stand_catalog
from app.modules.mail_templates.api.dependencies import get_authorization_adapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from uuid import UUID


class SelectiveAuthorization(AuthorizationPort):
    def __init__(self, *, allowed: set[str] | None = None, denied: set[str] | None = None) -> None:
        self._allowed = allowed
        self._denied = denied or set()

    def check_permission(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        permission_code: str,
        access_token: str,
    ) -> bool:
        _ = (organization_id, user_id, access_token)
        if permission_code in self._denied:
            return False
        if self._allowed is None:
            return True
        return permission_code in self._allowed


def _deny(client, codes: set[str]):
    client.app.dependency_overrides[get_authorization_adapter] = lambda: SelectiveAuthorization(denied=codes)


def _allow(client, codes: set[str]):
    client.app.dependency_overrides[get_authorization_adapter] = lambda: SelectiveAuthorization(allowed=codes)


def test_bootstrap_includes_preview_kind_definitions(client, db_session, auth_headers):
    seed_fair_stand_catalog(db_session)
    db_session.flush()
    response = client.get("/api/v1/fair-stand/catalog/bootstrap", headers=auth_headers)
    assert response.status_code == 200
    kinds = response.json()["previewKinds"]
    assert len(kinds) == 28
    shelf = next(kind for kind in kinds if kind["id"] == 20)
    assert isinstance(shelf["id"], int)
    assert "previewKey" not in shelf
    assert "module-drag-shelf" in shelf["markup"]
    assert "module-drag-shelf" in shelf["cssCode"]
    assert shelf["isActive"] is True


def test_super_admin_catalog_and_preview_crud(client, db_session, auth_headers):
    seed_fair_stand_catalog(db_session)
    db_session.flush()

    created = client.post(
        "/api/v1/fair-stand/admin/categories",
        json={"catalog_name": "QA", "catalog_index": 90},
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    created_id = created.json()["id"]
    assert isinstance(created_id, int)

    updated = client.patch(
        f"/api/v1/fair-stand/admin/categories/{created_id}",
        json={"catalog_name": "QA Grup"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["catalogName"] == "QA Grup"
    assert updated.json()["id"] == created_id

    preview = client.post(
        "/api/v1/fair-stand/admin/previews",
        json={
            "display_name": "QA kutu",
            "markup": '<div class="module-drag-shelf" data-preview-width></div>',
            "css_code": ".module-drag-shelf { height:8px; }",
            "sort_index": 99,
            "is_active": True,
        },
        headers=auth_headers,
    )
    assert preview.status_code == 201, preview.text
    preview_id = preview.json()["id"]
    assert isinstance(preview_id, int)
    assert "previewKey" not in preview.json()

    item = client.patch(
        "/api/v1/fair-stand/admin/items/shelf_100",
        json={"preview_id": preview_id},
        headers=auth_headers,
    )
    assert item.status_code == 200
    assert item.json()["previewId"] == preview_id

    invalid = client.patch(
        "/api/v1/fair-stand/admin/items/shelf_100",
        json={"preview_id": 999999},
        headers=auth_headers,
    )
    assert invalid.status_code == 400

    in_use = client.post(f"/api/v1/fair-stand/admin/previews/{preview_id}/archive", headers=auth_headers)
    assert in_use.status_code == 409

    restore = client.patch(
        "/api/v1/fair-stand/admin/items/shelf_100",
        json={"preview_id": 20},
        headers=auth_headers,
    )
    assert restore.status_code == 200
    assert restore.json()["previewId"] == 20

    archived = client.post(f"/api/v1/fair-stand/admin/previews/{preview_id}/archive", headers=auth_headers)
    assert archived.status_code == 200
    assert archived.json()["isActive"] is False
    assert archived.json()["id"] == preview_id

    inactive_assign = client.patch(
        "/api/v1/fair-stand/admin/items/shelf_100",
        json={"preview_id": preview_id},
        headers=auth_headers,
    )
    assert inactive_assign.status_code == 400

    unused_category = client.post(f"/api/v1/fair-stand/admin/categories/{created_id}/archive", headers=auth_headers)
    assert unused_category.status_code == 200
    assert unused_category.json()["isActive"] is False
    restored = client.post(f"/api/v1/fair-stand/admin/categories/{created_id}/restore", headers=auth_headers)
    assert restored.status_code == 200
    assert restored.json()["isActive"] is True
    unused_category = client.post(f"/api/v1/fair-stand/admin/categories/{created_id}/archive", headers=auth_headers)
    assert unused_category.status_code == 200

    duplicate_index = client.post(
        "/api/v1/fair-stand/admin/categories",
        json={"catalog_name": "Dup Index", "catalog_index": 1},
        headers=auth_headers,
    )
    assert duplicate_index.status_code == 409
    assert duplicate_index.json()["detail"] == "catalog_index already exists"


def test_category_id_is_stable_on_edit(client, db_session, auth_headers):
    seed_fair_stand_catalog(db_session)
    db_session.flush()
    created = client.post(
        "/api/v1/fair-stand/admin/categories",
        json={"catalog_name": "Rename Source", "catalog_index": 91},
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    category_id = created.json()["id"]
    linked = client.patch(
        "/api/v1/fair-stand/admin/items/shelf_100",
        json={"category_id": category_id},
        headers=auth_headers,
    )
    assert linked.status_code == 200
    assert linked.json()["categoryId"] == category_id

    renamed = client.patch(
        f"/api/v1/fair-stand/admin/categories/{category_id}",
        json={"catalog_name": "Rename Target"},
        headers=auth_headers,
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["id"] == category_id
    assert renamed.json()["catalogName"] == "Rename Target"

    items = client.get("/api/v1/fair-stand/admin/items", headers=auth_headers)
    assert items.status_code == 200
    shelf = next(item for item in items.json() if item["itemKey"] == "shelf_100")
    assert shelf["categoryId"] == category_id


def test_preview_id_is_stable_on_edit(client, db_session, auth_headers):
    seed_fair_stand_catalog(db_session)
    db_session.flush()
    created = client.post(
        "/api/v1/fair-stand/admin/previews",
        json={
            "display_name": "Rename Source",
            "markup": '<div class="module-drag-shelf" data-preview-width></div>',
            "css_code": ".module-drag-shelf { height:8px; }",
            "sort_index": 92,
            "is_active": True,
        },
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    preview_id = created.json()["id"]
    linked = client.patch(
        "/api/v1/fair-stand/admin/items/shelf_100",
        json={"preview_id": preview_id},
        headers=auth_headers,
    )
    assert linked.status_code == 200
    assert linked.json()["previewId"] == preview_id

    renamed = client.patch(
        f"/api/v1/fair-stand/admin/previews/{preview_id}",
        json={"display_name": "Rename Target"},
        headers=auth_headers,
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["id"] == preview_id
    assert renamed.json()["displayName"] == "Rename Target"

    items = client.get("/api/v1/fair-stand/admin/items", headers=auth_headers)
    assert items.status_code == 200
    shelf = next(item for item in items.json() if item["itemKey"] == "shelf_100")
    assert shelf["previewId"] == preview_id


def test_organization_admin_and_normal_user_denied_for_admin_mutations(client, db_session, auth_headers):
    seed_fair_stand_catalog(db_session)
    db_session.flush()
    org_codes = {
        PERMISSION_CATALOG_READ,
        PERMISSION_CATALOG_CREATE,
        PERMISSION_CATALOG_UPDATE,
        PERMISSION_CATALOG_ARCHIVE,
        PERMISSION_PREVIEWS_READ,
        PERMISSION_PREVIEWS_CREATE,
        PERMISSION_PREVIEWS_UPDATE,
        PERMISSION_PREVIEWS_ARCHIVE,
    }
    _deny(client, org_codes)
    try:
        assert client.get("/api/v1/fair-stand/admin/categories", headers=auth_headers).status_code == 403
        assert client.get("/api/v1/fair-stand/admin/previews", headers=auth_headers).status_code == 403
        assert client.post(
            "/api/v1/fair-stand/admin/categories",
            json={"catalog_name": "Blocked", "catalog_index": 80},
            headers=auth_headers,
        ).status_code == 403
        assert client.patch(
            "/api/v1/fair-stand/admin/items/shelf_100",
            json={"preview_id": 26},
            headers=auth_headers,
        ).status_code == 403
        assert client.post(
            "/api/v1/fair-stand/admin/previews",
            json={
                "display_name": "Blocked",
                "markup": "<div></div>",
                "css_code": ".x{color:red}",
                "sort_index": 1,
            },
            headers=auth_headers,
        ).status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_authorization_adapter, None)


def test_preview_css_and_markup_are_validated(client, db_session, auth_headers):
    seed_fair_stand_catalog(db_session)
    db_session.flush()
    scripted = client.post(
        "/api/v1/fair-stand/admin/previews",
        json={
            "display_name": "Evil",
            "markup": '<div onclick="alert(1)"></div>',
            "css_code": "body { background:red; }",
            "sort_index": 1,
        },
        headers=auth_headers,
    )
    assert scripted.status_code == 400
