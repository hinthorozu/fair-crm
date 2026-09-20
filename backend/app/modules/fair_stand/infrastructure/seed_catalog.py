from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid5, UUID, NAMESPACE_URL

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.fair_stand.application.cycle_validation import assert_acyclic_components
from app.modules.fair_stand.infrastructure.catalog_seed_data import CATALOG_SEED
from app.modules.fair_stand.infrastructure.preview_kind_definitions import all_preview_kind_rows
from app.modules.fair_stand.infrastructure.models import (
    FairStandCatalogPreviewKindModel,
    FairStandCategoryModel,
    FairStandItemAssetModel,
    FairStandItemBodyPartModel,
    FairStandItemComponentModel,
    FairStandItemDimensionsModel,
    FairStandItemModel,
    FairStandItemSceneDimensionsModel,
    FairStandItemStripOccupancyModel,
    FairStandItemVideoWallModel,
)


def _dec(value: object) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _stable_uuid(*parts: str) -> UUID:
    return uuid5(NAMESPACE_URL, "fair-stand:" + ":".join(parts))


def _clear_catalog(session: Session) -> None:
    session.execute(delete(FairStandItemBodyPartModel))
    session.execute(delete(FairStandItemVideoWallModel))
    session.execute(delete(FairStandItemComponentModel))
    session.execute(delete(FairStandItemAssetModel))
    session.execute(delete(FairStandItemStripOccupancyModel))
    session.execute(delete(FairStandItemSceneDimensionsModel))
    session.execute(delete(FairStandItemDimensionsModel))
    session.execute(delete(FairStandItemModel))
    session.execute(delete(FairStandCategoryModel))
    session.execute(delete(FairStandCatalogPreviewKindModel))


def seed_fair_stand_catalog(session: Session) -> None:
    _clear_catalog(session)
    now = datetime.now(tz=UTC)
    edges: list[tuple[str, str]] = []

    for definition in all_preview_kind_rows():
        session.add(
            FairStandCatalogPreviewKindModel(
                display_name=str(definition["display_name"]),
                markup=str(definition["markup"]),
                css_code=str(definition["css_code"]),
                sort_index=int(definition["sort_index"]),
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )

    for category in CATALOG_SEED["categories"]:
        session.add(
            FairStandCategoryModel(
                catalog_name=category["catalog_name"],
                catalog_index=category["catalog_index"],
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )

    session.flush()
    category_id_by_index = {
        row.catalog_index: row.id
        for row in session.scalars(select(FairStandCategoryModel)).all()
    }
    preview_id_by_sort = {
        row.sort_index: row.id
        for row in session.scalars(select(FairStandCatalogPreviewKindModel)).all()
    }

    for row in CATALOG_SEED["items"]:
        category_index = row.get("category_index")
        preview_sort = row.get("preview_id")
        session.add(
            FairStandItemModel(
                item_key=row["item_key"],
                name=row["name"],
                item_type=row["item_type"],
                unit=row["unit"],
                catalog_visible=row["catalog_visible"],
                category_id=category_id_by_index[category_index] if category_index is not None else None,
                catalog_item_index=row["catalog_item_index"],
                preview_id=preview_id_by_sort[preview_sort] if preview_sort is not None else None,
                material=row["material"],
                default_color=row["default_color"],
                panel_role=row["panel_role"],
                connector_type=row["connector_type"],
                preserve_model_scale=row["preserve_model_scale"],
                model_rotation_y_deg=_dec(row["model_rotation_y_deg"]),
                visual_rotation_y_deg=_dec(row["visual_rotation_y_deg"]),
                composition_mode=row["composition_mode"],
                composition_module_type=row["composition_module_type"],
                paintable=row["paintable"],
                shape=row["shape"],
                variant=row["variant"],
                eye_count=row["eye_count"],
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )

    session.flush()

    for row in CATALOG_SEED["items"]:
        item_key = row["item_key"]
        dims = row.get("dimensions")
        if dims:
            session.add(
                FairStandItemDimensionsModel(
                    item_key=item_key,
                    width_cm=_dec(dims["width_cm"]),
                    depth_cm=_dec(dims["depth_cm"]),
                    height_cm=_dec(dims["height_cm"]),
                    length_cm=_dec(dims["length_cm"]),
                    thickness_cm=_dec(dims["thickness_cm"]),
                    mount_height_cm=_dec(dims["mount_height_cm"]),
                    wall_gap_cm=_dec(dims["wall_gap_cm"]),
                )
            )
        scene = row.get("scene_dimensions")
        if scene:
            session.add(
                FairStandItemSceneDimensionsModel(
                    item_key=item_key,
                    width_cm=_dec(scene["width_cm"]),
                    depth_cm=_dec(scene["depth_cm"]),
                    height_cm=_dec(scene["height_cm"]),
                )
            )
        occupancy = row.get("strip_occupancy")
        if occupancy:
            session.add(
                FairStandItemStripOccupancyModel(
                    item_key=item_key,
                    align=occupancy["align"],
                    strip_count=occupancy["strip_count"],
                )
            )
        for asset in row.get("assets") or []:
            session.add(
                FairStandItemAssetModel(
                    id=_stable_uuid("asset", item_key, asset["asset_role"]),
                    item_key=item_key,
                    asset_role=asset["asset_role"],
                    relative_path=asset["relative_path"],
                    is_active=True,
                )
            )
        for component in row.get("components") or []:
            edges.append((item_key, component["child_item_key"]))
            session.add(
                FairStandItemComponentModel(
                    id=_stable_uuid("component", item_key, str(component["sort_order"])),
                    parent_item_key=item_key,
                    child_item_key=component["child_item_key"],
                    quantity=_dec(component["quantity"]),
                    sort_order=component["sort_order"],
                )
            )
        video_wall = row.get("video_wall")
        if video_wall:
            session.add(
                FairStandItemVideoWallModel(
                    parent_item_key=item_key,
                    rows=video_wall["rows"],
                    cols=video_wall["cols"],
                    panel_item_key=video_wall["panel_item_key"],
                )
            )
        for part in row.get("body_parts") or []:
            session.add(
                FairStandItemBodyPartModel(
                    parent_item_key=item_key,
                    body_role=part["body_role"],
                    child_item_key=part["child_item_key"],
                )
            )

    assert_acyclic_components(edges)
    session.flush()
