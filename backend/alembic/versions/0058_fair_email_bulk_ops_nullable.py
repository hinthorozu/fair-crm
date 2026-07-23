"""Nullable fair/customer/participation for operations bulk email; attempt-based activities.

Revision ID: 0058_fair_email_bulk_ops_nullable
Revises: 0057_drop_execution_ready_requires_worker
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0058_fair_email_bulk_ops_nullable"
down_revision: Union[str, None] = "0057_drop_execution_ready_requires_worker"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "crm_fair_email_batches",
        "fair_id",
        existing_type=sa.Uuid(as_uuid=True),
        nullable=True,
    )
    op.add_column(
        "crm_fair_email_batches",
        sa.Column("operation_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_crm_fair_email_batches_operation_id",
        "crm_fair_email_batches",
        ["operation_id"],
        unique=False,
    )

    op.alter_column(
        "crm_fair_email_outbox",
        "customer_id",
        existing_type=sa.Uuid(as_uuid=True),
        nullable=True,
    )
    op.alter_column(
        "crm_fair_email_outbox",
        "participation_id",
        existing_type=sa.Uuid(as_uuid=True),
        nullable=True,
    )
    op.add_column(
        "crm_fair_email_outbox",
        sa.Column(
            "send_attempt",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )

    op.execute("DROP INDEX IF EXISTS uq_crm_activities_fair_bulk_email_outbox")
    op.execute(
        """
        CREATE UNIQUE INDEX uq_crm_activities_fair_bulk_email_outbox_attempt
        ON crm_activities (
            organization_id,
            (metadata_json->>'outbox_id'),
            (metadata_json->>'send_attempt')
        )
        WHERE metadata_json->>'source' = 'fair_bulk_email' AND deleted_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_crm_activities_fair_bulk_email_outbox_attempt")
    op.execute(
        """
        CREATE UNIQUE INDEX uq_crm_activities_fair_bulk_email_outbox
        ON crm_activities (organization_id, (metadata_json->>'outbox_id'))
        WHERE metadata_json->>'source' = 'fair_bulk_email' AND deleted_at IS NULL
        """
    )

    op.drop_column("crm_fair_email_outbox", "send_attempt")
    op.alter_column(
        "crm_fair_email_outbox",
        "participation_id",
        existing_type=sa.Uuid(as_uuid=True),
        nullable=False,
    )
    op.alter_column(
        "crm_fair_email_outbox",
        "customer_id",
        existing_type=sa.Uuid(as_uuid=True),
        nullable=False,
    )

    op.drop_index("ix_crm_fair_email_batches_operation_id", table_name="crm_fair_email_batches")
    op.drop_column("crm_fair_email_batches", "operation_id")
    op.alter_column(
        "crm_fair_email_batches",
        "fair_id",
        existing_type=sa.Uuid(as_uuid=True),
        nullable=False,
    )
