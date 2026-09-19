from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.integrations.kyrox_core.auth import AuthContext
from app.modules.fair_stand.api.dependencies import (
    PERMISSION_CATALOG_ARCHIVE,
    PERMISSION_CATALOG_CREATE,
    PERMISSION_CATALOG_READ,
    PERMISSION_CATALOG_UPDATE,
    PERMISSION_PREVIEWS_ARCHIVE,
    PERMISSION_PREVIEWS_CREATE,
    PERMISSION_PREVIEWS_READ,
    PERMISSION_PREVIEWS_UPDATE,
    get_admin_catalog_service,
    get_catalog_bootstrap_use_case,
    get_item_use_case,
    require_any_permission,
    require_fair_stand_catalog_access,
    require_permission,
)
from app.modules.fair_stand.application.admin_catalog import AdminCatalogService, CatalogAdminError
from app.modules.fair_stand.application.get_catalog_bootstrap import GetCatalogBootstrapUseCase
from app.modules.fair_stand.application.get_item import GetItemUseCase

router = APIRouter(prefix="/fair-stand", tags=["fair-stand"])


class CategoryCreateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    catalog_name: str = Field(min_length=1, max_length=128)
    catalog_index: int = Field(ge=1)
    is_active: bool = True


class CategoryUpdateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    catalog_name: str | None = Field(default=None, min_length=1, max_length=128)
    catalog_index: int | None = Field(default=None, ge=1)
    is_active: bool | None = None


class ItemCatalogUpdateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    catalog_visible: bool | None = None
    category_id: int | None = None
    catalog_item_index: int | None = None
    preview_id: int | None = None


class PreviewCreateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str = Field(min_length=1, max_length=128)
    markup: str
    css_code: str
    sort_index: int = 0
    is_active: bool = True


class PreviewUpdateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str | None = Field(default=None, min_length=1, max_length=128)
    markup: str | None = None
    css_code: str | None = None
    sort_index: int | None = None
    is_active: bool | None = None


def _preview_kind_payload(preview) -> dict[str, Any]:
    return {
        "id": preview.id,
        "displayName": preview.display_name,
        "markup": preview.markup,
        "cssCode": preview.css_code,
        "sortIndex": preview.sort_index,
        "isActive": preview.is_active,
    }


