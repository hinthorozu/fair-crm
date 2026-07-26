"""Add email_account_provider_configs for generic provider credentials + error policy.

Revision ID: 0064_email_account_provider_configs
Revises: 0063_drop_legacy_email_operation_type
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0064_email_account_provider_configs"
down_revision: Union[str, None] = "0063_drop_legacy_email_operation_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "email_account_provider_configs" in tables:
        return
    if "email_accounts" not in tables:
        return

    op.create_table(
        "email_account_provider_configs",
        sa.Column("email_account_id", sa.Uuid(), nullable=False),
        sa.Column("provider_key", sa.String(length=64), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("error_policy_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["email_account_id"],
            ["email_accounts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("email_account_id"),
    )
    op.create_index(
        "ix_email_account_provider_configs_provider_key",
        "email_account_provider_configs",
        ["provider_key"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "email_account_provider_configs" not in inspector.get_table_names():
        return
    op.drop_index(
        "ix_email_account_provider_configs_provider_key",
        table_name="email_account_provider_configs",
    )
    op.drop_table("email_account_provider_configs")
