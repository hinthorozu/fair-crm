"""Allow durable OL08-07 terminal closure completion state.

Revision ID: 0083_terminal_closure
Revises: 0082_closure_product_cleanup
"""

from alembic import op

revision = "0083_terminal_closure"
down_revision = "0082_closure_product_cleanup"
branch_labels = None
depends_on = None

_TABLE = "crm_organization_closure_executions"
_CONSTRAINT = "ck_org_closure_execution_status"


def _replace_status_constraint(expression: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(_TABLE) as batch_op:
            batch_op.drop_constraint(_CONSTRAINT, type_="check")
            batch_op.create_check_constraint(_CONSTRAINT, expression)
        return

    op.drop_constraint(_CONSTRAINT, _TABLE, type_="check")
    op.create_check_constraint(_CONSTRAINT, _TABLE, expression)


def upgrade() -> None:
    _replace_status_constraint("status IN ('in_progress', 'blocked', 'completed')")


def downgrade() -> None:
    _replace_status_constraint("status IN ('in_progress', 'blocked')")
