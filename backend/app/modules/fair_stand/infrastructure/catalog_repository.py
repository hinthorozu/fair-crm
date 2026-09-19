from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.fair_stand.application.item_mapper import (
    CatalogCategory,
    CatalogPreview,
    ItemAggregate,
    map_category,
    map_item,
    map_preview,
)
from app.modules.fair_stand.infrastructure.models import (
    FairStandCatalogPreviewKindModel,
    FairStandCategoryModel,
    FairStandItemInnerCornerModel,
    FairStandItemInnerCornerReplacementModel,
    FairStandItemModel,
)


class SqlAlchemyFairStandCatalogRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _item_query(self):
        return select(FairStandItemModel).options(
            selectinload(FairStandItemModel.dimensions),
            selectinload(FairStandItemModel.scene_dimensions),
            selectinload(FairStandItemModel.strip_occupancy),
            selectinload(FairStandItemModel.assets),
            selectinload(FairStandItemModel.components),
            selectinload(FairStandItemModel.inner_corner)
            .selectinload(FairStandItemInnerCornerModel.replacements)
            .selectinload(FairStandItemInnerCornerReplacementModel.members),
            selectinload(FairStandItemModel.video_wall),
            selectinload(FairStandItemModel.body_parts),
        )

    def list_active_categories(self) -> list[CatalogCategory]:
        rows = self._session.scalars(
            select(FairStandCategoryModel)
            .where(FairStandCategoryModel.is_active.is_(True))
            .order_by(FairStandCategoryModel.catalog_index)
        ).all()
        return [map_category(row) for row in rows]

    def list_items(self, *, active_only: bool = True) -> list[ItemAggregate]:
        stmt = self._item_query()
        if active_only:
            stmt = stmt.where(FairStandItemModel.is_active.is_(True))
        stmt = stmt.order_by(FairStandItemModel.item_key)
        return [map_item(row) for row in self._session.scalars(stmt).all()]

    def get_item(self, item_key: str, *, active_only: bool = True) -> ItemAggregate | None:
        stmt = self._item_query().where(FairStandItemModel.item_key == item_key)
        if active_only:
            stmt = stmt.where(FairStandItemModel.is_active.is_(True))
        row = self._session.scalar(stmt)
        return map_item(row) if row is not None else None

    def list_categories(self, *, active_only: bool = False) -> list[FairStandCategoryModel]:
        stmt = select(FairStandCategoryModel).order_by(FairStandCategoryModel.catalog_index)
        if active_only:
            stmt = stmt.where(FairStandCategoryModel.is_active.is_(True))
        return list(self._session.scalars(stmt).all())

    def get_category(self, category_id: int) -> FairStandCategoryModel | None:
        return self._session.get(FairStandCategoryModel, int(category_id))

    def get_category_by_index(self, catalog_index: int) -> FairStandCategoryModel | None:
        return self._session.scalar(
            select(FairStandCategoryModel).where(FairStandCategoryModel.catalog_index == catalog_index)
        )

    def list_previews(self, *, active_only: bool = False) -> list[FairStandCatalogPreviewKindModel]:
        stmt = select(FairStandCatalogPreviewKindModel).order_by(
            FairStandCatalogPreviewKindModel.sort_index,
            FairStandCatalogPreviewKindModel.id,
        )
        if active_only:
            stmt = stmt.where(FairStandCatalogPreviewKindModel.is_active.is_(True))
        return list(self._session.scalars(stmt).all())

    def list_preview_payloads(self, *, active_only: bool = False) -> list[CatalogPreview]:
        return [map_preview(row) for row in self.list_previews(active_only=active_only)]

    def get_preview(self, preview_id: int) -> FairStandCatalogPreviewKindModel | None:
        return self._session.get(FairStandCatalogPreviewKindModel, int(preview_id))

    def list_item_catalog_rows(self) -> list[FairStandItemModel]:
        return list(
            self._session.scalars(
                select(FairStandItemModel).order_by(FairStandItemModel.item_key)
            ).all()
        )

    def get_item_row(self, item_key: str) -> FairStandItemModel | None:
        return self._session.get(FairStandItemModel, item_key)

    def count_items_for_category(self, category_id: int) -> int:
        rows = self._session.scalars(
            select(FairStandItemModel).where(FairStandItemModel.category_id == int(category_id))
        ).all()
        return len(rows)

    def count_items_for_preview(self, preview_id: int) -> int:
        rows = self._session.scalars(
            select(FairStandItemModel).where(FairStandItemModel.preview_id == int(preview_id))
        ).all()
        return len(rows)
