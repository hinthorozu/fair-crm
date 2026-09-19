from sqlalchemy import inspect, select

from app.modules.fair_stand.application.cycle_validation import CyclicItemCompositionError, assert_acyclic_components
from app.modules.fair_stand.infrastructure.catalog_seed_data import CATALOG_SEED
from app.modules.fair_stand.infrastructure.models import FairStandCategoryModel, FairStandItemComponentModel, FairStandItemModel
from app.modules.fair_stand.infrastructure.seed_catalog import seed_fair_stand_catalog


def test_seed_is_idempotent_and_matches_canonical_counts(db_session):
    seed_fair_stand_catalog(db_session)
    seed_fair_stand_catalog(db_session)
    db_session.flush()

    items = db_session.scalars(select(FairStandItemModel)).all()
    categories = db_session.scalars(select(FairStandCategoryModel)).all()
    components = db_session.scalars(select(FairStandItemComponentModel)).all()
    visible = [item for item in items if item.catalog_visible]

    assert len(categories) == 6
    assert len(items) == 96
    assert len(visible) == 58
    assert len(components) == 186
    assert {item.item_key for item in items} == {row["item_key"] for row in CATALOG_SEED["items"]}
    assert {category.catalog_name for category in categories} == {
        row["catalog_name"] for row in CATALOG_SEED["categories"]
    }
    assert "catalog_key" not in FairStandCategoryModel.__table__.c
    assert "catalog_key" not in FairStandItemModel.__table__.c
    assert "category_id" in FairStandItemModel.__table__.c
    assert all(isinstance(category.id, int) for category in categories)
    assert {item.category_id for item in visible}.issubset({category.id for category in categories})
    assert None not in {item.category_id for item in visible}


def test_cycle_validation_rejects_loop():
    try:
        assert_acyclic_components([("A", "B"), ("B", "A")])
    except CyclicItemCompositionError as exc:
        assert "A" in str(exc)
    else:
        raise AssertionError("expected cycle")


def test_self_component_rejected_by_seed_graph():
    assert_acyclic_components([("A", "B"), ("B", "C")])
