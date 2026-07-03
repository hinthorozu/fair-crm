#!/usr/bin/env python3
"""Export duplicate-group customers split by fair (read-only).

Writes one Excel file per fair plus NO_FAIR.xlsx and SUMMARY.xlsx.
Does not modify the database.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import ANALYSIS_DIR, EXPORTS_DIR, bootstrap

bootstrap()
DEFAULT_OUTPUT_DIR = EXPORTS_DIR / "duplicate_groups_by_fair"
NO_FAIR_FILE_NAME = "NO_FAIR.xlsx"
SUMMARY_FILE_NAME = "SUMMARY.xlsx"


def _load_module(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module: {module_path}")
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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export duplicate-group customers into one Excel file per fair."
    )
    parser.add_argument(
        "--organization-id",
        type=UUID,
        default=None,
        help="Limit analysis to one organization (default: all organizations).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory (default: scripts/maintenance/exports/duplicate_groups_by_fair/).",
    )
    return parser.parse_args()


def _safe_file_stem(fair_name: str, year: int | None) -> str:
    stem = re.sub(r'[\\/:*?"<>|]+', "_", fair_name).strip()
    stem = re.sub(r"\s+", "_", stem)
    stem = stem.strip("._") or "fair"
    year_part = str(year) if year is not None else "unknown"
    return f"{stem}_{year_part}"


def _unique_file_name(stem: str, used_names: set[str]) -> str:
    candidate = f"{stem}.xlsx"
    if candidate not in used_names:
        used_names.add(candidate)
        return candidate
    index = 2
    while True:
        candidate = f"{stem}_{index}.xlsx"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        index += 1


def _write_workbook(path: Path, columns: tuple[str, ...], rows: list[list[object]]) -> None:
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "duplicate_group_customers"
    sheet.append(list(columns))
    for row_values in rows:
        sheet.append(row_values)
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def _summary_counts(rows: list[list[object]], columns: tuple[str, ...]) -> tuple[int, int]:
    group_idx = columns.index("duplicate_group_id")
    customer_idx = columns.index("customer_id")
    groups = {row[group_idx] for row in rows if row[group_idx]}
    customers = {row[customer_idx] for row in rows if row[customer_idx]}
    return len(customers), len(groups)


def main() -> int:
    _configure_stdio_utf8()
    args = _parse_args()

    export_mod = _load_module(
        "maintenance_export_duplicate_group_customers",
        Path(__file__).resolve().parent / "export_duplicate_group_customers.py",
    )
    dup = _load_module(
        "maintenance_report_customer_duplicates",
        ANALYSIS_DIR / "report_customer_duplicates.py",
    )

    from openpyxl import Workbook
    from sqlalchemy.orm import Session

    from app.core.config import get_settings
    from app.db.session import SessionLocal
    from app.modules.customers.infrastructure.persistence.models import CustomerModel

    get_settings.cache_clear()
    settings = get_settings()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    db: Session = SessionLocal()
    fair_buckets: dict[tuple[str, int | None], list[tuple[tuple[str, str], list[object]]]] = (
        defaultdict(list)
    )
    no_fair_rows: list[tuple[tuple[str, str], list[object]]] = []
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

        records = []
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

        participations_by_customer = export_mod._load_participations(db, list(set(member_ids)))

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
                customer_values = export_mod._customer_export_values(model)
                participation_rows = participations_by_customer.get(customer_id)
                sort_key = (group_id, model.display_name.lower())

                if not participation_rows:
                    row_values = customer_values + [
                        group_id,
                        match_score,
                        duplicate_reason,
                        None,
                        None,
                        None,
                        None,
                    ]
                    no_fair_rows.append((sort_key, row_values))
                    continue

                for participation in participation_rows:
                    fair_key = (participation.fair_name or "UNKNOWN_FAIR", participation.fair_year)
                    row_values = customer_values + [
                        group_id,
                        match_score,
                        duplicate_reason,
                        participation.fair_name,
                        participation.fair_year,
                        participation.hall,
                        participation.stand,
                    ]
                    fair_buckets[fair_key].append((sort_key, row_values))

        used_names: set[str] = set()
        summary_rows: list[list[object]] = []

        for (fair_name, fair_year), rows in sorted(
            fair_buckets.items(),
            key=lambda item: ((item[0][1] if item[0][1] is not None else -1), item[0][0].lower()),
        ):
            rows.sort(key=lambda item: item[0])
            row_values = [row for _sort_key, row in rows]
            file_name = _unique_file_name(_safe_file_stem(fair_name, fair_year), used_names)
            file_path = output_dir / file_name
            _write_workbook(file_path, export_mod.OUTPUT_COLUMNS, row_values)
            customer_count, group_count = _summary_counts(row_values, export_mod.OUTPUT_COLUMNS)
            summary_rows.append([fair_name, fair_year, customer_count, group_count, file_name])

        no_fair_rows.sort(key=lambda item: item[0])
        no_fair_values = [row for _sort_key, row in no_fair_rows]
        no_fair_path = output_dir / NO_FAIR_FILE_NAME
        _write_workbook(no_fair_path, export_mod.OUTPUT_COLUMNS, no_fair_values)
        no_fair_customers, no_fair_groups = _summary_counts(
            no_fair_values,
            export_mod.OUTPUT_COLUMNS,
        )
        summary_rows.append(["NO_FAIR", None, no_fair_customers, no_fair_groups, NO_FAIR_FILE_NAME])

        summary_path = output_dir / SUMMARY_FILE_NAME
        summary_workbook = Workbook()
        summary_sheet = summary_workbook.active
        summary_sheet.title = "summary"
        summary_sheet.append(
            ["Fair Name", "Year", "Customer Count", "Duplicate Group Count", "Output File Name"]
        )
        for row in summary_rows:
            summary_sheet.append(row)
        summary_workbook.save(summary_path)
    finally:
        db.close()

    total_rows = sum(len(rows) for rows in fair_buckets.values()) + len(no_fair_rows)
    print("Duplicate groups by fair export")
    print(f"  Database: {settings.database_url.split('@')[-1]}")
    if args.organization_id is not None:
        print(f"  Organization filter: {args.organization_id}")
    print(f"  Duplicate groups analyzed: {len(all_groups)}")
    print(f"  Customers exported: {len(customers_exported)}")
    print(f"  Fair files written: {len(fair_buckets)}")
    print(f"  Total rows written: {total_rows}")
    print(f"  Output directory: {output_dir}")
    print(f"  Summary: {output_dir / SUMMARY_FILE_NAME}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
