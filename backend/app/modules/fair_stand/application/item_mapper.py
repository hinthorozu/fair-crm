from __future__ import annotations

from decimal import Decimal

from app.modules.fair_stand.domain.entities import CatalogCategory, CatalogPreview, ItemAggregate


def _num(value: Decimal | None) -> float | None:
    if value is None:
        return None
    number = float(value)
    return int(number) if number.is_integer() else number


def map_preview(row) -> CatalogPreview:
    return CatalogPreview(
        id=int(row.id),
        display_name=row.display_name,
        markup=row.markup,
        css_code=row.css_code,
        sort_index=row.sort_index,
        is_active=row.is_active,
    )


def map_category(row) -> CatalogCategory:
    return CatalogCategory(
        id=int(row.id),
        catalog_name=row.catalog_name,
        catalog_index=row.catalog_index,
    )


def map_item(row) -> ItemAggregate:
    payload: dict = {
        "itemKey": row.item_key,
        "name": row.name,
        "type": row.item_type,
        "catalogVisible": row.catalog_visible,
        "categoryId": int(row.category_id) if row.category_id is not None else None,
        "catalogItemIndex": row.catalog_item_index,
    }
    if row.unit is not None:
        payload["unit"] = row.unit
    if row.preview_id is not None:
        payload["previewId"] = int(row.preview_id)
    if row.material is not None:
        payload["material"] = row.material
    if row.default_color is not None:
        payload["defaultColor"] = int(row.default_color)
    if row.panel_role is not None:
        payload["panelRole"] = row.panel_role
    if row.nominal_module_width_cm is not None:
        payload["nominalModuleWidthCm"] = _num(row.nominal_module_width_cm)
    if row.connector_type is not None:
        payload["connectorType"] = row.connector_type
    if row.preserve_model_scale is not None:
        payload["preserveModelScale"] = row.preserve_model_scale
    if row.model_rotation_y_deg is not None:
        payload["modelRotationYDeg"] = _num(row.model_rotation_y_deg)
    if row.visual_rotation_y_deg is not None:
        payload["visualRotationYDeg"] = _num(row.visual_rotation_y_deg)
    if row.paintable is not None:
        payload["paintable"] = row.paintable
    if row.shape is not None:
        payload["shape"] = row.shape
    if row.variant is not None:
        payload["variant"] = row.variant
    if row.eye_count is not None:
        payload["eyeCount"] = int(row.eye_count)

    if row.dimensions is not None:
        dimensions = {}
        mapping = {
            "widthCm": row.dimensions.width_cm,
            "depthCm": row.dimensions.depth_cm,
            "heightCm": row.dimensions.height_cm,
            "lengthCm": row.dimensions.length_cm,
            "thicknessCm": row.dimensions.thickness_cm,
            "mountHeightCm": row.dimensions.mount_height_cm,
            "wallGapCm": row.dimensions.wall_gap_cm,
        }
        for key, value in mapping.items():
            number = _num(value)
            if number is not None:
                dimensions[key] = number
        if dimensions:
            payload["dimensions"] = dimensions

    if row.scene_dimensions is not None:
        scene = {}
        mapping = {
            "widthCm": row.scene_dimensions.width_cm,
            "depthCm": row.scene_dimensions.depth_cm,
            "heightCm": row.scene_dimensions.height_cm,
        }
        for key, value in mapping.items():
            number = _num(value)
            if number is not None:
                scene[key] = number
        if scene:
            payload["sceneDimensions"] = scene

    if row.strip_occupancy is not None:
        payload["stripOccupancy"] = {
            "align": row.strip_occupancy.align,
            "stripCount": int(row.strip_occupancy.strip_count),
        }

    model_file = next(
        (asset.relative_path for asset in row.assets if asset.asset_role == "model" and asset.is_active),
        None,
    )
    if model_file:
        payload["modelFile"] = model_file
    default_screen = next(
        (
            asset.relative_path
            for asset in row.assets
            if asset.asset_role == "default_screen" and asset.is_active
        ),
        None,
    )
    if default_screen:
        payload["defaultScreenFile"] = default_screen

    components = sorted(row.components, key=lambda component: component.sort_order)
    inner = row.inner_corner
    if components or row.composition_mode or inner:
        composition: dict = {}
        if row.composition_mode is not None:
            composition["mode"] = row.composition_mode
        if row.composition_module_type is not None:
            composition["moduleType"] = row.composition_module_type
        if components:
            composition["items"] = [
                {"itemKey": component.child_item_key, "quantity": _num(component.quantity)}
                for component in components
            ]
        if inner is not None:
            inner_payload: dict = {"panelItemKey": inner.panel_item_key}
            replacements = sorted(inner.replacements, key=lambda replacement: replacement.sort_order)
            if replacements:
                inner_payload["itemReplacements"] = [
                    {
                        "itemKey": replacement.replaced_item_key,
                        "items": [
                            {"itemKey": member.child_item_key, "quantity": _num(member.quantity)}
                            for member in sorted(replacement.members, key=lambda item: item.sort_order)
                        ],
                    }
                    for replacement in replacements
                ]
            composition["innerCorner"] = inner_payload
        payload["composition"] = composition

    if row.video_wall is not None:
        payload["videoWall"] = {
            "rows": int(row.video_wall.rows),
            "cols": int(row.video_wall.cols),
            "panelItemKey": row.video_wall.panel_item_key,
        }

    if row.body_parts:
        body = {part.body_role: part.child_item_key for part in row.body_parts}
        payload["bodyItems"] = {
            "sideItemKey": body["side"],
            "horizontalItemKey": body["horizontal"],
            "glassShelfItemKey": body["glass_shelf"],
        }

    return ItemAggregate(payload=payload)
