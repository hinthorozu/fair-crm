"""Merge enrichment and todos migration branches.

Revision ID: 0045_merge_enrichment_and_todos
Revises: 0042_crm_customer_enrichment_state, 0044_enrichment_candidate_query_indexes
"""

from typing import Sequence, Union

revision: str = "0045_merge_enrichment_and_todos"
down_revision: Union[str, tuple[str, ...], None] = (
    "0042_crm_customer_enrichment_state",
    "0044_enrichment_candidate_query_indexes",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
