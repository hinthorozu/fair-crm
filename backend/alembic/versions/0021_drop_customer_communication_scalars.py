"""Drop legacy phone/email/website columns from crm_customers.

Revision ID: 0021_drop_customer_communication_scalars
Revises: 0020_customer_communications
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0021_drop_customer_communication_scalars"
down_revision: Union[str, None] = "0020_customer_communications"
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


def _verify_backfill(connection) -> None:
    from app.modules.customers.application.communication_parsing import (
        emails_from_scalar,
        phones_from_scalar,
        websites_from_scalar,
    )
    from app.modules.customers.domain.services.normalizers import normalize_phone, normalize_website

    phone_mismatch = 0
    phone_samples: list[str] = []
    for row in connection.execute(
        sa.text(
            """
            SELECT id, phone FROM crm_customers
            WHERE phone IS NOT NULL AND trim(phone) <> ''
            """
        )
    ).mappings():
        expected = phones_from_scalar(row["phone"])
        if not expected:
            continue
        actual = {
            normalize_phone(value)
            for value in connection.execute(
                sa.text("SELECT phone FROM crm_customer_phones WHERE customer_id = :customer_id"),
                {"customer_id": row["id"]},
            ).scalars()
        }
        missing = [phone for phone in expected if normalize_phone(phone) not in actual]
        if missing:
            phone_mismatch += 1
            if len(phone_samples) < 5:
                phone_samples.append(
                    f"customer_id={row['id']} missing normalized phone(s)={missing!r}"
                )
    if phone_mismatch:
        detail = "; ".join(phone_samples)
        raise RuntimeError(
            f"Cannot drop crm_customers.phone: {phone_mismatch} row(s) have scalar phone "
            f"values missing from crm_customer_phones. Examples: {detail}"
        )

    website_mismatch = 0
    website_samples: list[str] = []
    for row in connection.execute(
        sa.text(
            """
            SELECT id, website FROM crm_customers
            WHERE website IS NOT NULL AND trim(website) <> ''
            """
        )
    ).mappings():
        expected = websites_from_scalar(row["website"])
        if not expected:
            continue
        actual = {
            normalize_website(value)
            for value in connection.execute(
                sa.text("SELECT website FROM crm_customer_websites WHERE customer_id = :customer_id"),
                {"customer_id": row["id"]},
            ).scalars()
        }
        missing = [website for website in expected if normalize_website(website) not in actual]
        if missing:
            website_mismatch += 1
            if len(website_samples) < 5:
                website_samples.append(
                    f"customer_id={row['id']} missing normalized website(s)={missing!r}"
                )
    if website_mismatch:
        detail = "; ".join(website_samples)
        raise RuntimeError(
            f"Cannot drop crm_customers.website: {website_mismatch} row(s) have scalar website "
            f"values missing from crm_customer_websites. Examples: {detail}"
        )

    email_rows = connection.execute(
        sa.text(
            """
            SELECT id, email FROM crm_customers
            WHERE email IS NOT NULL AND trim(email) <> ''
            """
        )
    ).mappings()

    email_mismatches = 0
    sample: list[str] = []
    for row in email_rows:
        customer_id = row["id"]
        try:
            expected = emails_from_scalar(row["email"])
        except ValueError:
            expected = _split_emails(row["email"])
        if not expected:
            continue
        actual = {
            value
            for value in connection.execute(
                sa.text(
                    "SELECT email FROM crm_customer_emails WHERE customer_id = :customer_id"
                ),
                {"customer_id": customer_id},
            ).scalars()
        }
        for email in expected:
            if email not in actual:
                email_mismatches += 1
                if len(sample) < 5:
                    sample.append(f"customer_id={customer_id} missing email={email!r}")
    if email_mismatches:
        detail = "; ".join(sample)
        raise RuntimeError(
            f"Cannot drop crm_customers.email: {email_mismatches} scalar email value(s) "
            f"missing from crm_customer_emails. Examples: {detail}"
        )


def upgrade() -> None:
    connection = op.get_bind()
    _verify_backfill(connection)
    op.drop_column("crm_customers", "phone")
    op.drop_column("crm_customers", "email")
    op.drop_column("crm_customers", "website")


def downgrade() -> None:
    op.add_column("crm_customers", sa.Column("website", sa.String(length=255), nullable=True))
    op.add_column("crm_customers", sa.Column("email", sa.String(length=255), nullable=True))
    op.add_column("crm_customers", sa.Column("phone", sa.String(length=50), nullable=True))
