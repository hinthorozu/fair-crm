"""Backfill scalar customer communications missing from child tables.

Unblocks Alembic migration 0021 when crm_customers.phone/email/website
exist but child rows were never created (or normalized values differ).

Idempotent: safe to run multiple times.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.modules.customers.application.communication_parsing import (
    emails_from_scalar,
    phones_from_scalar,
    websites_from_scalar,
)
from app.modules.customers.domain.services.normalizers import normalize_phone, normalize_website


def _mask_url(url: str) -> str:
    if "@" in url and ":" in url.split("@")[0]:
        prefix, rest = url.split("@", 1)
        return f"{prefix.rsplit(':', 1)[0]}:***@{rest}"
    return url


def _load_existing_phones(session: Session, customer_id: UUID) -> list[tuple[str, bool]]:
    return session.execute(
        text(
            """
            SELECT phone, is_primary
            FROM crm_customer_phones
            WHERE customer_id = :customer_id
            ORDER BY is_primary DESC, created_at ASC
            """
        ),
        {"customer_id": customer_id},
    ).all()


def _load_existing_emails(session: Session, customer_id: UUID) -> set[str]:
    return set(
        session.execute(
            text("SELECT email FROM crm_customer_emails WHERE customer_id = :customer_id"),
            {"customer_id": customer_id},
        ).scalars()
    )


def _load_existing_websites(session: Session, customer_id: UUID) -> set[str]:
    return set(
        session.execute(
            text("SELECT website FROM crm_customer_websites WHERE customer_id = :customer_id"),
            {"customer_id": customer_id},
        ).scalars()
    )


def backfill_phones(session: Session) -> tuple[int, int]:
    inserted = 0
    skipped = 0
    rows = session.execute(
        text(
            """
            SELECT c.id, c.organization_id, c.phone, c.created_at
            FROM crm_customers c
            WHERE c.phone IS NOT NULL AND trim(c.phone) <> ''
            AND NOT EXISTS (
                SELECT 1 FROM crm_customer_phones p
                WHERE p.customer_id = c.id AND p.phone = c.phone
            )
            """
        )
    ).mappings()

    for row in rows:
        normalized_values = phones_from_scalar(row["phone"])
        if not normalized_values:
            continue

        existing_rows = _load_existing_phones(session, row["id"])
        existing_normalized = {normalize_phone(phone) for phone, _ in existing_rows}
        has_primary = any(is_primary for _, is_primary in existing_rows)

        for phone_value in normalized_values:
            if normalize_phone(phone_value) in existing_normalized:
                skipped += 1
                continue

            is_primary = not has_primary
            session.execute(
                text(
                    """
                    INSERT INTO crm_customer_phones (
                        id, organization_id, customer_id, phone, is_primary, created_at
                    )
                    VALUES (
                        :id, :organization_id, :customer_id, :phone, :is_primary, :created_at
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "organization_id": row["organization_id"],
                    "customer_id": row["id"],
                    "phone": phone_value,
                    "is_primary": is_primary,
                    "created_at": row["created_at"] or datetime.now(tz=UTC),
                },
            )
            inserted += 1
            existing_normalized.add(normalize_phone(phone_value))
            has_primary = has_primary or is_primary

    return inserted, skipped


