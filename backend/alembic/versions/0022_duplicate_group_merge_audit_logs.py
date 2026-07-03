"""Duplicate group merge audit logs.

Revision ID: 0022_duplicate_group_merge_audit_logs
Revises: 0021_drop_customer_communication_scalars
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0022_duplicate_group_merge_audit_logs"
down_revision: Union[str, None] = "0021_drop_customer_communication_scalars"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    exists = connection.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = 'system_duplicate_group_merge_audit_logs'
            """
        )
    ).first()
    if exists:
        return

    op.create_table(
        "system_duplicate_group_merge_audit_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("executed_by_user_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("executed_by_user_email", sa.String(255), nullable=True),
        sa.Column("run_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("group_key", sa.String(512), nullable=False),
        sa.Column("group_by", sa.String(32), nullable=False),
        sa.Column("surviving_customer_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("archived_customer_ids", sa.JSON(), nullable=False),
        sa.Column("scalar_field_sources", sa.JSON(), nullable=False),
        sa.Column("selected_email_ids", sa.JSON(), nullable=False),
        sa.Column("selected_phone_ids", sa.JSON(), nullable=False),
        sa.Column("selected_website_ids", sa.JSON(), nullable=False),
        sa.Column("statistics", sa.JSON(), nullable=False),
        sa.Column("reconstruction_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_system_dg_merge_audit_org_executed_at",
        "system_duplicate_group_merge_audit_logs",
        ["organization_id", "executed_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_system_dg_merge_audit_org_executed_at",
        table_name="system_duplicate_group_merge_audit_logs",
    )
    op.drop_table("system_duplicate_group_merge_audit_logs")
