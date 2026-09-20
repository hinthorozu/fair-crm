from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from app.modules.fair_stand.application.cycle_validation import CyclicItemCompositionError, assert_acyclic_components
from app.modules.fair_stand.infrastructure.models import (
    FairStandCatalogPreviewKindModel,
    FairStandCategoryModel,
    FairStandItemComponentModel,
    FairStandItemModel,
)
from app.modules.fair_stand.infrastructure.seed_catalog import seed_fair_stand_catalog


def _now():
    return datetime.now(tz=UTC)


def _item(**overrides):
    now = _now()
    values = {
        "item_key": "tmp_item",
        "name": "Tmp",
        "item_type": "shelf",
        "catalog_visible": False,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    values.update(overrides)
    return FairStandItemModel(**values)


def test_all_fair_stand_foreign_keys_are_cascade_cascade(test_engine):
    inspector = inspect(test_engine)
    tables = [
        "fair_stand_items",
        "fair_stand_item_dimensions",
        "fair_stand_item_scene_dimensions",
        "fair_stand_item_strip_occupancy",
        "fair_stand_item_assets",
        "fair_stand_item_components",
        "fair_stand_item_video_walls",
        "fair_stand_item_body_parts",
    ]
    for table in tables:
        fks = inspector.get_foreign_keys(table)
        assert fks, table
        for fk in fks:
            options = fk.get("options") or {}
            ondelete = (options.get("ondelete") or fk.get("ondelete") or "").upper()
            onupdate = (options.get("onupdate") or fk.get("onupdate") or "").upper()
            if test_engine.dialect.name == "sqlite":
                assert ondelete in {"CASCADE", ""}, (table, fk)
            else:
                assert ondelete == "CASCADE", (table, fk)
                assert onupdate == "CASCADE", (table, fk)

    category_columns = {column["name"] for column in inspector.get_columns("fair_stand_categories")}
    item_columns = {column["name"] for column in inspector.get_columns("fair_stand_items")}
    assert "id" in category_columns
    assert "catalog_key" not in category_columns
    assert "catalog_key" not in item_columns
    assert "category_id" in item_columns
    assert inspector.get_pk_constraint("fair_stand_categories")["constrained_columns"] == ["id"]
    category_fk = next(
        fk for fk in inspector.get_foreign_keys("fair_stand_items") if fk["referred_table"] == "fair_stand_categories"
    )
    assert category_fk["constrained_columns"] == ["category_id"]
    assert category_fk["referred_columns"] == ["id"]
    preview_columns = {column["name"] for column in inspector.get_columns("fair_stand_catalog_preview_kinds")}
    assert "id" in preview_columns
    assert "preview_key" not in preview_columns
    assert "catalog_preview_key" not in item_columns
    assert "preview_id" in item_columns
    assert inspector.get_pk_constraint("fair_stand_catalog_preview_kinds")["constrained_columns"] == ["id"]
    preview_fk = next(
        fk for fk in inspector.get_foreign_keys("fair_stand_items") if fk["referred_table"] == "fair_stand_catalog_preview_kinds"
    )
    assert preview_fk["constrained_columns"] == ["preview_id"]
    assert preview_fk["referred_columns"] == ["id"]


def test_duplicate_item_key_rejected(db_session):
    db_session.add(_item(item_key="dup_key"))
    db_session.flush()
    db_session.add(_item(item_key="dup_key", name="Other"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_invalid_category_fk_rejected(db_session):
    db_session.add(_item(item_key="bad_cat", category_id=99999))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_invalid_preview_fk_rejected(db_session):
    db_session.add(
        FairStandCatalogPreviewKindModel(
            display_name="Raf",
            markup='<div class="module-drag-shelf" data-preview-width></div>',
            css_code=".module-drag-shelf { height:8px; }",
            sort_index=1,
            is_active=True,
            created_at=_now(),
            updated_at=_now(),
        ),
    )
    db_session.add(
        FairStandCategoryModel(
            catalog_name="Extra",
            catalog_index=1,
            is_active=True,
            created_at=_now(),
            updated_at=_now(),
        )
    )
    db_session.flush()
    extra_id = db_session.scalars(select(FairStandCategoryModel)).one().id
    db_session.add(
        _item(
            item_key="bad_preview",
            catalog_visible=True,
            category_id=extra_id,
            catalog_item_index=1,
            preview_id=99999,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_self_component_rejected(db_session):
    db_session.add(_item(item_key="self_parent"))
    db_session.flush()
    db_session.add(
        FairStandItemComponentModel(
            parent_item_key="self_parent",
            child_item_key="self_parent",
            quantity=Decimal("1"),
            sort_order=0,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_quantity_must_be_positive(db_session):
    db_session.add(_item(item_key="parent_a"))
    db_session.add(_item(item_key="child_b"))
    db_session.flush()
    db_session.add(
        FairStandItemComponentModel(
            parent_item_key="parent_a",
            child_item_key="child_b",
            quantity=Decimal("0"),
            sort_order=0,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_cycle_validation_rejects_loop():
    with pytest.raises(CyclicItemCompositionError):
        assert_acyclic_components([("A", "B"), ("B", "C"), ("C", "A")])


def test_seed_relation_counts(db_session):
    seed_fair_stand_catalog(db_session)
    db_session.flush()
    assets = db_session.execute(text("SELECT COUNT(*) FROM fair_stand_item_assets")).scalar_one()
    bodies = db_session.execute(text("SELECT COUNT(*) FROM fair_stand_item_body_parts")).scalar_one()
    walls = db_session.execute(text("SELECT COUNT(*) FROM fair_stand_item_video_walls")).scalar_one()
    item_keys = set(db_session.execute(text("SELECT item_key FROM fair_stand_items")).scalars().all())
    item_columns = {column["name"] for column in inspect(db_session.get_bind()).get_columns("fair_stand_items")}
    tables = set(inspect(db_session.get_bind()).get_table_names())
    assert assets > 0
    assert bodies > 0
    assert walls > 0
    assert len(item_keys) == 96
    assert {
        "panel_corner_42_5",
        "panel_corner_92",
        "panel_corner_142_5",
        "panel_corner_192",
    }.issubset(item_keys)
    assert "nominal_module_width_cm" not in item_columns
    assert "fair_stand_item_inner_corners" not in tables
    assert "fair_stand_item_inner_corner_replacements" not in tables
    assert "fair_stand_item_inner_corner_replacement_members" not in tables
