"""Import row customer/participation links: SET NULL on target delete."""

from typing import Sequence, Union

from alembic import op

revision: str = "0013_import_row_customer_fks"
down_revision: Union[str, None] = "0012_customer_cascade_delete"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _null_orphan_customer_refs() -> None:
    op.execute(
        """
        UPDATE crm_import_rows
        SET match_customer_id = NULL
        WHERE match_customer_id IS NOT NULL
          AND match_customer_id NOT IN (SELECT id FROM crm_customers)
        """
    )
    op.execute(
        """
        UPDATE crm_import_rows
        SET created_customer_id = NULL
        WHERE created_customer_id IS NOT NULL
          AND created_customer_id NOT IN (SELECT id FROM crm_customers)
        """
    )
    op.execute(
        """
        UPDATE crm_import_rows
        SET updated_customer_id = NULL
        WHERE updated_customer_id IS NOT NULL
          AND updated_customer_id NOT IN (SELECT id FROM crm_customers)
        """
    )


def _null_orphan_participation_refs() -> None:
    op.execute(
        """
        UPDATE crm_import_rows
        SET match_participation_id = NULL
        WHERE match_participation_id IS NOT NULL
          AND match_participation_id NOT IN (SELECT id FROM crm_customer_fair_participations)
        """
    )
    op.execute(
        """
        UPDATE crm_import_rows
        SET created_participation_id = NULL
        WHERE created_participation_id IS NOT NULL
          AND created_participation_id NOT IN (SELECT id FROM crm_customer_fair_participations)
        """
    )
    op.execute(
        """
        UPDATE crm_import_rows
        SET updated_participation_id = NULL
        WHERE updated_participation_id IS NOT NULL
          AND updated_participation_id NOT IN (SELECT id FROM crm_customer_fair_participations)
        """
    )


def _add_fk(constraint: str, local_col: str, remote_table: str) -> None:
    op.create_foreign_key(
        constraint,
        "crm_import_rows",
        remote_table,
        [local_col],
        ["id"],
        ondelete="SET NULL",
    )


def upgrade() -> None:
    _null_orphan_customer_refs()
    _null_orphan_participation_refs()

    _add_fk("crm_import_rows_match_customer_id_fkey", "match_customer_id", "crm_customers")
    _add_fk("crm_import_rows_created_customer_id_fkey", "created_customer_id", "crm_customers")
    _add_fk("crm_import_rows_updated_customer_id_fkey", "updated_customer_id", "crm_customers")
    _add_fk(
        "crm_import_rows_match_participation_id_fkey",
        "match_participation_id",
        "crm_customer_fair_participations",
    )
    _add_fk(
        "crm_import_rows_created_participation_id_fkey",
        "created_participation_id",
        "crm_customer_fair_participations",
    )
    _add_fk(
        "crm_import_rows_updated_participation_id_fkey",
        "updated_participation_id",
        "crm_customer_fair_participations",
    )


def downgrade() -> None:
    for constraint in (
        "crm_import_rows_updated_participation_id_fkey",
        "crm_import_rows_created_participation_id_fkey",
        "crm_import_rows_match_participation_id_fkey",
        "crm_import_rows_updated_customer_id_fkey",
        "crm_import_rows_created_customer_id_fkey",
        "crm_import_rows_match_customer_id_fkey",
    ):
        op.drop_constraint(constraint, "crm_import_rows", type_="foreignkey")
