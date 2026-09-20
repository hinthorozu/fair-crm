"""Drop legacy inner-corner tables and nominal_module_width_cm.

Revision ID: 0088_drop_legacy_inner_corner_and_nominal
Revises: 0087_fair_stand_preview_integer_id

Does not delete fair_stand_items rows. Inner-corner relation rows are dropped
with their tables; Item identity rows stay.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0088_drop_legacy_inner_corner_and_nominal"
down_revision = "0087_fair_stand_preview_integer_id"
branch_labels = None
depends_on = None

FK = {"ondelete": "CASCADE", "onupdate": "CASCADE"}


def _item_snapshot(bind):
    count = bind.execute(sa.text("SELECT COUNT(*) FROM fair_stand_items")).scalar_one()
    keys = [
        row[0]
        for row in bind.execute(sa.text("SELECT item_key FROM fair_stand_items ORDER BY item_key"))
    ]
    return int(count), keys


def upgrade() -> None:
    bind = op.get_bind()
    before_count, before_keys = _item_snapshot(bind)

    op.drop_table("fair_stand_item_inner_corner_replacement_members")
    op.drop_table("fair_stand_item_inner_corner_replacements")
    op.drop_table("fair_stand_item_inner_corners")

    with op.batch_alter_table("fair_stand_items") as batch_op:
        batch_op.drop_constraint("ck_fair_stand_items_nominal_width", type_="check")
        batch_op.drop_column("nominal_module_width_cm")

    after_count, after_keys = _item_snapshot(bind)
    if after_count != before_count or after_keys != before_keys:
        raise RuntimeError(
            "0088 must not change fair_stand_items identity rows: "
            f"before={before_count} after={after_count}"
        )


def downgrade() -> None:
    uuid_type = sa.Uuid()
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        uuid_type = postgresql.UUID(as_uuid=True)

    with op.batch_alter_table("fair_stand_items") as batch_op:
        batch_op.add_column(sa.Column("nominal_module_width_cm", sa.Numeric(precision=8, scale=2), nullable=True))
        batch_op.create_check_constraint(
            "ck_fair_stand_items_nominal_width",
            "nominal_module_width_cm IS NULL OR nominal_module_width_cm > 0",
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
