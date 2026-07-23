"""Drop execution_ready and requires_worker from operation_types.

Revision ID: 0057_drop_execution_ready_requires_worker
Revises: 0056_operation_types_capabilities
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0057_drop_execution_ready_requires_worker"
down_revision: Union[str, None] = "0056_operation_types_capabilities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("operation_types", "execution_ready")
    op.drop_column("operation_types", "requires_worker")


def downgrade() -> None:
    op.add_column(
        "operation_types",
        sa.Column(
            "requires_worker",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "operation_types",
        sa.Column(
            "execution_ready",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.alter_column("operation_types", "requires_worker", server_default=None)
    op.alter_column("operation_types", "execution_ready", server_default=None)
