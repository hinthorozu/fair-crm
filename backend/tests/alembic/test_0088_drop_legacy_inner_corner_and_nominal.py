from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

_migration_path = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "0088_drop_legacy_inner_corner_and_nominal.py"
)
_spec = spec_from_file_location("migration_0088_drop_legacy_inner_corner_and_nominal", _migration_path)
assert _spec and _spec.loader
migration = module_from_spec(_spec)
_spec.loader.exec_module(migration)


def test_0088_drops_legacy_relations_and_keeps_item_keys():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE fair_stand_items (
                    item_key VARCHAR(128) PRIMARY KEY,
                    name VARCHAR(256) NOT NULL,
                    item_type VARCHAR(64) NOT NULL,
                    catalog_visible BOOLEAN NOT NULL,
                    is_active BOOLEAN NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    nominal_module_width_cm NUMERIC(8, 2),
                    CONSTRAINT ck_fair_stand_items_nominal_width
                        CHECK (nominal_module_width_cm IS NULL OR nominal_module_width_cm > 0)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE fair_stand_item_inner_corners (
                    parent_item_key VARCHAR(128) PRIMARY KEY,
                    panel_item_key VARCHAR(128) NOT NULL,
                    FOREIGN KEY(parent_item_key) REFERENCES fair_stand_items(item_key),
                    FOREIGN KEY(panel_item_key) REFERENCES fair_stand_items(item_key)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE fair_stand_item_inner_corner_replacements (
                    id BLOB PRIMARY KEY,
                    parent_item_key VARCHAR(128) NOT NULL,
                    replaced_item_key VARCHAR(128) NOT NULL,
                    sort_order INTEGER NOT NULL,
                    FOREIGN KEY(parent_item_key) REFERENCES fair_stand_item_inner_corners(parent_item_key),
                    FOREIGN KEY(replaced_item_key) REFERENCES fair_stand_items(item_key)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE fair_stand_item_inner_corner_replacement_members (
                    id BLOB PRIMARY KEY,
                    replacement_id BLOB NOT NULL,
                    child_item_key VARCHAR(128) NOT NULL,
                    quantity NUMERIC(12, 4) NOT NULL,
                    sort_order INTEGER NOT NULL,
                    FOREIGN KEY(replacement_id) REFERENCES fair_stand_item_inner_corner_replacements(id),
                    FOREIGN KEY(child_item_key) REFERENCES fair_stand_items(item_key)
                )
                """
            )
        )
        for key in ("wall_200", "panel_197", "panel_corner_192"):
            connection.execute(
                text(
                    """
                    INSERT INTO fair_stand_items (
                        item_key, name, item_type, catalog_visible, is_active,
                        created_at, updated_at, nominal_module_width_cm
                    ) VALUES (:key, :key, 'panel', 0, 1, '2026-01-01', '2026-01-01', 200)
                    """
                ),
                {"key": key},
            )
        connection.execute(
            text(
                """
                INSERT INTO fair_stand_item_inner_corners (parent_item_key, panel_item_key)
                VALUES ('wall_200', 'panel_corner_192')
                """
            )
        )
        before = [row[0] for row in connection.execute(text("SELECT item_key FROM fair_stand_items ORDER BY 1"))]
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migration.upgrade()
        after = [row[0] for row in connection.execute(text("SELECT item_key FROM fair_stand_items ORDER BY 1"))]
        tables = set(inspect(connection).get_table_names())
        columns = {column["name"] for column in inspect(connection).get_columns("fair_stand_items")}

    assert before == after == ["panel_197", "panel_corner_192", "wall_200"]
    assert "fair_stand_item_inner_corners" not in tables
    assert "fair_stand_item_inner_corner_replacements" not in tables
    assert "fair_stand_item_inner_corner_replacement_members" not in tables
    assert "nominal_module_width_cm" not in columns
