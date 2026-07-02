"""Customer hard-delete cascades to contacts, activities, participations."""

from typing import Sequence, Union

from alembic import op

revision: str = "0012_customer_cascade_delete"
down_revision: Union[str, None] = "0011_system_backups"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _replace_fk(
    *,
    table: str,
    constraint: str,
    local_cols: list[str],
    remote_table: str,
    remote_cols: list[str],
    ondelete: str,
) -> None:
    op.drop_constraint(constraint, table, type_="foreignkey")
    op.create_foreign_key(
        constraint,
        table,
        remote_table,
        local_cols,
        remote_cols,
        ondelete=ondelete,
    )


def upgrade() -> None:
    # Customer removed (e.g. Navicat hard delete) → child rows removed automatically.
    _replace_fk(
        table="crm_contacts",
        constraint="crm_contacts_customer_id_fkey",
        local_cols=["customer_id"],
        remote_table="crm_customers",
        remote_cols=["id"],
        ondelete="CASCADE",
    )
    _replace_fk(
        table="crm_activities",
        constraint="crm_activities_customer_id_fkey",
        local_cols=["customer_id"],
        remote_table="crm_customers",
        remote_cols=["id"],
        ondelete="CASCADE",
    )
    _replace_fk(
        table="crm_customer_fair_participations",
        constraint="crm_customer_fair_participations_customer_id_fkey",
        local_cols=["customer_id"],
        remote_table="crm_customers",
        remote_cols=["id"],
        ondelete="CASCADE",
    )

    # Contact removed alone → clear optional references (customer delete already cascades children).
    _replace_fk(
        table="crm_activities",
        constraint="crm_activities_contact_id_fkey",
        local_cols=["contact_id"],
        remote_table="crm_contacts",
        remote_cols=["id"],
        ondelete="SET NULL",
    )
    _replace_fk(
        table="crm_customer_fair_participations",
        constraint="crm_customer_fair_participations_primary_contact_id_fkey",
        local_cols=["primary_contact_id"],
        remote_table="crm_contacts",
        remote_cols=["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    _replace_fk(
        table="crm_customer_fair_participations",
        constraint="crm_customer_fair_participations_primary_contact_id_fkey",
        local_cols=["primary_contact_id"],
        remote_table="crm_contacts",
        remote_cols=["id"],
        ondelete="RESTRICT",
    )
    _replace_fk(
        table="crm_activities",
        constraint="crm_activities_contact_id_fkey",
        local_cols=["contact_id"],
        remote_table="crm_contacts",
        remote_cols=["id"],
        ondelete="RESTRICT",
    )
    _replace_fk(
        table="crm_customer_fair_participations",
        constraint="crm_customer_fair_participations_customer_id_fkey",
        local_cols=["customer_id"],
        remote_table="crm_customers",
        remote_cols=["id"],
        ondelete="RESTRICT",
    )
    _replace_fk(
        table="crm_activities",
        constraint="crm_activities_customer_id_fkey",
        local_cols=["customer_id"],
        remote_table="crm_customers",
        remote_cols=["id"],
        ondelete="RESTRICT",
    )
    _replace_fk(
        table="crm_contacts",
        constraint="crm_contacts_customer_id_fkey",
        local_cols=["customer_id"],
        remote_table="crm_customers",
        remote_cols=["id"],
        ondelete="RESTRICT",
    )
