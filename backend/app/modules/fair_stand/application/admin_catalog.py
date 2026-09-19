from __future__ import annotations

from datetime import UTC, datetime
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.fair_stand.application.preview_sanitize import (
    PreviewDefinitionError,
    sanitize_css,
    sanitize_markup,
)
from app.modules.fair_stand.infrastructure.catalog_repository import SqlAlchemyFairStandCatalogRepository
from app.modules.fair_stand.infrastructure.models import (
    FairStandCatalogPreviewKindModel,
    FairStandCategoryModel,
    FairStandItemModel,
)


class CatalogAdminError(ValueError):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _category_payload(row: FairStandCategoryModel) -> dict:
    return {
        "id": int(row.id),
        "catalogName": row.catalog_name,
        "catalogIndex": row.catalog_index,
        "isActive": row.is_active,
    }


def _preview_payload(row: FairStandCatalogPreviewKindModel) -> dict:
    return {
        "id": int(row.id),
        "displayName": row.display_name,
        "markup": row.markup,
        "cssCode": row.css_code,
        "sortIndex": row.sort_index,
        "isActive": row.is_active,
    }


def _item_catalog_payload(row: FairStandItemModel) -> dict:
    return {
        "itemKey": row.item_key,
        "name": row.name,
        "catalogVisible": row.catalog_visible,
        "categoryId": int(row.category_id) if row.category_id is not None else None,
        "catalogItemIndex": row.catalog_item_index,
        "previewId": int(row.preview_id) if row.preview_id is not None else None,
        "isActive": row.is_active,
    }


