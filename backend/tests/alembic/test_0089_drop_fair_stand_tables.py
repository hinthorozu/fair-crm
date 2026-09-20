from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

_migration_path = (
    Path(__file__).resolve().parents[2] / "alembic" / "versions" / "0089_drop_fair_stand_tables.py"
)
_spec = spec_from_file_location("migration_0089_drop_fair_stand_tables", _migration_path)
assert _spec and _spec.loader
migration = module_from_spec(_spec)
_spec.loader.exec_module(migration)


def test_0089_drops_leftover_fair_stand_tables():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE fair_stand_categories (id INTEGER PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE fair_stand_items (item_key VARCHAR PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE fair_stand_item_assets (id INTEGER PRIMARY KEY)"))
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migration.upgrade()
        tables = set(inspect(connection).get_table_names())
    assert "fair_stand_categories" not in tables
    assert "fair_stand_items" not in tables
    assert "fair_stand_item_assets" not in tables
