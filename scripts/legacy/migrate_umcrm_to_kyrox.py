#!/usr/bin/env python3
"""Migrate legacy UMCRM canonical JSON exports into KYROX Fair CRM (dev only)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(SCRIPT_DIR))

from dotenv import load_dotenv

load_dotenv(BACKEND / ".env")

from umcrm_migration_engine import MigrationPlan, build_migration_plan  # noqa: E402

ALLOWED_ENVS = frozenset({"development", "local", "test"})
DEV_ORG_ID = UUID(
    os.environ.get("FAIR_CRM_DEV_ORGANIZATION_ID", "00000000-0000-4000-8000-000000000010")
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_dev_only() -> None:
    app_env = os.environ.get("APP_ENV", "development").strip().lower()
    if app_env not in ALLOWED_ENVS:
        print(f"Refusing: APP_ENV={app_env!r}", file=sys.stderr)
        raise SystemExit(1)


def write_dry_run_reports(plan: MigrationPlan, reports_dir: Path, meta: dict[str, Any]) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "meta": meta,
        "stats": plan.stats,
        "warnings": plan.warnings,
    }
    (reports_dir / "umcrm_migration_dry_run.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# UMCRM Migration Dry Run",
        "",
        f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Counts",
        "",
        f"- Fairs to create: **{plan.stats['fairs_to_create']:,}**",
        f"- Customers to create: **{plan.stats['customers_to_create']:,}**",
        f"- Participations to create: **{plan.stats['participations_to_create']:,}**",
        f"- Activities to create: **{plan.stats['activities_to_create']:,}**",
        f"- Merged legacy companies (non-canonical): **{plan.stats['merged_legacy_companies']:,}**",
        f"- Manual review customers: **{plan.stats['manual_review_records']:,}**",
        f"- Risk customers: **{plan.stats['risk_records']:,}**",
        f"- Participation duplicates skipped in plan: **{plan.stats['participation_duplicates_skipped']:,}**",
        "",
        "## Warnings",
        "",
    ]
    if plan.warnings:
        for warning in plan.warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("- None")
    lines.append("")
    (reports_dir / "umcrm_migration_dry_run.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_apply_reports(
    reports_dir: Path,
    meta: dict[str, Any],
    apply_stats: dict[str, Any],
    plan: MigrationPlan,
) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "umcrm_legacy_to_kyrox_fair_mapping.json").write_text(
        json.dumps(plan.legacy_fair_to_kyrox, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (reports_dir / "umcrm_legacy_to_kyrox_customer_mapping.json").write_text(
        json.dumps(plan.legacy_company_to_kyrox, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (reports_dir / "umcrm_legacy_to_kyrox_participation_mapping.json").write_text(
        json.dumps(plan.legacy_participation_keys, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "meta": meta,
        "apply_stats": apply_stats,
        "plan_stats": plan.stats,
    }
    (reports_dir / "umcrm_migration_apply_report.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# UMCRM Migration Apply Report",
        "",
        f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Apply results",
        "",
    ]
    for key, value in apply_stats.items():
        if isinstance(value, list):
            lines.append(f"- {key}: {len(value)}")
        else:
            lines.append(f"- {key}: **{value:,}**" if isinstance(value, int) else f"- {key}: **{value}**")
    lines.append("")
    (reports_dir / "umcrm_migration_apply_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def fair_status_for_dates(start: date | None, end: date | None) -> str:
    from app.modules.fairs.domain.value_objects import FairStatus

    today = date.today()
    if end and end < today:
        return FairStatus.COMPLETED
    if start and start > today:
        return FairStatus.PLANNED
    return FairStatus.ACTIVE


def apply_migration_plan(
    plan: MigrationPlan,
    *,
    org_id: UUID,
    batch_size: int = 500,
) -> dict[str, Any]:
    from umcrm_migration_engine import prepare_customer_fields
    from app.db.session import SessionLocal
    from app.modules.activities.domain.entities import Activity
    from app.modules.activities.domain.value_objects import (
        ActivitySource,
        ActivityStatus,
        ActivityType,
    )
    from app.modules.activities.infrastructure.persistence.models import ActivityModel
    from app.modules.activities.infrastructure.repositories.activity_repository import (
        SqlAlchemyActivityRepository,
    )
    from app.modules.customers.domain.entities import Customer
    from app.modules.customers.domain.value_objects import CustomerSource, CustomerStatus, CustomerType
    from app.modules.customers.infrastructure.persistence.models import CustomerModel
    from app.modules.customers.infrastructure.repositories.customer_repository import (
        SqlAlchemyCustomerRepository,
    )
    from app.modules.fairs.domain.entities import Fair
    from app.modules.fairs.infrastructure.persistence.models import FairModel
    from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
    from app.modules.participations.domain.entities import CustomerFairParticipation
    from app.modules.participations.domain.value_objects import ParticipationStatus
    from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
    from app.modules.participations.infrastructure.repositories.participation_repository import (
        SqlAlchemyParticipationRepository,
    )

    db = SessionLocal()
    now = datetime.now(tz=UTC)
    stats = {
        "fairs_created": 0,
        "fairs_skipped": 0,
        "customers_created": 0,
        "customers_skipped": 0,
        "participations_created": 0,
        "participations_skipped": 0,
        "activities_created": 0,
        "activities_skipped": 0,
        "failed_records": [],
    }

    fair_repo = SqlAlchemyFairRepository(db)
    customer_repo = SqlAlchemyCustomerRepository(db)
    participation_repo = SqlAlchemyParticipationRepository(db)
    activity_repo = SqlAlchemyActivityRepository(db)

    try:
        pending = 0
        for fair_spec in plan.fairs:
            if db.get(FairModel, fair_spec.kyrox_fair_id):
                stats["fairs_skipped"] += 1
                continue
            try:
                fair = Fair.create(
                    organization_id=org_id,
                    name=fair_spec.name,
                    venue=fair_spec.venue,
                    country=fair_spec.country,
                    start_date=fair_spec.start_date,
                    end_date=fair_spec.end_date,
                    website=fair_spec.website,
                    status=fair_status_for_dates(fair_spec.start_date, fair_spec.end_date),
                    description=fair_spec.description,
                    now=now,
                )
                fair.id = fair_spec.kyrox_fair_id
                fair_repo.add(fair)
                db.flush()
                stats["fairs_created"] += 1
                pending += 1
            except Exception as exc:
                db.rollback()
                stats["failed_records"].append(
                    {"entity": "fair", "legacy_fair_id": fair_spec.legacy_fair_id, "error": str(exc)}
                )
            if pending >= batch_size:
                db.commit()
                pending = 0

        for customer_spec in plan.customers:
            if db.get(CustomerModel, customer_spec.kyrox_customer_id):
                stats["customers_skipped"] += 1
                continue
            try:
                display_name, email, phone, website, description = prepare_customer_fields(
                    display_name=customer_spec.display_name,
                    email=customer_spec.email,
                    phone=customer_spec.phone,
                    website=customer_spec.website,
                    description=customer_spec.description,
                )
                customer = Customer.create(
                    organization_id=org_id,
                    display_name=display_name,
                    legal_name=display_name,
                    customer_type=CustomerType.EXHIBITOR,
                    status=CustomerStatus.ACTIVE,
                    website=website,
                    phone=phone,
                    email=email,
                    country=customer_spec.country,
                    description=description,
                    source=CustomerSource.MANUAL,
                    now=now,
                )
                customer.id = customer_spec.kyrox_customer_id
                customer_repo.add(customer)
                db.flush()
                stats["customers_created"] += 1
                pending += 1
            except Exception as exc:
                db.rollback()
                stats["failed_records"].append(
                    {
                        "entity": "customer",
                        "legacy_company_ids": customer_spec.legacy_company_ids,
                        "error": str(exc),
                    }
                )
            if pending >= batch_size:
                db.commit()
                pending = 0

        for part_spec in plan.participations:
            if db.get(CustomerFairParticipationModel, part_spec.kyrox_participation_id):
                stats["participations_skipped"] += 1
                continue
            if participation_repo.exists_active(
                org_id, part_spec.kyrox_customer_id, part_spec.kyrox_fair_id
            ):
                stats["participations_skipped"] += 1
                continue
            if not db.get(CustomerModel, part_spec.kyrox_customer_id):
                stats["failed_records"].append(
                    {
                        "entity": "participation",
                        "legacy_fair_id": part_spec.legacy_fair_id,
                        "legacy_company_id": part_spec.legacy_company_id,
                        "error": "customer missing",
                    }
                )
                continue
            if not db.get(FairModel, part_spec.kyrox_fair_id):
                stats["failed_records"].append(
                    {
                        "entity": "participation",
                        "legacy_fair_id": part_spec.legacy_fair_id,
                        "legacy_company_id": part_spec.legacy_company_id,
                        "error": "fair missing",
                    }
                )
                continue
            try:
                participation = CustomerFairParticipation.create(
                    organization_id=org_id,
                    customer_id=part_spec.kyrox_customer_id,
                    fair_id=part_spec.kyrox_fair_id,
                    hall=None,
                    stand=None,
                    participation_status=ParticipationStatus.EXHIBITOR,
                    notes=part_spec.notes,
                    now=now,
                )
                participation.id = part_spec.kyrox_participation_id
                participation_repo.add(participation)
                db.flush()
                stats["participations_created"] += 1
                pending += 1
            except Exception as exc:
                db.rollback()
                stats["failed_records"].append(
                    {
                        "entity": "participation",
                        "legacy_fair_id": part_spec.legacy_fair_id,
                        "legacy_company_id": part_spec.legacy_company_id,
                        "error": str(exc),
                    }
                )
            if pending >= batch_size:
                db.commit()
                pending = 0

        for activity_spec in plan.activities:
            if db.get(ActivityModel, activity_spec.kyrox_activity_id):
                stats["activities_skipped"] += 1
                continue
            if not db.get(CustomerModel, activity_spec.kyrox_customer_id):
                continue
            try:
                activity = Activity.create(
                    organization_id=org_id,
                    customer_id=activity_spec.kyrox_customer_id,
                    activity_type=ActivityType.NOTE,
                    subject=activity_spec.subject,
                    description=activity_spec.description,
                    activity_date=now,
                    status=ActivityStatus.COMPLETED,
                    source=ActivitySource.IMPORT,
                    now=now,
                )
                activity.id = activity_spec.kyrox_activity_id
                activity_repo.add(activity)
                db.flush()
                stats["activities_created"] += 1
                pending += 1
            except Exception as exc:
                db.rollback()
                stats["failed_records"].append(
                    {"entity": "activity", "customer_id": str(activity_spec.kyrox_customer_id), "error": str(exc)}
                )
            if pending >= batch_size:
                db.commit()
                pending = 0

        db.commit()
        return stats
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def count_db_entities(org_id: UUID) -> dict[str, int]:
    from app.db.session import SessionLocal
    from app.modules.activities.infrastructure.persistence.models import ActivityModel
    from app.modules.customers.infrastructure.persistence.models import CustomerModel
    from app.modules.fairs.infrastructure.persistence.models import FairModel
    from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel

    db = SessionLocal()
    try:
        return {
            "fairs": db.query(FairModel).filter(FairModel.organization_id == org_id).count(),
            "customers": db.query(CustomerModel)
            .filter(CustomerModel.organization_id == org_id)
            .count(),
            "participations": db.query(CustomerFairParticipationModel)
            .filter(CustomerFairParticipationModel.organization_id == org_id)
            .count(),
            "activities": db.query(ActivityModel)
            .filter(ActivityModel.organization_id == org_id)
            .count(),
        }
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate legacy UMCRM canonical JSON to KYROX CRM")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--cleaned-dir", type=Path, default=SCRIPT_DIR / "cleaned")
    parser.add_argument("--merge-plan-dir", type=Path, default=SCRIPT_DIR / "merge_plan")
    parser.add_argument("--reports-dir", type=Path, default=SCRIPT_DIR / "migration_reports")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--skip-domain-reset",
        action="store_true",
        help="Skip dev domain reset before apply (not recommended)",
    )
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()

    ensure_dev_only()

    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    if settings.app_env not in ALLOWED_ENVS:
        print(f"Refusing: backend APP_ENV={settings.app_env!r}", file=sys.stderr)
        return 1

    org_id = settings.dev_organization_id or DEV_ORG_ID
    org_id_str = str(org_id)

    companies = load_json(args.cleaned_dir / "clean_companies.json")
    email_groups = load_json(args.cleaned_dir / "clean_company_emails.json")
    fairs = load_json(args.cleaned_dir / "clean_fairs.json")
    relations = load_json(args.cleaned_dir / "clean_fair_company_relations.json")
    id_mapping = load_json(args.merge_plan_dir / "umcrm_company_id_mapping.json")
    merge_plan = load_json(args.merge_plan_dir / "umcrm_company_merge_plan.json")

    print(
        f"Loaded canonical inputs: companies={len(companies)}, fairs={len(fairs)}, "
        f"relations={len(relations)}"
    )

    plan = build_migration_plan(
        org_id=org_id_str,
        companies=companies,
        email_groups=email_groups,
        fairs=fairs,
        relations=relations,
        id_mapping=id_mapping,
        merge_plan=merge_plan,
        limit=args.limit,
    )

    meta = {
        "organization_id": org_id_str,
        "cleaned_dir": str(args.cleaned_dir.resolve()),
        "merge_plan_dir": str(args.merge_plan_dir.resolve()),
        "limit": args.limit,
    }

    if args.dry_run:
        existing = count_db_entities(org_id)
        print("Existing DB counts:", existing)
        print("Planned import:", plan.stats)
        write_dry_run_reports(plan, args.reports_dir, meta)
        print(f"Dry-run reports written to {args.reports_dir}")
        return 0

    if not args.skip_domain_reset:
        print("Resetting dev domain tables before apply ...")
        from reset_fair_crm_dev_domain import reset_domain_data  # noqa: E402
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            reset_domain_data(db, org_id)
            db.commit()
        finally:
            db.close()

    print("Applying migration ...")
    print("Planned:", plan.stats)
    apply_stats = apply_migration_plan(plan, org_id=org_id, batch_size=args.batch_size)
    write_apply_reports(args.reports_dir, meta, apply_stats, plan)

    final_counts = count_db_entities(org_id)
    print("Apply stats:", apply_stats)
    print("Final DB counts:", final_counts)
    print(f"Reports written to {args.reports_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
