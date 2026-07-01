"""crm_import_batches and crm_import_rows tables."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_crm_imports"
down_revision: Union[str, None] = "0005_crm_activities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crm_import_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("file_name", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invalid_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_crm_import_batches_organization_id", "crm_import_batches", ["organization_id"]
    )

    op.create_table(
        "crm_import_rows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("raw_data_json", sa.JSON(), nullable=False),
        sa.Column("normalized_data_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("validation_errors_json", sa.JSON(), nullable=True),
        sa.Column("match_customer_id", sa.Uuid(), nullable=True),
        sa.Column("match_confidence", sa.Integer(), nullable=True),
        sa.Column("match_reason", sa.String(length=255), nullable=True),
        sa.Column("decision", sa.String(length=32), nullable=True),
        sa.Column("created_customer_id", sa.Uuid(), nullable=True),
        sa.Column("updated_customer_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["crm_import_batches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_import_rows_batch_id", "crm_import_rows", ["batch_id"])
    op.create_index(
        "ix_crm_import_rows_organization_id", "crm_import_rows", ["organization_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_crm_import_rows_organization_id", table_name="crm_import_rows")
    op.drop_index("ix_crm_import_rows_batch_id", table_name="crm_import_rows")
    op.drop_table("crm_import_rows")
    op.drop_index("ix_crm_import_batches_organization_id", table_name="crm_import_batches")
    op.drop_table("crm_import_batches")
