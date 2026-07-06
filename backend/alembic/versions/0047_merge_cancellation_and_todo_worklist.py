"""Merge scraper cancellation and todo worklist migration branches.

Revision ID: 0047_merge_cancellation_and_todo_worklist
Revises: 0045_scraper_run_cancellation_fields, 0046_crm_todo_worklist_foundation
"""

from typing import Sequence, Union

revision: str = "0047_merge_cancellation_and_todo_worklist"
down_revision: Union[str, tuple[str, ...], None] = (
    "0045_scraper_run_cancellation_fields",
    "0046_crm_todo_worklist_foundation",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
