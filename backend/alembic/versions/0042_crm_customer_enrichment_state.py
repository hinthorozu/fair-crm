"""Create crm_customer_enrichment_states table.

Revision ID: 0042_crm_customer_enrichment_state
Revises: 0041_fair_email_outbox_mail_operation_unique
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0042_crm_customer_enrichment_state"
down_revision: Union[str, None] = "0041_fair_email_outbox_mail_operation_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crm_customer_enrichment_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column(
            "customer_id",
            sa.Uuid(),
            sa.ForeignKey("crm_customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("website", sa.String(length=2048), nullable=True),
        sa.Column(
            "last_enrichment_run_id",
            sa.Uuid(),
            sa.ForeignKey("scraper_run_history.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("last_email_scan_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_email_scan_status", sa.String(length=32), nullable=False),
        sa.Column("last_email_found", sa.String(length=320), nullable=True),
        sa.Column("last_source_url", sa.Text(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("retry_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "customer_id",
            name="uq_crm_customer_enrichment_states_org_customer",
        ),
    )
    op.create_index(
        "ix_crm_customer_enrichment_states_organization_id",
        "crm_customer_enrichment_states",
        ["organization_id"],
    )
    op.create_index(
        "ix_crm_customer_enrichment_states_customer_id",
        "crm_customer_enrichment_states",
        ["customer_id"],
    )
    op.create_index(
        "ix_crm_customer_enrichment_states_last_email_scan_status",
        "crm_customer_enrichment_states",
        ["last_email_scan_status"],
    )
    op.create_index(
        "ix_crm_customer_enrichment_states_retry_after",
        "crm_customer_enrichment_states",
        ["retry_after"],
    )


def downgrade() -> None:
    op.drop_index("ix_crm_customer_enrichment_states_retry_after", table_name="crm_customer_enrichment_states")
    op.drop_index(
        "ix_crm_customer_enrichment_states_last_email_scan_status",
        table_name="crm_customer_enrichment_states",
    )
    op.drop_index("ix_crm_customer_enrichment_states_customer_id", table_name="crm_customer_enrichment_states")
    op.drop_index("ix_crm_customer_enrichment_states_organization_id", table_name="crm_customer_enrichment_states")
    op.drop_table("crm_customer_enrichment_states")
