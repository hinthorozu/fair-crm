"""Remove retired operation_types.key='email' catalog row.

Revision ID: 0063_drop_legacy_email_operation_type
Revises: 0062_email_account_max_delivery_attempts
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0063_drop_legacy_email_operation_type"
down_revision: Union[str, None] = "0062_email_account_max_delivery_attempts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "operation_types" not in inspector.get_table_names():
        return
    op.execute(sa.text("DELETE FROM operation_types WHERE key = 'email'"))


def downgrade() -> None:
    # Intentionally no-op: legacy EMAIL operation type is not restored.
    pass
