"""Store the persistent System Fair identity label.

Revision ID: 0093_system_fair_identity_name
Revises: 0092_restore_job_manifest_json
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0093_system_fair_identity_name"
down_revision: Union[str, Sequence[str], None] = "0092_restore_job_manifest_json"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEX_NAME = "ix_crm_fairs_system_identity_name"


def upgrade() -> None:
    op.add_column(
        "crm_fairs",
        sa.Column("identity_name", sa.String(length=500), nullable=False, server_default=""),
    )
    from app.modules.fairs.domain.services.normalizers import compute_identity_name

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, name FROM crm_fairs")).fetchall()
    for row in rows:
        bind.execute(
            sa.text("UPDATE crm_fairs SET identity_name = :identity_name WHERE id = :id"),
            {
                "identity_name": compute_identity_name(name=row.name),
                "id": row.id,
            },
        )
    op.create_index(
        INDEX_NAME,
        "crm_fairs",
        ["origin", "source", "identity_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="crm_fairs")
    op.drop_column("crm_fairs", "identity_name")
