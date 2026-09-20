"""Drop leftover fair_stand_* tables from fair_crm.

Revision ID: 0089_drop_fair_stand_tables
Revises: 0088_drop_legacy_inner_corner_and_nominal

Catalog data lives in the fair_stand database / Fair Stand API. This revision
only removes the unused CRM copy. It does not drop the fair_stand database.
"""

from alembic import op
from sqlalchemy import inspect

revision = "0089_drop_fair_stand_tables"
down_revision = "0088_drop_legacy_inner_corner_and_nominal"
branch_labels = None
depends_on = None

TABLES = (
    "fair_stand_item_body_parts",
    "fair_stand_item_video_walls",
    "fair_stand_item_components",
    "fair_stand_item_assets",
    "fair_stand_item_strip_occupancy",
    "fair_stand_item_scene_dimensions",
    "fair_stand_item_dimensions",
    "fair_stand_items",
    "fair_stand_catalog_preview_kinds",
    "fair_stand_categories",
)


def upgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    for table in TABLES:
        if table in existing:
            op.drop_table(table)


def downgrade() -> None:
    raise NotImplementedError(
        "fair_stand_* tables were moved to the fair_stand database; restore from backup"
    )
