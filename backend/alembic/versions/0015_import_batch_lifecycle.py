"""Add import batch lifecycle status migration (mapping_completed, analyze job support)."""

from typing import Sequence, Union

from alembic import op

revision: str = "0015_import_batch_lifecycle"
down_revision: Union[str, None] = "0014_backup_format_options"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE crm_import_batches SET status = 'mapping_completed' WHERE status = 'mapped'"
    )
    op.execute("UPDATE crm_import_batches SET status = 'completed' WHERE status = 'applied'")


def downgrade() -> None:
    op.execute(
        "UPDATE crm_import_batches SET status = 'mapped' WHERE status = 'mapping_completed'"
    )
    op.execute("UPDATE crm_import_batches SET status = 'applied' WHERE status = 'completed'")
