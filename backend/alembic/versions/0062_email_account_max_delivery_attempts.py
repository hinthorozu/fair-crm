"""Add email_accounts.max_delivery_attempts (1–5, default 3).

Revision ID: 0062_email_account_max_delivery_attempts
Revises: 0061_email_account_id_json_backfill
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0062_email_account_max_delivery_attempts"
down_revision: Union[str, None] = "0061_email_account_id_json_backfill"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CONSTRAINT = "ck_email_accounts_max_delivery_attempts"


def upgrade() -> None:
    op.add_column(
        "email_accounts",
        sa.Column(
            "max_delivery_attempts",
            sa.Integer(),
            nullable=False,
            server_default="3",
        ),
    )
    op.execute(
        sa.text(
            "UPDATE email_accounts SET max_delivery_attempts = 3 "
            "WHERE max_delivery_attempts IS NULL OR max_delivery_attempts < 1 "
            "OR max_delivery_attempts > 5"
        )
    )
    op.create_check_constraint(
        _CONSTRAINT,
        "email_accounts",
        "max_delivery_attempts >= 1 AND max_delivery_attempts <= 5",
    )


def downgrade() -> None:
    op.drop_constraint(_CONSTRAINT, "email_accounts", type_="check")
    op.drop_column("email_accounts", "max_delivery_attempts")
