"""Customer communication child tables (phones, emails, websites).

Revision ID: 0020_customer_communications
Revises: 0019_do_dataset_group_by
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0020_customer_communications"
down_revision: Union[str, None] = "0019_do_dataset_group_by"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _split_emails(value: str | None) -> list[str]:
    if not value:
        return []
    text = value.replace(",", ";")
    emails: list[str] = []
    seen: set[str] = set()
    for part in text.split(";"):
        email = part.strip().lower()
        if not email or email in seen:
            continue
        seen.add(email)
        emails.append(email)
    return emails


def upgrade() -> None:
    op.create_table(
        "crm_customer_phones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["crm_customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_customer_phones_customer_id", "crm_customer_phones", ["customer_id"])
    op.create_index(
        "ix_crm_customer_phones_organization_id",
        "crm_customer_phones",
        ["organization_id"],
    )

    op.create_table(
        "crm_customer_emails",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["crm_customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_customer_emails_customer_id", "crm_customer_emails", ["customer_id"])
    op.create_index(
        "ix_crm_customer_emails_organization_id",
        "crm_customer_emails",
        ["organization_id"],
    )
    op.create_index("ix_crm_customer_emails_email", "crm_customer_emails", ["email"])

    op.create_table(
        "crm_customer_websites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("website", sa.String(length=255), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["crm_customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_customer_websites_customer_id", "crm_customer_websites", ["customer_id"])
    op.create_index(
        "ix_crm_customer_websites_organization_id",
        "crm_customer_websites",
        ["organization_id"],
    )

    connection = op.get_bind()
    customers = connection.execute(
        sa.text(
            """
            SELECT id, organization_id, phone, email, website, created_at
            FROM crm_customers
            """
        )
    ).mappings()

    phone_rows: list[dict] = []
    email_rows: list[dict] = []
    website_rows: list[dict] = []

    for customer in customers:
        created_at = customer["created_at"] or datetime.now(tz=UTC)
        customer_id = customer["id"]
        organization_id = customer["organization_id"]

        phone = customer["phone"]
        if phone:
            phone_rows.append(
                {
                    "id": uuid.uuid4(),
                    "organization_id": organization_id,
                    "customer_id": customer_id,
                    "phone": phone,
                    "is_primary": True,
                    "created_at": created_at,
                }
            )

        emails = _split_emails(customer["email"])
        for index, email in enumerate(emails):
            email_rows.append(
                {
                    "id": uuid.uuid4(),
                    "organization_id": organization_id,
                    "customer_id": customer_id,
                    "email": email,
                    "is_primary": index == 0,
                    "created_at": created_at,
                }
            )

        website = customer["website"]
        if website:
            website_rows.append(
                {
                    "id": uuid.uuid4(),
                    "organization_id": organization_id,
                    "customer_id": customer_id,
                    "website": website,
                    "is_primary": True,
                    "created_at": created_at,
                }
            )

    if phone_rows:
        op.bulk_insert(
            sa.table(
                "crm_customer_phones",
                sa.column("id", sa.Uuid()),
                sa.column("organization_id", sa.Uuid()),
                sa.column("customer_id", sa.Uuid()),
                sa.column("phone", sa.String()),
                sa.column("is_primary", sa.Boolean()),
                sa.column("created_at", sa.DateTime(timezone=True)),
            ),
            phone_rows,
        )

    if email_rows:
        op.bulk_insert(
            sa.table(
                "crm_customer_emails",
                sa.column("id", sa.Uuid()),
                sa.column("organization_id", sa.Uuid()),
                sa.column("customer_id", sa.Uuid()),
                sa.column("email", sa.String()),
                sa.column("is_primary", sa.Boolean()),
                sa.column("created_at", sa.DateTime(timezone=True)),
            ),
            email_rows,
        )

    if website_rows:
        op.bulk_insert(
            sa.table(
                "crm_customer_websites",
                sa.column("id", sa.Uuid()),
                sa.column("organization_id", sa.Uuid()),
                sa.column("customer_id", sa.Uuid()),
                sa.column("website", sa.String()),
                sa.column("is_primary", sa.Boolean()),
                sa.column("created_at", sa.DateTime(timezone=True)),
            ),
            website_rows,
        )


def downgrade() -> None:
    op.drop_index("ix_crm_customer_websites_organization_id", table_name="crm_customer_websites")
    op.drop_index("ix_crm_customer_websites_customer_id", table_name="crm_customer_websites")
    op.drop_table("crm_customer_websites")

    op.drop_index("ix_crm_customer_emails_email", table_name="crm_customer_emails")
    op.drop_index("ix_crm_customer_emails_organization_id", table_name="crm_customer_emails")
    op.drop_index("ix_crm_customer_emails_customer_id", table_name="crm_customer_emails")
    op.drop_table("crm_customer_emails")

    op.drop_index("ix_crm_customer_phones_organization_id", table_name="crm_customer_phones")
    op.drop_index("ix_crm_customer_phones_customer_id", table_name="crm_customer_phones")
    op.drop_table("crm_customer_phones")