@dataclass
class AdminCatalogService:
    session: Session
    repository: SqlAlchemyFairStandCatalogRepository

    def list_categories(self) -> list[dict]:
        return [_category_payload(row) for row in self.repository.list_categories()]

    def create_category(self, *, catalog_name: str, catalog_index: int, is_active: bool = True) -> dict:
        if not catalog_name.strip():
            raise CatalogAdminError("catalog_name is required")
        if int(catalog_index) < 1:
            raise CatalogAdminError("catalog_index must be greater than 0")
        if self.repository.get_category_by_index(int(catalog_index)) is not None:
            raise CatalogAdminError("catalog_index already exists", status_code=409)
        now = _now()
        row = FairStandCategoryModel(
            catalog_name=catalog_name.strip(),
            catalog_index=int(catalog_index),
            is_active=bool(is_active),
            created_at=now,
            updated_at=now,
        )
        self.session.add(row)
        self._flush()
        self.session.refresh(row)
        return _category_payload(row)

    def update_category(
        self,
        category_id: int,
        *,
        catalog_name: str | None,
        catalog_index: int | None,
        is_active: bool | None = None,
    ) -> dict:
        row = self.repository.get_category(category_id)
        if row is None:
            raise CatalogAdminError("Category not found", status_code=404)
        if catalog_name is not None:
            if not catalog_name.strip():
                raise CatalogAdminError("catalog_name is required")
            row.catalog_name = catalog_name.strip()
        if catalog_index is not None:
            if int(catalog_index) < 1:
                raise CatalogAdminError("catalog_index must be greater than 0")
            next_index = int(catalog_index)
            taken = self.repository.get_category_by_index(next_index)
            if taken is not None and taken.id != row.id:
                raise CatalogAdminError("catalog_index already exists", status_code=409)
            row.catalog_index = next_index
        if is_active is not None:
            row.is_active = bool(is_active)
        row.updated_at = _now()
        self._flush()
        return _category_payload(row)

    def archive_category(self, category_id: int) -> dict:
        row = self.repository.get_category(category_id)
        if row is None:
            raise CatalogAdminError("Category not found", status_code=404)
        if self.repository.count_items_for_category(category_id) > 0:
            raise CatalogAdminError("Category is in use by catalog items", status_code=409)
        row.is_active = False
        row.updated_at = _now()
        self._flush()
        return _category_payload(row)

    def restore_category(self, category_id: int) -> dict:
        row = self.repository.get_category(category_id)
        if row is None:
            raise CatalogAdminError("Category not found", status_code=404)
        row.is_active = True
        row.updated_at = _now()
        self._flush()
        return _category_payload(row)

    def list_items(self) -> list[dict]:
        return [_item_catalog_payload(row) for row in self.repository.list_item_catalog_rows()]

    def update_item_catalog(
        self,
        item_key: str,
        *,
        catalog_visible: bool | None,
        category_id: int | None | object = None,
        category_id_provided: bool = False,
        catalog_item_index: int | None,
        preview_id: int | None | object = None,
        preview_id_provided: bool = False,
    ) -> dict:
        row = self.repository.get_item_row(item_key)
        if row is None:
            raise CatalogAdminError("Item not found", status_code=404)
        if catalog_visible is not None:
            row.catalog_visible = bool(catalog_visible)
        if category_id_provided:
            if category_id is None:
                row.category_id = None
            else:
                category = self.repository.get_category(int(category_id))
                if category is None or not category.is_active:
                    raise CatalogAdminError("categoryId must reference an active category")
                row.category_id = int(category_id)
        if catalog_item_index is not None:
            row.catalog_item_index = int(catalog_item_index) if catalog_item_index else None
        if preview_id_provided:
            if preview_id is None:
                row.preview_id = None
            else:
                preview = self.repository.get_preview(int(preview_id))
                if preview is None:
                    raise CatalogAdminError("previewId must reference an existing preview")
                if not preview.is_active:
                    raise CatalogAdminError("previewId must reference an active preview")
                row.preview_id = int(preview_id)
        if row.catalog_visible:
            if row.category_id is None or row.catalog_item_index is None or row.preview_id is None:
                raise CatalogAdminError(
                    "Visible catalog items require categoryId, catalogItemIndex, and previewId"
                )
        row.updated_at = _now()
        self._flush()
        return _item_catalog_payload(row)

    def list_previews(self) -> list[dict]:
        return [_preview_payload(row) for row in self.repository.list_previews()]

    def create_preview(
        self,
        *,
        display_name: str,
        markup: str,
        css_code: str,
        sort_index: int,
        is_active: bool = True,
    ) -> dict:
        if not display_name.strip():
            raise CatalogAdminError("display_name is required")
        now = _now()
        try:
            row = FairStandCatalogPreviewKindModel(
                display_name=display_name.strip(),
                markup=sanitize_markup(markup),
                css_code=sanitize_css(css_code),
                sort_index=int(sort_index),
                is_active=bool(is_active),
                created_at=now,
                updated_at=now,
            )
        except PreviewDefinitionError as exc:
            raise CatalogAdminError(str(exc)) from exc
        self.session.add(row)
        self._flush()
        self.session.refresh(row)
        return _preview_payload(row)

    def update_preview(
        self,
        preview_id: int,
        *,
        display_name: str | None,
        markup: str | None,
        css_code: str | None,
        sort_index: int | None,
        is_active: bool | None,
    ) -> dict:
        row = self.repository.get_preview(preview_id)
        if row is None:
            raise CatalogAdminError("Preview not found", status_code=404)
        try:
            if display_name is not None:
                if not display_name.strip():
                    raise CatalogAdminError("display_name is required")
                row.display_name = display_name.strip()
            if markup is not None:
                row.markup = sanitize_markup(markup)
            if css_code is not None:
                row.css_code = sanitize_css(css_code)
            if sort_index is not None:
                row.sort_index = int(sort_index)
            if is_active is not None:
                row.is_active = bool(is_active)
        except PreviewDefinitionError as exc:
            raise CatalogAdminError(str(exc)) from exc
        row.updated_at = _now()
        self._flush()
        return _preview_payload(row)

    def archive_preview(self, preview_id: int) -> dict:
        row = self.repository.get_preview(preview_id)
        if row is None:
            raise CatalogAdminError("Preview not found", status_code=404)
        if self.repository.count_items_for_preview(preview_id) > 0:
            raise CatalogAdminError("Preview is in use by catalog items", status_code=409)
        row.is_active = False
        row.updated_at = _now()
        self._flush()
        return _preview_payload(row)

    def restore_preview(self, preview_id: int) -> dict:
        row = self.repository.get_preview(preview_id)
        if row is None:
            raise CatalogAdminError("Preview not found", status_code=404)
        row.is_active = True
        row.updated_at = _now()
        self._flush()
        return _preview_payload(row)

    def _flush(self) -> None:
        try:
            self.session.flush()
        except IntegrityError as exc:
            orig = str(getattr(exc, "orig", exc)).lower()
            if "uq_fair_stand_categories_catalog_index" in orig or "catalog_index" in orig:
                raise CatalogAdminError("catalog_index already exists", status_code=409) from exc
            raise CatalogAdminError("Catalog uniqueness or foreign key constraint failed", status_code=409) from exc
