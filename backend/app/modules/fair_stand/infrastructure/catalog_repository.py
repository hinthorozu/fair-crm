from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.fair_stand.application.item_mapper import CatalogCategory, ItemAggregate, map_category, map_item
from app.modules.fair_stand.infrastructure.models import (
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
