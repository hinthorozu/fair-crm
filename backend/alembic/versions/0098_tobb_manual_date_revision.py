"""Remember manual date edits even when dates return to a previous baseline."""
from alembic import op
import sqlalchemy as sa

revision = "0098_tobb_manual_date_revision"
down_revision = "0097_tobb_run_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("crm_fairs", sa.Column("tobb_date_revision", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("crm_fairs", "tobb_date_revision")
