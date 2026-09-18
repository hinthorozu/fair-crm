from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import inspect, text
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
        "fair_stand_item_inner_corners",
        "fair_stand_item_inner_corner_replacements",
        "fair_stand_item_inner_corner_replacement_members",
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


def test_duplicate_item_key_rejected(db_session):
    db_session.add(_item(item_key="dup_key"))
    db_session.flush()
    db_session.add(_item(item_key="dup_key", name="Other"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_invalid_category_fk_rejected(db_session):
    db_session.add(_item(item_key="bad_cat", catalog_key="missing-category"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_invalid_preview_fk_rejected(db_session):
    db_session.add(
        FairStandCatalogPreviewKindModel(preview_key="shelf", sort_index=1),
    )
    db_session.add(
        FairStandCategoryModel(
            catalog_key="extra",
            catalog_name="Extra",
            catalog_index=1,
            is_active=True,
            created_at=_now(),
            updated_at=_now(),
        )
    )
    db_session.flush()
    db_session.add(
        _item(
            item_key="bad_preview",
            catalog_visible=True,
            catalog_key="extra",
            catalog_item_index=1,
            catalog_preview_key="not-a-preview",
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
    inner = db_session.execute(text("SELECT COUNT(*) FROM fair_stand_item_inner_corners")).scalar_one()
    replacements = db_session.execute(text("SELECT COUNT(*) FROM fair_stand_item_inner_corner_replacements")).scalar_one()
    members = db_session.execute(
        text("SELECT COUNT(*) FROM fair_stand_item_inner_corner_replacement_members")
    ).scalar_one()
    bodies = db_session.execute(text("SELECT COUNT(*) FROM fair_stand_item_body_parts")).scalar_one()
    walls = db_session.execute(text("SELECT COUNT(*) FROM fair_stand_item_video_walls")).scalar_one()
    assert assets > 0
    assert inner > 0
    assert replacements > 0
    assert members > 0
    assert bodies > 0
    assert walls > 0
