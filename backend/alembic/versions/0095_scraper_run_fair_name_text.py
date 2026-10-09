"""Store scraper_run_history.fair_name as unbounded text.

Official TOBB titles are longer than varchar(255). crm_fairs.name is already text.

Revision ID: 0095_scraper_run_fair_name_text
Revises: 0094_system_fair_separations
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0095_scraper_run_fair_name_text"
down_revision: Union[str, Sequence[str], None] = "0094_system_fair_separations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("scraper_run_history") as batch_op:
            batch_op.alter_column(
                "fair_name",
                existing_type=sa.String(length=255),
                type_=sa.Text(),
                existing_nullable=True,
            )
        return
    op.alter_column(
        "scraper_run_history",
        "fair_name",
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("scraper_run_history") as batch_op:
            batch_op.alter_column(
                "fair_name",
                existing_type=sa.Text(),
                type_=sa.String(length=255),
                existing_nullable=True,
            )
        return
    op.alter_column(
        "scraper_run_history",
        "fair_name",
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
