"""Store crm_fairs.name as unbounded text.

Revision ID: 0091_fair_name_text
Revises: 0090_system_fair_identity
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0091_fair_name_text"
down_revision: Union[str, Sequence[str], None] = "0090_system_fair_identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("crm_fairs") as batch_op:
            batch_op.alter_column(
                "name",
                existing_type=sa.String(length=255),
                type_=sa.Text(),
                existing_nullable=False,
            )
        return
    op.alter_column(
        "crm_fairs",
        "name",
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("crm_fairs") as batch_op:
            batch_op.alter_column(
                "name",
                existing_type=sa.Text(),
                type_=sa.String(length=255),
                existing_nullable=False,
            )
        return
    op.alter_column(
        "crm_fairs",
        "name",
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=False,
    )
