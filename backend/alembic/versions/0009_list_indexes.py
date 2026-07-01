"""List endpoint performance indexes (Sprint 08.0).

Revision ID: 0009_list_indexes
Revises: 0008_import_wizard
Create Date: 2026-07-01
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0009_list_indexes"
down_revision: Union[str, None] = "0008_import_wizard"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # crm_customers: normalized_name already indexed in 0001
    op.create_index(
        "ix_crm_customers_email",
        "crm_customers",
        ["email"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_crm_customers_phone",
        "crm_customers",
        ["phone"],
        if_not_exists=True,
    )

    op.create_index(
        "ix_crm_fairs_name",
        "crm_fairs",
        ["name"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_crm_fairs_start_date",
        "crm_fairs",
        ["start_date"],
        if_not_exists=True,
    )

    op.create_index(
        "ix_crm_activities_activity_date",
        "crm_activities",
        ["activity_date"],
        if_not_exists=True,
    )

    # crm_customer_fair_participations: customer_id and fair_id already indexed in 0007
    op.create_index(
        "ix_crm_cfp_participation_status",
        "crm_customer_fair_participations",
        ["participation_status"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_crm_cfp_participation_status",
        table_name="crm_customer_fair_participations",
        if_exists=True,
    )
    op.drop_index("ix_crm_activities_activity_date", table_name="crm_activities", if_exists=True)
    op.drop_index("ix_crm_fairs_start_date", table_name="crm_fairs", if_exists=True)
    op.drop_index("ix_crm_fairs_name", table_name="crm_fairs", if_exists=True)
    op.drop_index("ix_crm_customers_phone", table_name="crm_customers", if_exists=True)
    op.drop_index("ix_crm_customers_email", table_name="crm_customers", if_exists=True)
