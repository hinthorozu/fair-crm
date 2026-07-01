"""Import wizard: fair_id, raw preview, column mapping, participation fields.

Revision ID: 0008_import_wizard
Revises: 0007_crm_participations
Create Date: 2026-07-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_import_wizard"
down_revision: Union[str, None] = "0007_crm_participations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "crm_import_batches",
        sa.Column("fair_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "crm_import_batches",
        sa.Column("source_type", sa.String(length=32), nullable=False, server_default="excel"),
    )
    op.add_column(
        "crm_import_batches",
        sa.Column("column_mapping_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "crm_import_batches",
        sa.Column("raw_preview_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "crm_import_batches",
        sa.Column("has_header_row", sa.Boolean(), nullable=True),
    )
    op.create_index("ix_crm_import_batches_fair_id", "crm_import_batches", ["fair_id"])

    op.add_column(
        "crm_import_rows",
        sa.Column("participation_exists", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "crm_import_rows",
        sa.Column("match_participation_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "crm_import_rows",
        sa.Column("suggested_action", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "crm_import_rows",
        sa.Column("created_participation_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "crm_import_rows",
        sa.Column("updated_participation_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "crm_import_batches",
        sa.Column("created_participations", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "crm_import_batches",
        sa.Column("updated_participations", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("crm_import_batches", "updated_participations")
    op.drop_column("crm_import_batches", "created_participations")
    op.drop_column("crm_import_rows", "updated_participation_id")
    op.drop_column("crm_import_rows", "created_participation_id")
    op.drop_column("crm_import_rows", "suggested_action")
    op.drop_column("crm_import_rows", "match_participation_id")
    op.drop_column("crm_import_rows", "participation_exists")
    op.drop_index("ix_crm_import_batches_fair_id", table_name="crm_import_batches")
    op.drop_column("crm_import_batches", "has_header_row")
    op.drop_column("crm_import_batches", "raw_preview_json")
    op.drop_column("crm_import_batches", "column_mapping_json")
    op.drop_column("crm_import_batches", "source_type")
    op.drop_column("crm_import_batches", "fair_id")