def backfill_websites(session: Session) -> tuple[int, int]:
    inserted = 0
    skipped = 0
    rows = session.execute(
        text(
            """
            SELECT c.id, c.organization_id, c.website, c.created_at
            FROM crm_customers c
            WHERE c.website IS NOT NULL AND trim(c.website) <> ''
            AND NOT EXISTS (
                SELECT 1 FROM crm_customer_websites w
                WHERE w.customer_id = c.id AND w.website = c.website
            )
            """
        )
    ).mappings()

    for row in rows:
        normalized_values = websites_from_scalar(row["website"])
        if not normalized_values:
            continue

        existing_values = _load_existing_websites(session, row["id"])
        existing_normalized = {normalize_website(value) for value in existing_values}
        has_primary = bool(
            session.execute(
                text(
                    """
                    SELECT 1 FROM crm_customer_websites
                    WHERE customer_id = :customer_id AND is_primary = true
                    LIMIT 1
                    """
                ),
                {"customer_id": row["id"]},
            ).first()
        )

        for website_value in normalized_values:
            if normalize_website(website_value) in existing_normalized:
                skipped += 1
                continue

            is_primary = not has_primary
            session.execute(
                text(
                    """
                    INSERT INTO crm_customer_websites (
                        id, organization_id, customer_id, website, is_primary, created_at
                    )
                    VALUES (
                        :id, :organization_id, :customer_id, :website, :is_primary, :created_at
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "organization_id": row["organization_id"],
                    "customer_id": row["id"],
                    "website": website_value,
                    "is_primary": is_primary,
                    "created_at": row["created_at"] or datetime.now(tz=UTC),
                },
            )
            inserted += 1
            existing_normalized.add(normalize_website(website_value))
            has_primary = has_primary or is_primary

    return inserted, skipped


def backfill_emails(session: Session) -> tuple[int, int]:
    inserted = 0
    skipped = 0

    emails_by_customer: dict[UUID, set[str]] = {}
    primary_by_customer: dict[UUID, bool] = {}
    for customer_id, email in session.execute(
        text("SELECT customer_id, email FROM crm_customer_emails")
    ):
        emails_by_customer.setdefault(customer_id, set()).add(email)
    for (customer_id,) in session.execute(
        text(
            """
            SELECT customer_id
            FROM crm_customer_emails
            WHERE is_primary = true
            """
        )
    ):
        primary_by_customer[customer_id] = True

    rows = session.execute(
        text(
            """
            SELECT id, organization_id, email, created_at
            FROM crm_customers
            WHERE email IS NOT NULL AND trim(email) <> ''
            """
        )
    ).mappings()

    for row in rows:
        try:
            expected_values = emails_from_scalar(row["email"])
        except ValueError:
            continue
        if not expected_values:
            continue

        customer_id = row["id"]
        existing_values = emails_by_customer.setdefault(customer_id, set())
        has_primary = primary_by_customer.get(customer_id, False)

        for email_value in expected_values:
            if email_value in existing_values:
                skipped += 1
                continue

            is_primary = not has_primary
            session.execute(
                text(
                    """
                    INSERT INTO crm_customer_emails (
                        id, organization_id, customer_id, email, is_primary, created_at
                    )
                    VALUES (
                        :id, :organization_id, :customer_id, :email, :is_primary, :created_at
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "organization_id": row["organization_id"],
                    "customer_id": customer_id,
                    "email": email_value,
                    "is_primary": is_primary,
                    "created_at": row["created_at"] or datetime.now(tz=UTC),
                },
            )
            inserted += 1
            existing_values.add(email_value)
            if is_primary:
                primary_by_customer[customer_id] = True
            has_primary = has_primary or is_primary

    return inserted, skipped


def _scalar_columns_exist(session: Session) -> bool:
    return bool(
        session.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'crm_customers' AND column_name = 'phone'
                """
            )
        ).scalar()
    )


def _verify_migration_0021_counts(session: Session) -> dict[str, int]:
    if not _scalar_columns_exist(session):
        return {
            "phone_mismatch": 0,
            "website_mismatch": 0,
            "email_mismatch": 0,
            "note": "scalar columns already dropped (migration 0021 applied)",
        }

    phone_mismatch = 0
    for row in session.execute(
        text(
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
            for value in session.execute(
                text("SELECT phone FROM crm_customer_phones WHERE customer_id = :customer_id"),
                {"customer_id": row["id"]},
            ).scalars()
        }
        if any(normalize_phone(phone) not in actual for phone in expected):
            phone_mismatch += 1

    website_mismatch = 0
    for row in session.execute(
        text(
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
            for value in session.execute(
                text("SELECT website FROM crm_customer_websites WHERE customer_id = :customer_id"),
                {"customer_id": row["id"]},
            ).scalars()
        }
        if any(normalize_website(website) not in actual for website in expected):
            website_mismatch += 1

    emails_by_customer: dict[UUID, set[str]] = {}
    for customer_id, email in session.execute(text("SELECT customer_id, email FROM crm_customer_emails")):
        emails_by_customer.setdefault(customer_id, set()).add(email)

    email_mismatches = 0
    for row in session.execute(
        text(
            """
            SELECT id, email FROM crm_customers
            WHERE email IS NOT NULL AND trim(email) <> ''
            """
        )
    ).mappings():
        try:
            expected = emails_from_scalar(row["email"])
        except ValueError:
            continue
        actual = emails_by_customer.get(row["id"], set())
        for email in expected:
            if email not in actual:
                email_mismatches += 1

    return {
        "phone_mismatch": phone_mismatch,
        "website_mismatch": website_mismatch,
        "email_mismatch": email_mismatches,
    }


def main() -> int:
    settings = get_settings()
    print("DATABASE_URL", _mask_url(settings.database_url))

    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        if not _scalar_columns_exist(session):
            print("scalar communication columns already dropped; backfill not required")
            return 0

        before = _verify_migration_0021_counts(session)
        print("before", before)

        phone_inserted, phone_skipped = backfill_phones(session)
        website_inserted, website_skipped = backfill_websites(session)
        email_inserted, email_skipped = backfill_emails(session)
        session.commit()

        after = _verify_migration_0021_counts(session)
        print(
            "inserted",
            {
                "phones": phone_inserted,
                "websites": website_inserted,
                "emails": email_inserted,
            },
        )
        print(
            "skipped",
            {
                "phones": phone_skipped,
                "websites": website_skipped,
                "emails": email_skipped,
            },
        )
        print("after", after)

        if after["phone_mismatch"] or after["website_mismatch"] or after["email_mismatch"]:
            print("ERROR: migration 0021 verification would still fail")
            return 1

        print("Backfill completed successfully")
        return 0
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
