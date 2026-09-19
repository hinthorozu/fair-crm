"""Replace preview_key identity with integer id.

Revision ID: 0087_fair_stand_preview_integer_id
Revises: 0086_fair_stand_category_integer_id
"""

from alembic import op
import sqlalchemy as sa

revision = "0087_fair_stand_preview_integer_id"
down_revision = "0086_fair_stand_category_integer_id"
branch_labels = None
depends_on = None

FK = {"ondelete": "CASCADE", "onupdate": "CASCADE"}
VISIBLE_CHECK = (
    "NOT catalog_visible OR (category_id IS NOT NULL AND catalog_item_index IS NOT NULL AND preview_id IS NOT NULL)"
)


def _inspector():
    return sa.inspect(op.get_bind())


def _drop_fk(table: str, column: str) -> None:
    for fk in _inspector().get_foreign_keys(table):
        if column in (fk.get("constrained_columns") or []):
            name = fk.get("name")
            if name:
                op.drop_constraint(name, table, type_="foreignkey")


def _drop_index_if_exists(name: str, table: str) -> None:
    existing = {index["name"] for index in _inspector().get_indexes(table)}
    if name in existing:
        op.drop_index(name, table_name=table)


def _seed_if_empty(bind) -> None:
    count = bind.execute(sa.text("SELECT COUNT(*) FROM fair_stand_items")).scalar_one()
    if count:
        return
    from sqlalchemy.orm import Session

    from app.modules.fair_stand.infrastructure.seed_catalog import seed_fair_stand_catalog

    session = Session(bind=bind)
    seed_fair_stand_catalog(session)
    session.flush()


def _assert_backfill(connection) -> None:
    previews = connection.execute(sa.text("SELECT COUNT(*) FROM fair_stand_catalog_preview_kinds")).scalar_one()
    missing_id = connection.execute(
        sa.text("SELECT COUNT(*) FROM fair_stand_catalog_preview_kinds WHERE id IS NULL")
    ).scalar_one()
    keyed = connection.execute(
        sa.text("SELECT COUNT(*) FROM fair_stand_items WHERE catalog_preview_key IS NOT NULL")
    ).scalar_one()
    linked = connection.execute(
        sa.text("SELECT COUNT(*) FROM fair_stand_items WHERE preview_id IS NOT NULL")
    ).scalar_one()
    orphan = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM fair_stand_items "
            "WHERE catalog_preview_key IS NOT NULL AND preview_id IS NULL"
        )
    ).scalar_one()
    visible = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM fair_stand_items "
            "WHERE catalog_visible IS TRUE AND preview_id IS NOT NULL"
        )
    ).scalar_one()
    if missing_id:
        raise RuntimeError("Preview integer id backfill left NULL ids")
    if keyed != linked or orphan:
        raise RuntimeError(
            f"Item→Preview backfill mismatch: previews={previews} keyed={keyed} "
            f"linked={linked} orphan={orphan} visible={visible}"
        )


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.add_column("fair_stand_catalog_preview_kinds", sa.Column("id", sa.Integer(), nullable=True))
    bind.execute(
        sa.text(
            "UPDATE fair_stand_catalog_preview_kinds SET id = sort_index "
            "WHERE id IS NULL"
        )
    )
    op.add_column("fair_stand_items", sa.Column("preview_id", sa.Integer(), nullable=True))
    bind.execute(
        sa.text(
            "UPDATE fair_stand_items SET preview_id = ("
            "SELECT fair_stand_catalog_preview_kinds.id FROM fair_stand_catalog_preview_kinds "
            "WHERE fair_stand_catalog_preview_kinds.preview_key = fair_stand_items.catalog_preview_key"
            ") WHERE catalog_preview_key IS NOT NULL"
        )
    )
    _assert_backfill(bind)

    if dialect == "sqlite":
        with op.batch_alter_table("fair_stand_items") as batch_op:
            batch_op.drop_constraint("ck_fair_stand_items_catalog_visible", type_="check")
            batch_op.drop_column("catalog_preview_key")
        with op.batch_alter_table("fair_stand_catalog_preview_kinds") as batch_op:
            batch_op.alter_column("id", existing_type=sa.Integer(), nullable=False)
            batch_op.drop_column("preview_key")
            batch_op.create_primary_key("pk_fair_stand_catalog_preview_kinds", ["id"])
        with op.batch_alter_table("fair_stand_items") as batch_op:
            batch_op.create_foreign_key(
                "fk_fair_stand_items_preview_id_fair_stand_catalog_preview_kinds",
                "fair_stand_catalog_preview_kinds",
                ["preview_id"],
                ["id"],
                **FK,
            )
            batch_op.create_check_constraint("ck_fair_stand_items_catalog_visible", VISIBLE_CHECK)
        op.create_index("ix_fair_stand_items_preview_id", "fair_stand_items", ["preview_id"])
        _seed_if_empty(bind)
        return

    op.execute("ALTER TABLE fair_stand_items DROP CONSTRAINT IF EXISTS ck_fair_stand_items_catalog_visible")
    _drop_fk("fair_stand_items", "catalog_preview_key")
    op.drop_column("fair_stand_items", "catalog_preview_key")

    pk = _inspector().get_pk_constraint("fair_stand_catalog_preview_kinds")
    if pk and pk.get("name"):
        op.drop_constraint(pk["name"], "fair_stand_catalog_preview_kinds", type_="primary")
    op.alter_column("fair_stand_catalog_preview_kinds", "id", existing_type=sa.Integer(), nullable=False)
    op.create_primary_key("fair_stand_catalog_preview_kinds_pkey", "fair_stand_catalog_preview_kinds", ["id"])
    op.execute(
        "CREATE SEQUENCE IF NOT EXISTS fair_stand_catalog_preview_kinds_id_seq "
        "OWNED BY fair_stand_catalog_preview_kinds.id"
    )
    op.execute(
        "SELECT setval("
        "'fair_stand_catalog_preview_kinds_id_seq', "
        "(SELECT COALESCE(MAX(id), 1) FROM fair_stand_catalog_preview_kinds), "
        "(SELECT COUNT(*) > 0 FROM fair_stand_catalog_preview_kinds)"
        ")"
    )
    op.execute(
        "ALTER TABLE fair_stand_catalog_preview_kinds "
        "ALTER COLUMN id SET DEFAULT nextval('fair_stand_catalog_preview_kinds_id_seq')"
    )
    op.drop_column("fair_stand_catalog_preview_kinds", "preview_key")

    op.create_foreign_key(
        "fk_fair_stand_items_preview_id_fair_stand_catalog_preview_kinds",
        "fair_stand_items",
        "fair_stand_catalog_preview_kinds",
        ["preview_id"],
        ["id"],
        **FK,
    )
    op.create_index("ix_fair_stand_items_preview_id", "fair_stand_items", ["preview_id"])
    op.create_check_constraint(
        "ck_fair_stand_items_catalog_visible",
        "fair_stand_items",
        VISIBLE_CHECK,
    )
    _seed_if_empty(bind)


def downgrade() -> None:
    raise NotImplementedError("Preview integer-id migration is not reversible")
