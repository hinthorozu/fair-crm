"""Pure migration plan builder for legacy UMCRM → KYROX CRM (no DB I/O)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any

UMCRM_MIGRATION_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

COUNTRY_BY_ID = {1: "Türkiye", 2: "Other"}


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def deterministic_uuid(org_id: str, entity: str, key: str | int) -> uuid.UUID:
    return uuid.uuid5(UMCRM_MIGRATION_NAMESPACE, f"{org_id}:{entity}:{key}")


def join_emails(emails: list[str]) -> str | None:
    if not emails:
        return None
    cleaned = sorted({e.strip().lower() for e in emails if e and e.strip()})
    return ";".join(cleaned) if cleaned else None


def fit_semicolon_emails(value: str | None, max_len: int = 255) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    if len(value) <= max_len:
        return value, None
    parts = value.split(";")
    kept: list[str] = []
    overflow: list[str] = []
    current = ""
    for part in parts:
        candidate = part if not kept else f"{current};{part}" if current else part
        if not kept:
            trial = part
        else:
            trial = f"{';'.join(kept)};{part}" if kept else part
        if len(trial) <= max_len:
            kept.append(part)
            current = trial
        else:
            overflow.extend(parts[len(kept) :])
            break
    primary = ";".join(kept) if kept else parts[0][:max_len]
    overflow_all = overflow or parts[len(kept) :]
    overflow_note = f"Additional emails: {';'.join(overflow_all)}" if overflow_all else None
    return primary, overflow_note


def truncate_text(value: str | None, max_len: int) -> str | None:
    if not value:
        return None
    text = value.strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def prepare_customer_fields(
    *,
    display_name: str,
    email: str | None,
    phone: str | None,
    website: str | None,
    description: str | None,
) -> tuple[str, str | None, str | None, str | None, str | None]:
    email_fit, email_overflow = fit_semicolon_emails(email, 255)
    description = build_description_parts(description, email_overflow)
    return (
        truncate_text(display_name, 255) or "Legacy Company",
        email_fit,
        truncate_text(phone, 50),
        truncate_text(website, 255),
        description,
    )


def join_phones(phones: list[str]) -> tuple[str | None, str | None]:
    if not phones:
        return None, None
    primary = phones[0]
    extras = phones[1:]
    extra_note = f"Additional phones: {', '.join(extras)}" if extras else None
    return primary, extra_note


def build_description_parts(*parts: str | None) -> str | None:
    chunks = [p.strip() for p in parts if p and p.strip()]
    return "\n\n".join(chunks) if chunks else None


@dataclass
class FairImportSpec:
    legacy_fair_id: int
    kyrox_fair_id: uuid.UUID
    name: str
    start_date: date | None
    end_date: date | None
    venue: str | None
    website: str | None
    description: str | None
    country: str | None
    issues: list[str] = field(default_factory=list)


@dataclass
class CustomerImportSpec:
    kyrox_customer_id: uuid.UUID
    customer_key: int
    legacy_company_ids: list[int]
    action: str
    migration_review_status: str | None
    display_name: str
    email: str | None
    phone: str | None
    website: str | None
    country: str | None
    description: str | None
    merge_group_id: str | None = None
    issues: list[str] = field(default_factory=list)


@dataclass
class ParticipationImportSpec:
    kyrox_participation_id: uuid.UUID
    legacy_fair_id: int
    legacy_company_id: int
    resolved_legacy_company_id: int
    kyrox_fair_id: uuid.UUID
    kyrox_customer_id: uuid.UUID
    notes: str | None


@dataclass
class ActivityImportSpec:
    kyrox_activity_id: uuid.UUID
    kyrox_customer_id: uuid.UUID
    subject: str
    description: str


@dataclass
class MigrationPlan:
    fairs: list[FairImportSpec]
    customers: list[CustomerImportSpec]
    participations: list[ParticipationImportSpec]
    activities: list[ActivityImportSpec]
    legacy_fair_to_kyrox: dict[str, str]
    legacy_company_to_kyrox: dict[str, str]
    legacy_participation_keys: dict[str, str]
    stats: dict[str, Any]
    warnings: list[str]


def _company_map(companies: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {c["legacy_company_id"]: c for c in companies}


def _emails_map(email_groups: list[dict[str, Any]]) -> dict[int, list[str]]:
    return {g["legacy_company_id"]: g.get("emails_clean") or [] for g in email_groups}


def _auto_merge_lookup(merge_plan: dict[str, Any]) -> dict[int, dict[str, Any]]:
    lookup: dict[int, dict[str, Any]] = {}
    for group in merge_plan.get("auto_merge_groups", []):
        for cid in group.get("merged_legacy_company_ids", []):
            lookup[int(cid)] = group
    return lookup


def resolve_target_legacy_company_id(legacy_company_id: int, id_mapping: dict[str, Any]) -> int:
    entry = id_mapping[str(legacy_company_id)]
    action = entry["action"]
    if action == "merge":
        target = entry.get("target_legacy_company_id")
        if target is None:
            raise ValueError(f"merge mapping missing target for {legacy_company_id}")
        return int(target)
    return legacy_company_id


def customer_key_for_legacy(legacy_company_id: int, id_mapping: dict[str, Any]) -> int:
    return resolve_target_legacy_company_id(legacy_company_id, id_mapping)


def build_customer_specs(
    *,
    org_id: str,
    companies: list[dict[str, Any]],
    email_groups: list[dict[str, Any]],
    id_mapping: dict[str, Any],
    merge_plan: dict[str, Any],
) -> tuple[list[CustomerImportSpec], dict[int, uuid.UUID]]:
    company_by_id = _company_map(companies)
    emails_by_id = _emails_map(email_groups)
    auto_merge = _auto_merge_lookup(merge_plan)
    specs: list[CustomerImportSpec] = []
    key_to_uuid: dict[int, uuid.UUID] = {}
    handled_keys: set[int] = set()

    for legacy_id_str, entry in id_mapping.items():
        legacy_id = int(legacy_id_str)
        action = entry["action"]
        if action == "merge" and entry.get("role") == "merged":
            continue
        if action == "merge":
            key = int(entry["target_legacy_company_id"])
        else:
            key = legacy_id

        if key in handled_keys:
            continue
        handled_keys.add(key)

        review_status = None
        merge_group_id = entry.get("merge_group_id")
        legacy_ids = [legacy_id]
        display_name = ""
        email = None
        phone = None
        website = None
        country = None
        description = None
        issues: list[str] = []

        if action == "merge":
            group = auto_merge.get(key)
            if not group:
                issues.append("missing_auto_merge_group")
                company = company_by_id.get(key, {})
            else:
                merge_group_id = group.get("merge_group_id")
                legacy_ids = sorted(int(x) for x in group.get("merged_legacy_company_ids", []))
                field_merge = group.get("field_merge") or {}
                display_name = field_merge.get("name_clean") or company_by_id.get(key, {}).get(
                    "name_clean", f"Legacy Company {key}"
                )
                email = field_merge.get("emails_canonical_semicolon") or join_emails(
                    field_merge.get("emails_merged") or []
                )
                phones = field_merge.get("phones_merged") or []
                phone, phone_note = join_phones(phones)
                websites = field_merge.get("website_canonical")
                if not websites:
                    aliases = field_merge.get("website_aliases") or []
                    websites = aliases[0] if aliases else None
                website = websites
                country = COUNTRY_BY_ID.get(field_merge.get("country_id"), "Türkiye")
                aliases = field_merge.get("aliases") or []
                notes_merged = field_merge.get("notes_merged") or []
                phone_issues = field_merge.get("phone_issues") or []
                description = build_description_parts(
                    build_description_parts(*notes_merged),
                    f"Name aliases: {', '.join(aliases)}" if aliases else None,
                    phone_note,
                    f"Phone review flags: {', '.join(phone_issues)}" if phone_issues else None,
                    f"Legacy merge group {merge_group_id}; legacy company IDs: {', '.join(map(str, legacy_ids))}",
                )
        else:
            company = company_by_id.get(legacy_id, {})
            display_name = company.get("name_clean") or company.get("name_original") or f"Legacy {legacy_id}"
            email = join_emails(emails_by_id.get(legacy_id, []))
            phone, phone_note = join_phones(company.get("phone_values_clean") or [])
            websites = company.get("website_values_clean") or []
            website = websites[0] if websites else None
            country = COUNTRY_BY_ID.get(company.get("country_id"), "Türkiye")
            issues.extend(company.get("issues") or [])
            if action == "manual_review":
                review_status = "manual_review"
            elif action == "risk":
                review_status = "risk"
            description = build_description_parts(
                company.get("notes_clean"),
                phone_note,
                f"Migration review status: {review_status}" if review_status else None,
                f"Legacy company ID: {legacy_id}",
            )

        if not display_name.strip():
            display_name = f"Legacy Company {key}"
            issues.append("empty_name")

        kyrox_id = deterministic_uuid(org_id, "customer", key)
        key_to_uuid[key] = kyrox_id
        specs.append(
            CustomerImportSpec(
                kyrox_customer_id=kyrox_id,
                customer_key=key,
                legacy_company_ids=legacy_ids,
                action=action,
                migration_review_status=review_status,
                display_name=display_name.strip(),
                email=email,
                phone=phone,
                website=website,
                country=country,
                description=description,
                merge_group_id=merge_group_id,
                issues=issues,
            )
        )

    return specs, key_to_uuid


def build_fair_specs(org_id: str, fairs: list[dict[str, Any]]) -> list[FairImportSpec]:
    specs: list[FairImportSpec] = []
    for fair in fairs:
        legacy_id = int(fair["legacy_fair_id"])
        start = parse_iso_date(fair.get("start_date_clean"))
        end = parse_iso_date(fair.get("end_date_clean"))
        description = build_description_parts(
            fair.get("email_subject_clean"),
            "Legacy UMCRM EmailSubject preserved for migration metadata."
            if fair.get("email_subject_clean")
            else None,
        )
        specs.append(
            FairImportSpec(
                legacy_fair_id=legacy_id,
                kyrox_fair_id=deterministic_uuid(org_id, "fair", legacy_id),
                name=fair.get("name_clean") or fair.get("name_original") or f"Fair {legacy_id}",
                start_date=start,
                end_date=end,
                venue=fair.get("fair_area_clean"),
                website=fair.get("website_clean"),
                description=description,
                country="Türkiye",
                issues=list(fair.get("issues") or []),
            )
        )
    return specs


def build_participation_specs(
    *,
    org_id: str,
    relations: list[dict[str, Any]],
    id_mapping: dict[str, Any],
    key_to_uuid: dict[int, uuid.UUID],
    fair_uuid_by_legacy: dict[int, uuid.UUID],
) -> tuple[list[ParticipationImportSpec], int]:
    specs: list[ParticipationImportSpec] = []
    seen: set[tuple[int, int]] = set()
    skipped_duplicates = 0

    for rel in relations:
        legacy_company_id = int(rel["legacy_company_id"])
        legacy_fair_id = int(rel["legacy_fair_id"])
        resolved_company = customer_key_for_legacy(legacy_company_id, id_mapping)
        pair = (resolved_company, legacy_fair_id)
        if pair in seen:
            skipped_duplicates += 1
            continue
        seen.add(pair)

        fair_uuid = fair_uuid_by_legacy.get(legacy_fair_id)
        customer_uuid = key_to_uuid.get(resolved_company)
        if fair_uuid is None or customer_uuid is None:
            continue

        rel_key = f"{legacy_fair_id}:{resolved_company}"
        specs.append(
            ParticipationImportSpec(
                kyrox_participation_id=deterministic_uuid(org_id, "participation", rel_key),
                legacy_fair_id=legacy_fair_id,
                legacy_company_id=legacy_company_id,
                resolved_legacy_company_id=resolved_company,
                kyrox_fair_id=fair_uuid,
                kyrox_customer_id=customer_uuid,
                notes=f"Legacy relation id {rel.get('legacy_relation_id')}; source company {legacy_company_id}",
            )
        )
    return specs, skipped_duplicates


def build_activity_specs(org_id: str, customers: list[CustomerImportSpec]) -> list[ActivityImportSpec]:
    activities: list[ActivityImportSpec] = []
    for customer in customers:
        review = customer.migration_review_status or "none"
        description = build_description_parts(
            customer.description,
            f"Legacy company IDs: {', '.join(map(str, customer.legacy_company_ids))}",
            f"Merge action: {customer.action}",
            f"Migration review status: {review}",
        )
        activities.append(
            ActivityImportSpec(
                kyrox_activity_id=deterministic_uuid(
                    org_id, "activity", customer.customer_key
                ),
                kyrox_customer_id=customer.kyrox_customer_id,
                subject="Legacy UMCRM migration",
                description=description or "Imported from legacy UMCRM canonical JSON.",
            )
        )
    return activities


def build_migration_plan(
    *,
    org_id: str,
    companies: list[dict[str, Any]],
    email_groups: list[dict[str, Any]],
    fairs: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    id_mapping: dict[str, Any],
    merge_plan: dict[str, Any],
    limit: int | None = None,
) -> MigrationPlan:
    warnings: list[str] = []
    fair_specs = build_fair_specs(org_id, fairs)
    customer_specs, key_to_uuid = build_customer_specs(
        org_id=org_id,
        companies=companies,
        email_groups=email_groups,
        id_mapping=id_mapping,
        merge_plan=merge_plan,
    )
    customer_specs.sort(key=lambda c: c.customer_key)

    if limit is not None:
        customer_specs = customer_specs[:limit]
        allowed_keys = {c.customer_key for c in customer_specs}
        key_to_uuid = {k: v for k, v in key_to_uuid.items() if k in allowed_keys}
        allowed_fair_ids = set()
        filtered_relations = []
        for rel in relations:
            resolved = customer_key_for_legacy(int(rel["legacy_company_id"]), id_mapping)
            if resolved in allowed_keys:
                filtered_relations.append(rel)
                allowed_fair_ids.add(int(rel["legacy_fair_id"]))
        relations = filtered_relations
        fair_specs = [f for f in fair_specs if f.legacy_fair_id in allowed_fair_ids]
        warnings.append(f"Applied --limit {limit}: subset import only")

    fair_uuid_by_legacy = {f.legacy_fair_id: f.kyrox_fair_id for f in fair_specs}
    participation_specs, skipped_dupes = build_participation_specs(
        org_id=org_id,
        relations=relations,
        id_mapping=id_mapping,
        key_to_uuid=key_to_uuid,
        fair_uuid_by_legacy=fair_uuid_by_legacy,
    )
    activity_specs = build_activity_specs(org_id, customer_specs)

    legacy_fair_to_kyrox = {str(f.legacy_fair_id): str(f.kyrox_fair_id) for f in fair_specs}
    legacy_company_to_kyrox: dict[str, str] = {}
    for spec in customer_specs:
        for legacy_id in spec.legacy_company_ids:
            legacy_company_to_kyrox[str(legacy_id)] = str(spec.kyrox_customer_id)
    for legacy_id_str in id_mapping:
        legacy_id = int(legacy_id_str)
        key = customer_key_for_legacy(legacy_id, id_mapping)
        if key in key_to_uuid:
            legacy_company_to_kyrox[str(legacy_id)] = str(key_to_uuid[key])

    participation_map = {
        f"{p.legacy_fair_id}:{p.resolved_legacy_company_id}": str(p.kyrox_participation_id)
        for p in participation_specs
    }

    merge_records = sum(
        1 for v in id_mapping.values() if v.get("action") == "merge" and v.get("role") != "canonical"
    )
    if not merge_records:
        merge_records = sum(
            len(g.get("merged_legacy_company_ids", [])) - 1
            for g in merge_plan.get("auto_merge_groups", [])
        )

    stats = {
        "fairs_to_create": len(fair_specs),
        "customers_to_create": len(customer_specs),
        "participations_to_create": len(participation_specs),
        "activities_to_create": len(activity_specs),
        "merged_legacy_companies": merge_records,
        "manual_review_records": sum(
            1 for c in customer_specs if c.migration_review_status == "manual_review"
        ),
        "risk_records": sum(1 for c in customer_specs if c.migration_review_status == "risk"),
        "participation_duplicates_skipped": skipped_dupes,
        "auto_merge_customers": sum(1 for c in customer_specs if c.action == "merge"),
        "keep_customers": sum(1 for c in customer_specs if c.action == "keep"),
    }

    return MigrationPlan(
        fairs=fair_specs,
        customers=customer_specs,
        participations=participation_specs,
        activities=activity_specs,
        legacy_fair_to_kyrox=legacy_fair_to_kyrox,
        legacy_company_to_kyrox=legacy_company_to_kyrox,
        legacy_participation_keys=participation_map,
        stats=stats,
        warnings=warnings,
    )
