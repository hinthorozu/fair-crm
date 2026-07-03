#!/usr/bin/env python3
"""Export duplicate-group customers with fair participations (read-only).

One row per customer participation. Customers without participations appear once
with empty fair columns. Does not modify the database.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import ANALYSIS_DIR, EXPORTS_DIR, bootstrap

bootstrap()

CUSTOMER_EXPORT_COLUMNS = (
    "customer_id",
    "organization_id",
    "company_name",
    "legal_name",
    "trade_name",
    "normalized_company_name",
    "customer_type",
    "status",
    "website",
    "phone",
    "email",
    "tax_number",
    "tax_office",
    "country",
    "city",
    "district",
    "address",
    "description",
    "source",
    "created_at",
    "updated_at",
    "deleted_at",
    "archived_from_status",
)

EXTRA_COLUMNS = (
    "duplicate_group_id",
    "match_score",
    "duplicate_reason",
    "fair_name",
    "fair_year",
    "hall",
    "stand",
)

OUTPUT_COLUMNS = CUSTOMER_EXPORT_COLUMNS + EXTRA_COLUMNS


@dataclass(frozen=True)
class ParticipationRow:
    fair_name: str | None
    fair_year: int | None
    hall: str | None
    stand: str | None


def _load_duplicate_module():
    module_path = ANALYSIS_DIR / "report_customer_duplicates.py"
    module_name = "maintenance_report_customer_duplicates"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load duplicate analysis module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


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


def _fair_year(start_date: date | None, end_date: date | None) -> int | None:
    if start_date is not None:
        return start_date.year
    if end_date is not None:
        return end_date.year
    return None


def _default_output_path() -> Path:
    stamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return EXPORTS_DIR / f"duplicate_group_customers_{stamp}.xlsx"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export duplicate-group customers with participations to Excel."
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
        help="Output .xlsx path (default: scripts/maintenance/exports/duplicate_group_customers_<timestamp>.xlsx).",
    )
    return parser.parse_args()


def _customer_export_values(model) -> list[object]:
    return [
        str(model.id),
        str(model.organization_id),
        model.display_name,
        model.legal_name,
        model.trade_name,
        model.normalized_name,
        model.customer_type,
        model.status,
        model.website,
        model.phone,
        model.email,
        model.tax_number,
        model.tax_office,
        model.country,
        model.city,
        model.district,
        model.address,
        model.description,
        model.source,
        _excel_datetime(model.created_at),
        _excel_datetime(model.updated_at),
        _excel_datetime(model.deleted_at),
        model.archived_from_status,
    ]


def _load_participations(db, customer_ids: list[UUID]) -> dict[UUID, list[ParticipationRow]]:
    from app.modules.fairs.infrastructure.persistence.models import FairModel
    from app.modules.participations.infrastructure.persistence.models import (
        CustomerFairParticipationModel,
    )

    if not customer_ids:
        return {}

    rows = (
        db.query(
            CustomerFairParticipationModel.customer_id,
            CustomerFairParticipationModel.hall,
            CustomerFairParticipationModel.stand,
            FairModel.name,
            FairModel.start_date,
            FairModel.end_date,
        )
        .join(FairModel, FairModel.id == CustomerFairParticipationModel.fair_id)
        .filter(CustomerFairParticipationModel.customer_id.in_(customer_ids))
        .order_by(
            CustomerFairParticipationModel.customer_id.asc(),
            FairModel.start_date.asc().nulls_last(),
            FairModel.name.asc(),
            CustomerFairParticipationModel.created_at.asc(),
        )
        .all()
    )

    by_customer: dict[UUID, list[ParticipationRow]] = defaultdict(list)
    for customer_id, hall, stand, fair_name, start_date, end_date in rows:
        by_customer[customer_id].append(
            ParticipationRow(
                fair_name=fair_name,
                fair_year=_fair_year(start_date, end_date),
                hall=hall,
                stand=stand,
            )
        )
    return dict(by_customer)


def main() -> int:
    _configure_stdio_utf8()
    args = _parse_args()
    dup = _load_duplicate_module()

    from openpyxl import Workbook
    from sqlalchemy.orm import Session

    from app.core.config import get_settings
    from app.db.session import SessionLocal
    from app.modules.customers.infrastructure.persistence.models import CustomerModel

    get_settings.cache_clear()
    settings = get_settings()
    output_path = (args.output or _default_output_path()).resolve()

    db: Session = SessionLocal()
    export_rows: list[tuple[tuple, list[object]]] = []
    all_groups: list[tuple[str, list[UUID], object, dict]] = []
    customers_exported: set[UUID] = set()

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
        model_by_id = {model.id: model for model in models}

        records: list = []
        for model in models:
            records.append(
                dup.CustomerRecord(
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
                    norm_key=dup._customer_norm_key(model.display_name, model.normalized_name),
                    email_key=dup._normalize_email_key(model.email),
                    phone_key=dup._normalize_phone_key(model.phone),
                )
            )

        by_org: dict[UUID, list] = defaultdict(list)
        for record in records:
            by_org[record.organization_id].append(record)

        group_serial = 0
        member_ids: list[UUID] = []
        for _org_id, org_records in sorted(by_org.items(), key=lambda item: str(item[0])):
            org_groups, builder = dup._build_org_groups(org_records)
            record_map = {record.id: record for record in org_records}
            for _root, members in sorted(
                org_groups.items(),
                key=lambda item: (len(item[1]), str(item[1][0])),
                reverse=True,
            ):
                group_serial += 1
                group_id = f"dup_grp_{group_serial:05d}"
                all_groups.append((group_id, members, builder, record_map))
                member_ids.extend(members)

        participations_by_customer = _load_participations(db, list(set(member_ids)))

        for group_id, members, builder, _record_map in all_groups:
            member_set = set(members)
            for customer_id in members:
                model = model_by_id.get(customer_id)
                if model is None:
                    continue

                customers_exported.add(customer_id)
                edge = dup._best_edge_in_group(customer_id, member_set, builder.edge_scores)
                match_score = edge.score if edge.score > 0 else None
                duplicate_reason = edge.reason
                customer_values = _customer_export_values(model)
                participation_rows = participations_by_customer.get(customer_id)

                if not participation_rows:
                    sort_key = (group_id, model.display_name.lower(), -1, "")
                    export_rows.append(
                        (
                            sort_key,
                            customer_values
                            + [
                                group_id,
                                match_score,
                                duplicate_reason,
                                None,
                                None,
                                None,
                                None,
                            ],
                        )
                    )
                    continue

                for participation in participation_rows:
                    fair_year = participation.fair_year
                    sort_key = (
                        group_id,
                        model.display_name.lower(),
                        fair_year if fair_year is not None else -1,
                        (participation.fair_name or "").lower(),
                    )
                    export_rows.append(
                        (
                            sort_key,
                            customer_values
                            + [
                                group_id,
                                match_score,
                                duplicate_reason,
                                participation.fair_name,
                                participation.fair_year,
                                participation.hall,
                                participation.stand,
                            ],
                        )
                    )

        export_rows.sort(key=lambda item: item[0])

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "duplicate_group_customers"
        sheet.append(list(OUTPUT_COLUMNS))
        for _sort_key, row_values in export_rows:
            sheet.append(row_values)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        workbook.save(output_path)
    finally:
        db.close()

    participation_rows_exported = len(export_rows)
    print("Duplicate group customer export")
    print(f"  Database: {settings.database_url.split('@')[-1]}")
    if args.organization_id is not None:
        print(f"  Organization filter: {args.organization_id}")
    print(f"  Duplicate groups exported: {len(all_groups)}")
    print(f"  Customers exported: {len(customers_exported)}")
    print(f"  Participation rows exported: {participation_rows_exported}")
    print(f"  Excel output: {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
