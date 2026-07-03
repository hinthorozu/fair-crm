#!/usr/bin/env python3
"""One-time duplicate analysis across all customers (read-only).

Builds potential duplicate groups using Import Wizard matching logic and
exports an Excel report. Does not modify the database.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import REPORTS_DIR, bootstrap

bootstrap()

from app.modules.customers.application.duplicate_group_analysis import (
    CLASS_MANUAL,
    CLASS_POSSIBLE,
    CLASS_PROBABLE,
    CLASS_STRONG,
    CustomerRecord,
    best_edge_in_group,
    build_org_groups,
    classify_score,
    customer_norm_key,
    load_fair_metadata,
    normalize_email_key,
    normalize_phone_key,
)

OUTPUT_COLUMNS = (
    "duplicate_group_id",
    "match_score",
    "customer_id",
    "company_name",
    "normalized_company_name",
    "phone",
    "email",
    "website",
    "city",
    "country",
    "status",
    "fair_count",
    "first_fair_name",
    "created_at",
    "classification",
    "duplicate_reason",
)


def _configure_stdio_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def _excel_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


def _default_output_path() -> Path:
    stamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR / f"customer_duplicates_{stamp}.xlsx"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze all customers for potential duplicate groups (read-only)."
    )
    parser.add_argument(
        "--organization-id",
        type=UUID,
        default=None,
        help="Limit analysis to one organization (default: all organizations).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output .xlsx path (default: scripts/maintenance/reports/customer_duplicates_<timestamp>.xlsx).",
    )
    return parser.parse_args()


def main() -> int:
    _configure_stdio_utf8()
    args = _parse_args()

    from openpyxl import Workbook
    from sqlalchemy.orm import Session

    from app.core.config import get_settings
    from app.db.session import SessionLocal
    from app.modules.customers.infrastructure.persistence.models import CustomerModel

    get_settings.cache_clear()
    settings = get_settings()
    output_path = (args.output or _default_output_path()).resolve()

    db: Session = SessionLocal()
    try:
        customer_query = db.query(CustomerModel).order_by(
            CustomerModel.organization_id.asc(),
            CustomerModel.display_name.asc(),
            CustomerModel.id.asc(),
        )
        if args.organization_id is not None:
            customer_query = customer_query.filter(
                CustomerModel.organization_id == args.organization_id
            )
        models = customer_query.all()
        fair_counts, first_fair_names = load_fair_metadata(db)

        records: list[CustomerRecord] = []
        for model in models:
            records.append(
                CustomerRecord(
                    id=model.id,
                    organization_id=model.organization_id,
                    company_name=model.display_name,
                    normalized_company_name=model.normalized_name,
                    phone=model.phone,
                    email=model.email,
                    website=model.website,
                    city=model.city,
                    country=model.country,
                    status=model.status,
                    created_at=model.created_at,
                    norm_key=customer_norm_key(model.display_name, model.normalized_name),
                    email_key=normalize_email_key(model.email),
                    phone_key=normalize_phone_key(model.phone),
                    fair_count=fair_counts.get(model.id, 0),
                    first_fair_name=first_fair_names.get(model.id),
                )
            )

        by_org: dict[UUID, list[CustomerRecord]] = defaultdict(list)
        for record in records:
            by_org[record.organization_id].append(record)

        all_groups: list[tuple[str, list[UUID], object, dict[UUID, CustomerRecord]]] = []
        group_serial = 0
        for _org_id, org_records in sorted(by_org.items(), key=lambda item: str(item[0])):
            org_groups, builder = build_org_groups(org_records)
            record_map = {record.id: record for record in org_records}
            for _root, members in sorted(
                org_groups.items(),
                key=lambda item: (len(item[1]), str(item[1][0])),
                reverse=True,
            ):
                group_serial += 1
                group_id = f"dup_grp_{group_serial:05d}"
                all_groups.append((group_id, members, builder, record_map))

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "customer_duplicates"
        sheet.append(list(OUTPUT_COLUMNS))

        classification_counts: Counter[str] = Counter()

        for group_id, member_ids, builder, record_map in all_groups:
            member_set = set(member_ids)
            for customer_id in member_ids:
                record = record_map[customer_id]
                edge = best_edge_in_group(customer_id, member_set, builder.edge_scores)
                classification = classify_score(edge.score)
                classification_counts[classification] += 1
                sheet.append(
                    [
                        group_id,
                        edge.score if edge.score > 0 else None,
                        str(record.id),
                        record.company_name,
                        record.normalized_company_name,
                        record.phone,
                        record.email,
                        record.website,
                        record.city,
                        record.country,
                        record.status,
                        record.fair_count,
                        record.first_fair_name,
                        _excel_datetime(record.created_at),
                        classification,
                        edge.reason,
                    ]
                )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        workbook.save(output_path)
    finally:
        db.close()

    customers_in_groups = sum(len(members) for _, members, _, _ in all_groups)
    print("Customer duplicate analysis report")
    print(f"  Database: {settings.database_url.split('@')[-1]}")
    if args.organization_id is not None:
        print(f"  Organization filter: {args.organization_id}")
    print(f"  Total customers analyzed: {len(records)}")
    print(f"  Total duplicate groups: {len(all_groups)}")
    print(f"  Total customers inside duplicate groups: {customers_in_groups}")
    print(f"  {CLASS_STRONG}: {classification_counts.get(CLASS_STRONG, 0)}")
    print(f"  {CLASS_PROBABLE}: {classification_counts.get(CLASS_PROBABLE, 0)}")
    print(f"  {CLASS_POSSIBLE}: {classification_counts.get(CLASS_POSSIBLE, 0)}")
    print(f"  {CLASS_MANUAL}: {classification_counts.get(CLASS_MANUAL, 0)}")
    print(f"  Excel output: {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
