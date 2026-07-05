"""Create smtp_accounts table.

Revision ID: 0034_smtp_accounts
Revises: 0033_scraper_run_source_import_batch
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0034_smtp_accounts"
down_revision: Union[str, None] = "0033_scraper_run_source_import_batch"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "smtp_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("from_email", sa.String(length=255), nullable=False),
        sa.Column("from_name", sa.String(length=255), nullable=True),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("password", sa.Text(), nullable=True),
        sa.Column("encryption_type", sa.String(length=32), nullable=False, server_default="starttls"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_smtp_accounts_organization_id", "smtp_accounts", ["organization_id"])
    op.create_index("ix_smtp_accounts_is_default", "smtp_accounts", ["is_default"])
    op.create_index("ix_smtp_accounts_is_active", "smtp_accounts", ["is_active"])
    op.create_index(
        "uq_smtp_accounts_org_default",
        "smtp_accounts",
        ["organization_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND is_default = true"),
        sqlite_where=sa.text("deleted_at IS NULL AND is_default = 1"),
    )


def downgrade() -> None:
    op.drop_index("uq_smtp_accounts_org_default", table_name="smtp_accounts")
    op.drop_index("ix_smtp_accounts_is_active", table_name="smtp_accounts")
    op.drop_index("ix_smtp_accounts_is_default", table_name="smtp_accounts")
    op.drop_index("ix_smtp_accounts_organization_id", table_name="smtp_accounts")
    op.drop_table("smtp_accounts")
