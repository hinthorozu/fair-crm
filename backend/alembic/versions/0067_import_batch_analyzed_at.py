"""Add analyzed_at timestamp to import batches.

Revision ID: 0067_import_batch_analyzed_at
Revises: 0066_mail_send_external_message_id_idx
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0067_import_batch_analyzed_at"
down_revision: Union[str, None] = "0066_mail_send_external_message_id_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "crm_import_batches" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("crm_import_batches")}
    if "analyzed_at" in columns:
        return
    op.add_column("crm_import_batches", sa.Column("analyzed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "crm_import_batches" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("crm_import_batches")}
    if "analyzed_at" not in columns:
        return
    op.drop_column("crm_import_batches", "analyzed_at")