def _raise_admin(exc: CatalogAdminError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/catalog/bootstrap")
def get_catalog_bootstrap(
    auth: Annotated[AuthContext, Depends(require_fair_stand_catalog_access)],
    use_case: Annotated[GetCatalogBootstrapUseCase, Depends(get_catalog_bootstrap_use_case)],
) -> dict[str, Any]:
    _ = auth
    snapshot = use_case.execute()
    return {
        "revision": snapshot.revision,
        "categories": [
            {
                "id": category.id,
                "catalogName": category.catalog_name,
                "catalogIndex": category.catalog_index,
            }
            for category in snapshot.categories
        ],
        "items": [item.payload for item in snapshot.items],
        "previewKinds": [_preview_kind_payload(preview) for preview in snapshot.preview_kinds],
    }


@router.get("/items/{item_key}")
def get_item(
    item_key: str,
    auth: Annotated[AuthContext, Depends(require_fair_stand_catalog_access)],
    use_case: Annotated[GetItemUseCase, Depends(get_item_use_case)],
) -> dict[str, Any]:
    _ = auth
    item = use_case.execute(item_key)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item.payload


@router.get("/admin/categories")
def admin_list_categories(
    auth: Annotated[AuthContext, Depends(require_permission(PERMISSION_CATALOG_READ))],
    service: Annotated[AdminCatalogService, Depends(get_admin_catalog_service)],
) -> list[dict[str, Any]]:
    _ = auth
    return service.list_categories()


@router.post("/admin/categories", status_code=status.HTTP_201_CREATED)
def admin_create_category(
    body: CategoryCreateBody,
    auth: Annotated[AuthContext, Depends(require_permission(PERMISSION_CATALOG_CREATE))],
    service: Annotated[AdminCatalogService, Depends(get_admin_catalog_service)],
) -> dict[str, Any]:
    _ = auth
    try:
        return service.create_category(
            catalog_name=body.catalog_name,
            catalog_index=body.catalog_index,
            is_active=body.is_active,
        )
    except CatalogAdminError as exc:
        _raise_admin(exc)
        raise


@router.patch("/admin/categories/{category_id}")
def admin_update_category(
    category_id: int,
    body: CategoryUpdateBody,
    auth: Annotated[AuthContext, Depends(require_permission(PERMISSION_CATALOG_UPDATE))],
    service: Annotated[AdminCatalogService, Depends(get_admin_catalog_service)],
) -> dict[str, Any]:
    _ = auth
    try:
        return service.update_category(
            category_id,
            catalog_name=body.catalog_name,
            catalog_index=body.catalog_index,
            is_active=body.is_active,
        )
    except CatalogAdminError as exc:
        _raise_admin(exc)
        raise


@router.post("/admin/categories/{category_id}/archive")
def admin_archive_category(
    category_id: int,
    auth: Annotated[AuthContext, Depends(require_permission(PERMISSION_CATALOG_ARCHIVE))],
    service: Annotated[AdminCatalogService, Depends(get_admin_catalog_service)],
) -> dict[str, Any]:
    _ = auth
    try:
        return service.archive_category(category_id)
    except CatalogAdminError as exc:
        _raise_admin(exc)
        raise


@router.post("/admin/categories/{category_id}/restore")
def admin_restore_category(
    category_id: int,
    auth: Annotated[AuthContext, Depends(require_permission(PERMISSION_CATALOG_ARCHIVE))],
    service: Annotated[AdminCatalogService, Depends(get_admin_catalog_service)],
) -> dict[str, Any]:
    _ = auth
    try:
        return service.restore_category(category_id)
    except CatalogAdminError as exc:
        _raise_admin(exc)
        raise


@router.get("/admin/items")
def admin_list_items(
    auth: Annotated[
        AuthContext,
        Depends(require_any_permission(PERMISSION_CATALOG_READ, PERMISSION_CATALOG_UPDATE)),
    ],
    service: Annotated[AdminCatalogService, Depends(get_admin_catalog_service)],
) -> list[dict[str, Any]]:
    _ = auth
    return service.list_items()


@router.patch("/admin/items/{item_key}")
def admin_update_item_catalog(
    item_key: str,
    body: ItemCatalogUpdateBody,
    auth: Annotated[AuthContext, Depends(require_permission(PERMISSION_CATALOG_UPDATE))],
    service: Annotated[AdminCatalogService, Depends(get_admin_catalog_service)],
) -> dict[str, Any]:
    _ = auth
    try:
        return service.update_item_catalog(
            item_key,
            catalog_visible=body.catalog_visible,
            category_id=body.category_id,
            category_id_provided="category_id" in body.model_fields_set,
            catalog_item_index=body.catalog_item_index,
            preview_id=body.preview_id,
            preview_id_provided="preview_id" in body.model_fields_set,
        )
    except CatalogAdminError as exc:
        _raise_admin(exc)
        raise


@router.get("/admin/previews")
def admin_list_previews(
    auth: Annotated[AuthContext, Depends(require_permission(PERMISSION_PREVIEWS_READ))],
    service: Annotated[AdminCatalogService, Depends(get_admin_catalog_service)],
) -> list[dict[str, Any]]:
    _ = auth
    return service.list_previews()


@router.post("/admin/previews", status_code=status.HTTP_201_CREATED)
def admin_create_preview(
    body: PreviewCreateBody,
    auth: Annotated[AuthContext, Depends(require_permission(PERMISSION_PREVIEWS_CREATE))],
    service: Annotated[AdminCatalogService, Depends(get_admin_catalog_service)],
) -> dict[str, Any]:
    _ = auth
    try:
        return service.create_preview(
            display_name=body.display_name,
            markup=body.markup,
            css_code=body.css_code,
            sort_index=body.sort_index,
            is_active=body.is_active,
        )
    except CatalogAdminError as exc:
        _raise_admin(exc)
        raise


@router.patch("/admin/previews/{preview_id}")
def admin_update_preview(
    preview_id: int,
    body: PreviewUpdateBody,
    auth: Annotated[AuthContext, Depends(require_permission(PERMISSION_PREVIEWS_UPDATE))],
    service: Annotated[AdminCatalogService, Depends(get_admin_catalog_service)],
) -> dict[str, Any]:
    _ = auth
    try:
        return service.update_preview(
            preview_id,
            display_name=body.display_name,
            markup=body.markup,
            css_code=body.css_code,
            sort_index=body.sort_index,
            is_active=body.is_active,
        )
    except CatalogAdminError as exc:
        _raise_admin(exc)
        raise


@router.post("/admin/previews/{preview_id}/archive")
def admin_archive_preview(
    preview_id: int,
    auth: Annotated[AuthContext, Depends(require_permission(PERMISSION_PREVIEWS_ARCHIVE))],
    service: Annotated[AdminCatalogService, Depends(get_admin_catalog_service)],
) -> dict[str, Any]:
    _ = auth
    try:
        return service.archive_preview(preview_id)
    except CatalogAdminError as exc:
        _raise_admin(exc)
        raise


@router.post("/admin/previews/{preview_id}/restore")
def admin_restore_preview(
    preview_id: int,
    auth: Annotated[AuthContext, Depends(require_permission(PERMISSION_PREVIEWS_ARCHIVE))],
    service: Annotated[AdminCatalogService, Depends(get_admin_catalog_service)],
) -> dict[str, Any]:
    _ = auth
    try:
        return service.restore_preview(preview_id)
    except CatalogAdminError as exc:
        _raise_admin(exc)
        raise
