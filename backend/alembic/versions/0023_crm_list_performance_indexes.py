"""CRM list and duplicate-analysis performance indexes.

Revision ID: 0023_crm_list_performance_indexes
Revises: 0022_duplicate_group_merge_audit_logs
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0023_crm_list_performance_indexes"
down_revision: Union[str, None] = "0022_duplicate_group_merge_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_crm_customers_org_status",
        "crm_customers",
        ["organization_id", "status"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_crm_customers_org_normalized_name",
        "crm_customers",
        ["organization_id", "normalized_name"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_crm_customers_deleted_at",
        "crm_customers",
        ["deleted_at"],
        if_not_exists=True,
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_crm_customers_org_display_name_lower
        ON crm_customers (organization_id, lower(display_name))
        WHERE status <> 'deleted'
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_crm_customer_phones_phone
        ON crm_customer_phones (phone)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_crm_customer_websites_website
        ON crm_customer_websites (website)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_crm_customer_websites_website")
    op.execute("DROP INDEX IF EXISTS ix_crm_customer_phones_phone")
    op.execute("DROP INDEX IF EXISTS ix_crm_customers_org_display_name_lower")
    op.drop_index("ix_crm_customers_deleted_at", table_name="crm_customers", if_exists=True)
    op.drop_index("ix_crm_customers_org_normalized_name", table_name="crm_customers", if_exists=True)
    op.drop_index("ix_crm_customers_org_status", table_name="crm_customers", if_exists=True)
