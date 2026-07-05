"""Add optional metadata_json to crm_activities for system activity context.

Revision ID: 0037_crm_activity_metadata_json
Revises: 0036_crm_fair_email_outbox
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0037_crm_activity_metadata_json"
down_revision: Union[str, None] = "0036_crm_fair_email_outbox"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("crm_activities", sa.Column("metadata_json", sa.JSON(), nullable=True))
    op.execute(
        """
        CREATE UNIQUE INDEX uq_crm_activities_fair_bulk_email_outbox
        ON crm_activities (organization_id, (metadata_json->>'outbox_id'))
        WHERE metadata_json->>'source' = 'fair_bulk_email' AND deleted_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_crm_activities_fair_bulk_email_outbox")
    op.drop_column("crm_activities", "metadata_json")
