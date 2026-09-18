"""Fair Stand Item/Category relational catalog.

Revision ID: 0084_fair_stand_item_catalog
Revises: 0083_terminal_closure
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0084_fair_stand_item_catalog"
down_revision = "0083_terminal_closure"
branch_labels = None
depends_on = None

FK = {"ondelete": "CASCADE", "onupdate": "CASCADE"}


def upgrade() -> None:
    op.create_table(
        "fair_stand_categories",
        sa.Column("catalog_key", sa.String(length=64), nullable=False),
        sa.Column("catalog_name", sa.String(length=128), nullable=False),
        sa.Column("catalog_index", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("catalog_index > 0", name="ck_fair_stand_categories_catalog_index"),
        sa.PrimaryKeyConstraint("catalog_key"),
        sa.UniqueConstraint("catalog_index", name="uq_fair_stand_categories_catalog_index"),
    )

    op.create_table(
        "fair_stand_catalog_preview_kinds",
        sa.Column("preview_key", sa.String(length=64), nullable=False),
        sa.Column("sort_index", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("preview_key"),
    )

    op.create_table(
        "fair_stand_items",
        sa.Column("item_key", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("item_type", sa.String(length=64), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("catalog_visible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("catalog_key", sa.String(length=64), nullable=True),
        sa.Column("catalog_item_index", sa.Integer(), nullable=True),
        sa.Column("catalog_preview_key", sa.String(length=64), nullable=True),
        sa.Column("material", sa.String(length=64), nullable=True),
        sa.Column("default_color", sa.Integer(), nullable=True),
        sa.Column("panel_role", sa.String(length=32), nullable=True),
        sa.Column("nominal_module_width_cm", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("connector_type", sa.String(length=32), nullable=True),
        sa.Column("preserve_model_scale", sa.Boolean(), nullable=True),
        sa.Column("model_rotation_y_deg", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("visual_rotation_y_deg", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("composition_mode", sa.String(length=16), nullable=True),
        sa.Column("composition_module_type", sa.String(length=64), nullable=True),
        sa.Column("paintable", sa.Boolean(), nullable=True),
        sa.Column("shape", sa.String(length=16), nullable=True),
        sa.Column("variant", sa.String(length=64), nullable=True),
        sa.Column("eye_count", sa.SmallInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "panel_role IS NULL OR panel_role IN ('straight', 'inner-corner')",
            name="ck_fair_stand_items_panel_role",
        ),
        sa.CheckConstraint(
            "connector_type IS NULL OR connector_type IN ('start', 'single', 'double', 'corner')",
            name="ck_fair_stand_items_connector_type",
        ),
        sa.CheckConstraint("eye_count IS NULL OR eye_count IN (2, 3)", name="ck_fair_stand_items_eye_count"),
        sa.CheckConstraint(
            "nominal_module_width_cm IS NULL OR nominal_module_width_cm > 0",
            name="ck_fair_stand_items_nominal_width",
        ),
        sa.CheckConstraint(
            "composition_mode IS NULL OR composition_mode IN ('recipe')",
            name="ck_fair_stand_items_composition_mode",
        ),
        sa.CheckConstraint(
            "NOT catalog_visible OR (catalog_key IS NOT NULL AND catalog_item_index IS NOT NULL AND catalog_preview_key IS NOT NULL)",
            name="ck_fair_stand_items_catalog_visible",
        ),
        sa.ForeignKeyConstraint(["catalog_key"], ["fair_stand_categories.catalog_key"], **FK),
        sa.ForeignKeyConstraint(
            ["catalog_preview_key"], ["fair_stand_catalog_preview_kinds.preview_key"], **FK
        ),
        sa.PrimaryKeyConstraint("item_key"),
    )
    op.create_index("ix_fair_stand_items_item_type", "fair_stand_items", ["item_type"])
    op.create_index("ix_fair_stand_items_catalog_key", "fair_stand_items", ["catalog_key"])
    op.create_index("ix_fair_stand_items_is_active", "fair_stand_items", ["is_active"])
    op.create_index(
        "uq_fair_stand_items_catalog_order",
        "fair_stand_items",
        ["catalog_key", "catalog_item_index"],
        unique=True,
        postgresql_where=sa.text("catalog_visible IS TRUE"),
        sqlite_where=sa.text("catalog_visible IS TRUE"),
    )

    op.create_table(
        "fair_stand_item_dimensions",
        sa.Column("item_key", sa.String(length=128), nullable=False),
        sa.Column("width_cm", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("depth_cm", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("height_cm", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("length_cm", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("thickness_cm", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("mount_height_cm", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("wall_gap_cm", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.CheckConstraint(
            "width_cm IS NOT NULL OR depth_cm IS NOT NULL OR height_cm IS NOT NULL "
            "OR length_cm IS NOT NULL OR thickness_cm IS NOT NULL "
            "OR mount_height_cm IS NOT NULL OR wall_gap_cm IS NOT NULL",
            name="ck_fair_stand_item_dimensions_present",
        ),
        sa.ForeignKeyConstraint(["item_key"], ["fair_stand_items.item_key"], **FK),
        sa.PrimaryKeyConstraint("item_key"),
    )

    op.create_table(
        "fair_stand_item_scene_dimensions",
        sa.Column("item_key", sa.String(length=128), nullable=False),
        sa.Column("width_cm", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("depth_cm", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("height_cm", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.CheckConstraint(
            "width_cm IS NOT NULL OR depth_cm IS NOT NULL OR height_cm IS NOT NULL",
            name="ck_fair_stand_item_scene_dimensions_present",
        ),
        sa.ForeignKeyConstraint(["item_key"], ["fair_stand_items.item_key"], **FK),
        sa.PrimaryKeyConstraint("item_key"),
    )

    op.create_table(
        "fair_stand_item_strip_occupancy",
        sa.Column("item_key", sa.String(length=128), nullable=False),
        sa.Column("align", sa.String(length=16), nullable=False),
        sa.Column("strip_count", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint("strip_count > 0", name="ck_fair_stand_item_strip_count"),
        sa.CheckConstraint("align IN ('top')", name="ck_fair_stand_item_strip_align"),
        sa.ForeignKeyConstraint(["item_key"], ["fair_stand_items.item_key"], **FK),
        sa.PrimaryKeyConstraint("item_key"),
    )

    uuid_type = sa.Uuid()
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        uuid_type = postgresql.UUID(as_uuid=True)

    op.create_table(
        "fair_stand_item_assets",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("item_key", sa.String(length=128), nullable=False),
        sa.Column("asset_role", sa.String(length=32), nullable=False),
        sa.Column("relative_path", sa.String(length=512), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint(
            "asset_role IN ('model', 'default_screen', 'catalog_image', 'thumbnail', 'texture')",
            name="ck_fair_stand_item_assets_role",
        ),
        sa.ForeignKeyConstraint(["item_key"], ["fair_stand_items.item_key"], **FK),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("item_key", "asset_role", name="uq_fair_stand_item_assets_role"),
    )
    op.create_index("ix_fair_stand_item_assets_item_key", "fair_stand_item_assets", ["item_key"])

    op.create_table(
        "fair_stand_item_components",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("parent_item_key", sa.String(length=128), nullable=False),
        sa.Column("child_item_key", sa.String(length=128), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_fair_stand_item_components_quantity"),
        sa.CheckConstraint("parent_item_key <> child_item_key", name="ck_fair_stand_item_components_self"),
        sa.ForeignKeyConstraint(["parent_item_key"], ["fair_stand_items.item_key"], **FK),
        sa.ForeignKeyConstraint(["child_item_key"], ["fair_stand_items.item_key"], **FK),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parent_item_key", "sort_order", name="uq_fair_stand_item_components_sort"),
    )
    op.create_index(
        "ix_fair_stand_item_components_child", "fair_stand_item_components", ["child_item_key"]
    )

    op.create_table(
        "fair_stand_item_inner_corners",
        sa.Column("parent_item_key", sa.String(length=128), nullable=False),
        sa.Column("panel_item_key", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(["parent_item_key"], ["fair_stand_items.item_key"], **FK),
        sa.ForeignKeyConstraint(["panel_item_key"], ["fair_stand_items.item_key"], **FK),
        sa.PrimaryKeyConstraint("parent_item_key"),
    )

    op.create_table(
        "fair_stand_item_inner_corner_replacements",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("parent_item_key", sa.String(length=128), nullable=False),
        sa.Column("replaced_item_key", sa.String(length=128), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_item_key"], ["fair_stand_item_inner_corners.parent_item_key"], **FK
        ),
        sa.ForeignKeyConstraint(["replaced_item_key"], ["fair_stand_items.item_key"], **FK),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "parent_item_key", "replaced_item_key", name="uq_fair_stand_inner_corner_replaced"
        ),
    )

    op.create_table(
        "fair_stand_item_inner_corner_replacement_members",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("replacement_id", uuid_type, nullable=False),
        sa.Column("child_item_key", sa.String(length=128), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_fair_stand_inner_corner_member_qty"),
        sa.ForeignKeyConstraint(
            ["replacement_id"], ["fair_stand_item_inner_corner_replacements.id"], **FK
        ),
        sa.ForeignKeyConstraint(["child_item_key"], ["fair_stand_items.item_key"], **FK),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "replacement_id", "sort_order", name="uq_fair_stand_inner_corner_member_sort"
        ),
    )

    op.create_table(
        "fair_stand_item_video_walls",
        sa.Column("parent_item_key", sa.String(length=128), nullable=False),
        sa.Column("rows", sa.SmallInteger(), nullable=False),
        sa.Column("cols", sa.SmallInteger(), nullable=False),
        sa.Column("panel_item_key", sa.String(length=128), nullable=False),
        sa.CheckConstraint("rows > 0", name="ck_fair_stand_video_wall_rows"),
        sa.CheckConstraint("cols > 0", name="ck_fair_stand_video_wall_cols"),
        sa.ForeignKeyConstraint(["parent_item_key"], ["fair_stand_items.item_key"], **FK),
        sa.ForeignKeyConstraint(["panel_item_key"], ["fair_stand_items.item_key"], **FK),
        sa.PrimaryKeyConstraint("parent_item_key"),
    )

    op.create_table(
        "fair_stand_item_body_parts",
        sa.Column("parent_item_key", sa.String(length=128), nullable=False),
        sa.Column("body_role", sa.String(length=32), nullable=False),
        sa.Column("child_item_key", sa.String(length=128), nullable=False),
        sa.CheckConstraint(
            "body_role IN ('side', 'horizontal', 'glass_shelf')",
            name="ck_fair_stand_body_role",
        ),
        sa.ForeignKeyConstraint(["parent_item_key"], ["fair_stand_items.item_key"], **FK),
        sa.ForeignKeyConstraint(["child_item_key"], ["fair_stand_items.item_key"], **FK),
        sa.PrimaryKeyConstraint("parent_item_key", "body_role"),
    )

    from app.modules.fair_stand.infrastructure.seed_catalog import seed_fair_stand_catalog

    bind = op.get_bind()
    from sqlalchemy.orm import Session

    session = Session(bind=bind)
    seed_fair_stand_catalog(session)
    session.commit()


def downgrade() -> None:
    op.drop_table("fair_stand_item_body_parts")
    op.drop_table("fair_stand_item_video_walls")
    op.drop_table("fair_stand_item_inner_corner_replacement_members")
    op.drop_table("fair_stand_item_inner_corner_replacements")
    op.drop_table("fair_stand_item_inner_corners")
    op.drop_index("ix_fair_stand_item_components_child", table_name="fair_stand_item_components")
    op.drop_table("fair_stand_item_components")
    op.drop_index("ix_fair_stand_item_assets_item_key", table_name="fair_stand_item_assets")
    op.drop_table("fair_stand_item_assets")
    op.drop_table("fair_stand_item_strip_occupancy")
    op.drop_table("fair_stand_item_scene_dimensions")
    op.drop_table("fair_stand_item_dimensions")
    op.drop_index("uq_fair_stand_items_catalog_order", table_name="fair_stand_items")
    op.drop_index("ix_fair_stand_items_is_active", table_name="fair_stand_items")
    op.drop_index("ix_fair_stand_items_catalog_key", table_name="fair_stand_items")
    op.drop_index("ix_fair_stand_items_item_type", table_name="fair_stand_items")
    op.drop_table("fair_stand_items")
    op.drop_table("fair_stand_catalog_preview_kinds")
    op.drop_table("fair_stand_categories")
