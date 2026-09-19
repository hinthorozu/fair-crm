"""Expand catalog preview kinds into managed preview entities.

Revision ID: 0085_fair_stand_catalog_previews
Revises: 0084_fair_stand_item_catalog
"""

from datetime import UTC, datetime

from alembic import op
import sqlalchemy as sa

from app.modules.fair_stand.infrastructure.preview_kind_definitions import all_preview_kind_rows

revision = "0085_fair_stand_catalog_previews"
down_revision = "0084_fair_stand_item_catalog"
branch_labels = None
depends_on = None


def _existing_columns() -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns("fair_stand_catalog_preview_kinds")}


def upgrade() -> None:
    existing = _existing_columns()
    # Inspector reads the live table (0084 preview_key/sort_index). Do not use
    # op.add_column here: current model metadata already contains these names
    # and Alembic can skip the ALTER, then the UPDATE below fails.
    if "display_name" not in existing:
        op.execute(sa.text("ALTER TABLE fair_stand_catalog_preview_kinds ADD COLUMN display_name VARCHAR(128)"))
    if "markup" not in existing:
        op.execute(sa.text("ALTER TABLE fair_stand_catalog_preview_kinds ADD COLUMN markup TEXT"))
    if "css_code" not in existing:
        op.execute(sa.text("ALTER TABLE fair_stand_catalog_preview_kinds ADD COLUMN css_code TEXT"))
    if "is_active" not in existing:
        op.execute(sa.text("ALTER TABLE fair_stand_catalog_preview_kinds ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL"))
    bind = op.get_bind()
    timestamp_type = "TIMESTAMP WITH TIME ZONE" if bind.dialect.name == "postgresql" else "TIMESTAMP"
    if "created_at" not in existing:
        op.execute(sa.text(f"ALTER TABLE fair_stand_catalog_preview_kinds ADD COLUMN created_at {timestamp_type}"))
    if "updated_at" not in existing:
        op.execute(sa.text(f"ALTER TABLE fair_stand_catalog_preview_kinds ADD COLUMN updated_at {timestamp_type}"))

    bind = op.get_bind()
    now = datetime.now(tz=UTC)
    definitions = {row["preview_key"]: row for row in all_preview_kind_rows()}
    existing = bind.execute(sa.text("SELECT preview_key, sort_index FROM fair_stand_catalog_preview_kinds")).mappings().all()
    for row in existing:
        definition = definitions.get(row["preview_key"])
        if definition is None:
            display_name = str(row["preview_key"])
            markup = '<div class="module-drag-shelf" data-preview-width></div>'
            css_code = ""
            sort_index = row["sort_index"] or 0
        else:
            display_name = str(definition["display_name"])
            markup = str(definition["markup"])
            css_code = str(definition["css_code"])
            sort_index = int(definition["sort_index"])
        bind.execute(
            sa.text(
                """
                UPDATE fair_stand_catalog_preview_kinds
                SET display_name=:display_name,
                    markup=:markup,
                    css_code=:css_code,
                    sort_index=:sort_index,
                    is_active=TRUE,
                    created_at=:created_at,
                    updated_at=:updated_at
                WHERE preview_key=:preview_key
                """
            ),
            {
                "display_name": display_name,
                "markup": markup,
                "css_code": css_code,
                "sort_index": sort_index,
                "created_at": now,
                "updated_at": now,
                "preview_key": row["preview_key"],
            },
        )

    op.alter_column("fair_stand_catalog_preview_kinds", "display_name", nullable=False)
    op.alter_column("fair_stand_catalog_preview_kinds", "markup", nullable=False)
    op.alter_column("fair_stand_catalog_preview_kinds", "css_code", nullable=False)
    op.alter_column("fair_stand_catalog_preview_kinds", "sort_index", existing_type=sa.Integer(), nullable=False)
    op.alter_column("fair_stand_catalog_preview_kinds", "created_at", nullable=False)
    op.alter_column("fair_stand_catalog_preview_kinds", "updated_at", nullable=False)
    op.alter_column("fair_stand_catalog_preview_kinds", "is_active", server_default=None)


def downgrade() -> None:
    op.alter_column("fair_stand_catalog_preview_kinds", "sort_index", existing_type=sa.Integer(), nullable=True)
    op.drop_column("fair_stand_catalog_preview_kinds", "updated_at")
    op.drop_column("fair_stand_catalog_preview_kinds", "created_at")
    op.drop_column("fair_stand_catalog_preview_kinds", "is_active")
    op.drop_column("fair_stand_catalog_preview_kinds", "css_code")
    op.drop_column("fair_stand_catalog_preview_kinds", "markup")
    op.drop_column("fair_stand_catalog_preview_kinds", "display_name")
