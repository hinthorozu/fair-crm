#!/usr/bin/env python3
"""One-time maintenance: delete customers with no fair participation.

Internal admin use only. Finds customers with zero rows in
crm_customer_fair_participations and physically deletes them.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import bootstrap

bootstrap()


def _configure_stdio_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def main() -> int:
    _configure_stdio_utf8()

    from app.core.config import get_settings
    from app.db.session import SessionLocal
    from app.modules.customers.infrastructure.persistence.models import CustomerModel
    from app.modules.participations.infrastructure.persistence.models import (
        CustomerFairParticipationModel,
    )

    get_settings.cache_clear()
    settings = get_settings()
    db = SessionLocal()

    deleted = 0
    failed = 0
    total_found = 0

    try:
        customers = (
            db.query(CustomerModel)
            .outerjoin(
                CustomerFairParticipationModel,
                CustomerModel.id == CustomerFairParticipationModel.customer_id,
            )
            .filter(CustomerFairParticipationModel.id.is_(None))
            .order_by(CustomerModel.display_name.asc(), CustomerModel.id.asc())
            .all()
        )
        total_found = len(customers)

        for customer in customers:
            participation_count = (
                db.query(CustomerFairParticipationModel)
                .filter(CustomerFairParticipationModel.customer_id == customer.id)
                .count()
            )
            if participation_count > 0:
                failed += 1
                print(
                    f"FAILED  {customer.id}  {customer.display_name}  "
                    f"(has_fair_participation:{participation_count})",
                    file=sys.stderr,
                )
                continue

            try:
                db.delete(customer)
                deleted += 1
                print(f"DELETE  {customer.id}  {customer.display_name}")
            except Exception as exc:
                failed += 1
                print(
                    f"FAILED  {customer.id}  {customer.display_name}  ({exc})",
                    file=sys.stderr,
                )

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print()
    print("Delete customers without fair participation")
    print(f"  Database: {settings.database_url.split('@')[-1]}")
    print(f"  Total customers found: {total_found}")
    print(f"  Total deleted: {deleted}")
    print(f"  Total failed: {failed}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
