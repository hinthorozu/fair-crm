"""Add system fair identity columns to crm_fairs.

Revision ID: 0090_system_fair_identity
Revises: 0089_drop_fair_stand_tables
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0090_system_fair_identity"
down_revision: Union[str, Sequence[str], None] = "0089_drop_fair_stand_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CHECK_SQL = (
    "(origin = 'organization' AND organization_id IS NOT NULL) "
    "OR (origin = 'system' AND organization_id IS NULL)"
)
UNIQUE_INDEX = "uq_crm_fairs_system_external_id"
CHECK_NAME = "ck_crm_fairs_origin_organization"


def upgrade() -> None:
    op.add_column(
        "crm_fairs",
        sa.Column("origin", sa.String(length=32), nullable=False, server_default="organization"),
    )
    op.add_column("crm_fairs", sa.Column("source", sa.String(length=32), nullable=True))
    op.add_column("crm_fairs", sa.Column("external_id", sa.String(length=64), nullable=True))
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("crm_fairs") as batch_op:
            batch_op.alter_column("organization_id", existing_type=sa.Uuid(), nullable=True)
            batch_op.create_check_constraint(CHECK_NAME, CHECK_SQL)
    else:
        op.alter_column("crm_fairs", "organization_id", existing_type=sa.Uuid(), nullable=True)
        op.create_check_constraint(CHECK_NAME, "crm_fairs", CHECK_SQL)
    op.create_index(
        UNIQUE_INDEX,
        "crm_fairs",
        ["source", "external_id"],
        unique=True,
        sqlite_where=sa.text("origin = 'system'"),
        postgresql_where=sa.text("origin = 'system'"),
    )


def downgrade() -> None:
    op.drop_index(UNIQUE_INDEX, table_name="crm_fairs")
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("crm_fairs") as batch_op:
            batch_op.drop_constraint(CHECK_NAME, type_="check")
            batch_op.alter_column("organization_id", existing_type=sa.Uuid(), nullable=False)
    else:
        op.drop_constraint(CHECK_NAME, "crm_fairs", type_="check")
        op.alter_column("crm_fairs", "organization_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_column("crm_fairs", "external_id")
    op.drop_column("crm_fairs", "source")
    op.drop_column("crm_fairs", "origin")
