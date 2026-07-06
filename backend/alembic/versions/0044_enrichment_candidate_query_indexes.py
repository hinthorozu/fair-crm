"""Composite indexes for enrichment candidate query performance.

Revision ID: 0044_enrichment_candidate_query_indexes
Revises: 0043_crm_todos
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0044_enrichment_candidate_query_indexes"
down_revision: Union[str, None] = "0043_crm_todos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = "0042_crm_customer_enrichment_state"


def upgrade() -> None:
    op.create_index(
        "ix_crm_customer_emails_org_customer",
        "crm_customer_emails",
        ["organization_id", "customer_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_crm_customer_websites_org_customer",
        "crm_customer_websites",
        ["organization_id", "customer_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_crm_customer_enrichment_states_org_customer",
        "crm_customer_enrichment_states",
        ["organization_id", "customer_id"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_crm_customer_enrichment_states_org_customer",
        table_name="crm_customer_enrichment_states",
        if_exists=True,
    )
    op.drop_index(
        "ix_crm_customer_websites_org_customer",
        table_name="crm_customer_websites",
        if_exists=True,
    )
    op.drop_index(
        "ix_crm_customer_emails_org_customer",
        table_name="crm_customer_emails",
        if_exists=True,
    )
