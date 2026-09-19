"""Replace category catalog_key identity with integer id.

Revision ID: 0086_fair_stand_category_integer_id
Revises: 0085_fair_stand_catalog_previews
"""

from alembic import op
import sqlalchemy as sa

revision = "0086_fair_stand_category_integer_id"
down_revision = "0085_fair_stand_catalog_previews"
branch_labels = None
depends_on = None

FK = {"ondelete": "CASCADE", "onupdate": "CASCADE"}


def _inspector():
    return sa.inspect(op.get_bind())


def _drop_fk(table: str, column: str) -> None:
    for fk in _inspector().get_foreign_keys(table):
        if column in (fk.get("constrained_columns") or []):
            name = fk.get("name")
            if name:
                op.drop_constraint(name, table, type_="foreignkey")


def _drop_pk(table: str) -> None:
    for constraint in _inspector().get_pk_constraint(table).get("name") and [
        _inspector().get_pk_constraint(table)
    ] or []:
        name = constraint.get("name")
        if name:
            op.drop_constraint(name, table, type_="primary")


def _drop_index_if_exists(name: str, table: str) -> None:
    existing = {index["name"] for index in _inspector().get_indexes(table)}
    if name in existing:
        op.drop_index(name, table_name=table)


def _assert_backfill(connection) -> None:
    categories = connection.execute(sa.text("SELECT COUNT(*) FROM fair_stand_categories")).scalar_one()
    items = connection.execute(sa.text("SELECT COUNT(*) FROM fair_stand_items")).scalar_one()
    keyed = connection.execute(
        sa.text("SELECT COUNT(*) FROM fair_stand_items WHERE catalog_key IS NOT NULL")
    ).scalar_one()
    linked = connection.execute(
        sa.text("SELECT COUNT(*) FROM fair_stand_items WHERE category_id IS NOT NULL")
    ).scalar_one()
    orphan = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM fair_stand_items "
            "WHERE catalog_key IS NOT NULL AND category_id IS NULL"
        )
    ).scalar_one()
    missing_id = connection.execute(
        sa.text("SELECT COUNT(*) FROM fair_stand_categories WHERE id IS NULL")
    ).scalar_one()
    if missing_id:
        raise RuntimeError("Category integer id backfill left NULL ids")
    if keyed != linked or orphan:
        raise RuntimeError(
            f"Item→Category backfill mismatch: categories={categories} items={items} "
            f"keyed={keyed} linked={linked} orphan={orphan}"
        )


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.add_column("fair_stand_categories", sa.Column("id", sa.Integer(), nullable=True))
    bind.execute(
        sa.text(
            "UPDATE fair_stand_categories SET id = catalog_index "
            "WHERE id IS NULL"
        )
    )
    op.add_column("fair_stand_items", sa.Column("category_id", sa.Integer(), nullable=True))
    bind.execute(
        sa.text(
            "UPDATE fair_stand_items SET category_id = ("
            "SELECT fair_stand_categories.id FROM fair_stand_categories "
            "WHERE fair_stand_categories.catalog_key = fair_stand_items.catalog_key"
            ") WHERE catalog_key IS NOT NULL"
        )
    )
    _assert_backfill(bind)

    if dialect == "sqlite":
        with op.batch_alter_table("fair_stand_items") as batch_op:
            batch_op.drop_constraint("ck_fair_stand_items_catalog_visible", type_="check")
            try:
                batch_op.drop_index("uq_fair_stand_items_catalog_order")
            except Exception:
                pass
            try:
                batch_op.drop_index("ix_fair_stand_items_catalog_key")
            except Exception:
                pass
            batch_op.drop_column("catalog_key")
        with op.batch_alter_table("fair_stand_categories") as batch_op:
            batch_op.alter_column("id", existing_type=sa.Integer(), nullable=False)
            batch_op.drop_column("catalog_key")
            batch_op.create_primary_key("pk_fair_stand_categories", ["id"])
        with op.batch_alter_table("fair_stand_items") as batch_op:
            batch_op.create_foreign_key(
                "fk_fair_stand_items_category_id_fair_stand_categories",
                "fair_stand_categories",
                ["category_id"],
                ["id"],
                **FK,
            )
            batch_op.create_check_constraint(
                "ck_fair_stand_items_catalog_visible",
                "NOT catalog_visible OR (category_id IS NOT NULL AND catalog_item_index IS NOT NULL AND catalog_preview_key IS NOT NULL)",
            )
        op.create_index("ix_fair_stand_items_category_id", "fair_stand_items", ["category_id"])
        op.create_index(
            "uq_fair_stand_items_catalog_order",
            "fair_stand_items",
            ["category_id", "catalog_item_index"],
            unique=True,
            sqlite_where=sa.text("catalog_visible IS TRUE"),
        )
        return

    op.execute("ALTER TABLE fair_stand_items DROP CONSTRAINT IF EXISTS ck_fair_stand_items_catalog_visible")
    _drop_index_if_exists("uq_fair_stand_items_catalog_order", "fair_stand_items")
    _drop_index_if_exists("ix_fair_stand_items_catalog_key", "fair_stand_items")
    _drop_fk("fair_stand_items", "catalog_key")
    op.drop_column("fair_stand_items", "catalog_key")

    pk = _inspector().get_pk_constraint("fair_stand_categories")
    if pk and pk.get("name"):
        op.drop_constraint(pk["name"], "fair_stand_categories", type_="primary")
    op.alter_column("fair_stand_categories", "id", existing_type=sa.Integer(), nullable=False)
    op.create_primary_key("fair_stand_categories_pkey", "fair_stand_categories", ["id"])
    op.execute("CREATE SEQUENCE IF NOT EXISTS fair_stand_categories_id_seq OWNED BY fair_stand_categories.id")
    op.execute(
        "SELECT setval("
        "'fair_stand_categories_id_seq', "
        "(SELECT COALESCE(MAX(id), 1) FROM fair_stand_categories), "
        "(SELECT COUNT(*) > 0 FROM fair_stand_categories)"
        ")"
    )
    op.execute("ALTER TABLE fair_stand_categories ALTER COLUMN id SET DEFAULT nextval('fair_stand_categories_id_seq')")
    op.drop_column("fair_stand_categories", "catalog_key")

    op.create_foreign_key(
        "fk_fair_stand_items_category_id_fair_stand_categories",
        "fair_stand_items",
        "fair_stand_categories",
        ["category_id"],
        ["id"],
        **FK,
    )
    op.create_index("ix_fair_stand_items_category_id", "fair_stand_items", ["category_id"])
    op.create_index(
        "uq_fair_stand_items_catalog_order",
        "fair_stand_items",
        ["category_id", "catalog_item_index"],
        unique=True,
        postgresql_where=sa.text("catalog_visible IS TRUE"),
    )
    op.create_check_constraint(
        "ck_fair_stand_items_catalog_visible",
        "fair_stand_items",
        "NOT catalog_visible OR (category_id IS NOT NULL AND catalog_item_index IS NOT NULL AND catalog_preview_key IS NOT NULL)",
    )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    op.add_column("fair_stand_categories", sa.Column("catalog_key", sa.String(length=64), nullable=True))
    bind.execute(sa.text("UPDATE fair_stand_categories SET catalog_key = 'category-' || id::text"))
    op.add_column("fair_stand_items", sa.Column("catalog_key", sa.String(length=64), nullable=True))
    bind.execute(
        sa.text(
            "UPDATE fair_stand_items SET catalog_key = ("
            "SELECT fair_stand_categories.catalog_key FROM fair_stand_categories "
            "WHERE fair_stand_categories.id = fair_stand_items.category_id"
            ")"
        )
    )
    if dialect != "sqlite":
        op.execute("ALTER TABLE fair_stand_items DROP CONSTRAINT IF EXISTS ck_fair_stand_items_catalog_visible")
        _drop_index_if_exists("uq_fair_stand_items_catalog_order", "fair_stand_items")
        _drop_index_if_exists("ix_fair_stand_items_category_id", "fair_stand_items")
        _drop_fk("fair_stand_items", "category_id")
        op.drop_column("fair_stand_items", "category_id")
        pk = _inspector().get_pk_constraint("fair_stand_categories")
        if pk and pk.get("name"):
            op.drop_constraint(pk["name"], "fair_stand_categories", type_="primary")
        op.alter_column("fair_stand_categories", "catalog_key", existing_type=sa.String(length=64), nullable=False)
        op.create_primary_key("fair_stand_categories_pkey", "fair_stand_categories", ["catalog_key"])
        op.drop_column("fair_stand_categories", "id")
        op.create_foreign_key(
            "fair_stand_items_catalog_key_fkey",
            "fair_stand_items",
            "fair_stand_categories",
            ["catalog_key"],
            ["catalog_key"],
            **FK,
        )
        op.create_index("ix_fair_stand_items_catalog_key", "fair_stand_items", ["catalog_key"])
        op.create_index(
            "uq_fair_stand_items_catalog_order",
            "fair_stand_items",
            ["catalog_key", "catalog_item_index"],
            unique=True,
            postgresql_where=sa.text("catalog_visible IS TRUE"),
        )
        op.create_check_constraint(
            "ck_fair_stand_items_catalog_visible",
            "fair_stand_items",
            "NOT catalog_visible OR (catalog_key IS NOT NULL AND catalog_item_index IS NOT NULL AND catalog_preview_key IS NOT NULL)",
        )
        return
    raise NotImplementedError("SQLite downgrade for 0086 is not supported")
