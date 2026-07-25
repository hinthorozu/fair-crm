"""Evolve smtp_accounts into provider-aware email_accounts (A1).

Revision ID: 0060_email_accounts_provider_aware
Revises: 0059_fair_email_outbox_fair_name
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0060_email_accounts_provider_aware"
down_revision: Union[str, None] = "0059_fair_email_outbox_fair_name"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # --- email_accounts from smtp_accounts ---
    op.rename_table("smtp_accounts", "email_accounts")

    op.add_column(
        "email_accounts",
        sa.Column("account_type", sa.String(length=32), nullable=False, server_default="smtp"),
    )
    op.add_column(
        "email_accounts",
        sa.Column("provider_key", sa.String(length=64), nullable=True),
    )

    op.create_table(
        "email_account_smtp_configs",
        sa.Column("email_account_id", sa.Uuid(), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("password", sa.Text(), nullable=True),
        sa.Column(
            "encryption_type",
            sa.String(length=32),
            nullable=False,
            server_default="starttls",
        ),
        sa.ForeignKeyConstraint(
            ["email_account_id"],
            ["email_accounts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("email_account_id"),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO email_account_smtp_configs
                (email_account_id, host, port, username, password, encryption_type)
            SELECT id, host, port, username, password, encryption_type
            FROM email_accounts
            """
        )
    )

    if dialect == "sqlite":
        with op.batch_alter_table("email_accounts") as batch_op:
            batch_op.drop_column("host")
            batch_op.drop_column("port")
            batch_op.drop_column("username")
            batch_op.drop_column("password")
            batch_op.drop_column("encryption_type")
    else:
        op.drop_column("email_accounts", "host")
        op.drop_column("email_accounts", "port")
        op.drop_column("email_accounts", "username")
        op.drop_column("email_accounts", "password")
        op.drop_column("email_accounts", "encryption_type")

    # Rename indexes (best-effort; names may differ by dialect)
    _rename_index(
        "ix_smtp_accounts_organization_id",
        "ix_email_accounts_organization_id",
        "email_accounts",
        ["organization_id"],
    )
    _rename_index(
        "ix_smtp_accounts_is_default",
        "ix_email_accounts_is_default",
        "email_accounts",
        ["is_default"],
    )
    _rename_index(
        "ix_smtp_accounts_is_active",
        "ix_email_accounts_is_active",
        "email_accounts",
        ["is_active"],
    )

    op.drop_index("uq_smtp_accounts_org_default", table_name="email_accounts")
    op.create_index(
        "uq_email_accounts_org_default",
        "email_accounts",
        ["organization_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND is_default = true"),
        sqlite_where=sa.text("deleted_at IS NULL AND is_default = 1"),
    )

    # --- FK column renames ---
    _rename_column("crm_fair_email_batches", "smtp_account_id", "email_account_id")
    _rename_column("mail_send_operations", "smtp_account_id", "email_account_id")


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    _rename_column("mail_send_operations", "email_account_id", "smtp_account_id")
    _rename_column("crm_fair_email_batches", "email_account_id", "smtp_account_id")

    op.drop_index("uq_email_accounts_org_default", table_name="email_accounts")
    op.create_index(
        "uq_smtp_accounts_org_default",
        "email_accounts",
        ["organization_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND is_default = true"),
        sqlite_where=sa.text("deleted_at IS NULL AND is_default = 1"),
    )

    if dialect == "sqlite":
        with op.batch_alter_table("email_accounts") as batch_op:
            batch_op.add_column(sa.Column("host", sa.String(length=255), nullable=True))
            batch_op.add_column(sa.Column("port", sa.Integer(), nullable=True))
            batch_op.add_column(sa.Column("username", sa.String(length=255), nullable=True))
            batch_op.add_column(sa.Column("password", sa.Text(), nullable=True))
            batch_op.add_column(
                sa.Column(
                    "encryption_type",
                    sa.String(length=32),
                    nullable=False,
                    server_default="starttls",
                )
            )
    else:
        op.add_column("email_accounts", sa.Column("host", sa.String(length=255), nullable=True))
        op.add_column("email_accounts", sa.Column("port", sa.Integer(), nullable=True))
        op.add_column(
            "email_accounts",
            sa.Column("username", sa.String(length=255), nullable=True),
        )
        op.add_column("email_accounts", sa.Column("password", sa.Text(), nullable=True))
        op.add_column(
            "email_accounts",
            sa.Column(
                "encryption_type",
                sa.String(length=32),
                nullable=False,
                server_default="starttls",
            ),
        )

    op.execute(
        sa.text(
            """
            UPDATE email_accounts AS a
            SET
                host = c.host,
                port = c.port,
                username = c.username,
                password = c.password,
                encryption_type = c.encryption_type
            FROM email_account_smtp_configs AS c
            WHERE c.email_account_id = a.id
            """
            if dialect != "sqlite"
            else """
            UPDATE email_accounts
            SET
                host = (
                    SELECT c.host FROM email_account_smtp_configs c
                    WHERE c.email_account_id = email_accounts.id
                ),
                port = (
                    SELECT c.port FROM email_account_smtp_configs c
                    WHERE c.email_account_id = email_accounts.id
                ),
                username = (
                    SELECT c.username FROM email_account_smtp_configs c
                    WHERE c.email_account_id = email_accounts.id
                ),
                password = (
                    SELECT c.password FROM email_account_smtp_configs c
                    WHERE c.email_account_id = email_accounts.id
                ),
                encryption_type = (
                    SELECT c.encryption_type FROM email_account_smtp_configs c
                    WHERE c.email_account_id = email_accounts.id
                )
            """
        )
    )

    if dialect == "sqlite":
        with op.batch_alter_table("email_accounts") as batch_op:
            batch_op.drop_column("provider_key")
            batch_op.drop_column("account_type")
    else:
        op.drop_column("email_accounts", "provider_key")
        op.drop_column("email_accounts", "account_type")

    op.drop_table("email_account_smtp_configs")
    op.rename_table("email_accounts", "smtp_accounts")


def _rename_index(old_name: str, new_name: str, table: str, columns: list[str]) -> None:
    try:
        op.drop_index(old_name, table_name=table)
    except Exception:
        pass
    try:
        op.create_index(new_name, table, columns)
    except Exception:
        pass


def _rename_column(table: str, old_name: str, new_name: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(old_name, new_column_name=new_name)
    else:
        op.alter_column(table, old_name, new_column_name=new_name)
