"""UMCRM duplicate merge plan builder (shared by script and tests)."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse


def normalize_phone_digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def website_host(value: str) -> str:
    text = value.strip().lower()
    if not text.startswith(("http://", "https://")):
        text = "http://" + text
    parsed = urlparse(text)
    host = (parsed.netloc or parsed.path).lower().removeprefix("www.").rstrip("/")
    return host


def email_domain(value: str) -> str:
    if "@" not in value:
        return ""
    return value.rsplit("@", 1)[1].lower().strip()


def contact_richness(company: dict[str, Any], emails: list[str]) -> int:
    return (
        len(emails)
        + len(company.get("phone_values_clean") or [])
        + len(company.get("website_values_clean") or [])
        + (1 if company.get("notes_clean") else 0)
    )


def fair_ids_for_companies(
    company_ids: list[int],
    relations_by_company: dict[int, list[int]],
) -> dict[int, set[int]]:
    fair_to_companies: dict[int, set[int]] = defaultdict(set)
    for cid in company_ids:
        for fair_id in relations_by_company.get(cid, []):
            fair_to_companies[fair_id].add(cid)
    return fair_to_companies


def has_same_fair_conflict(
    company_ids: list[int],
    relations_by_company: dict[int, list[int]],
) -> tuple[bool, list[dict[str, Any]]]:
    conflicts: list[dict[str, Any]] = []
    fair_map = fair_ids_for_companies(company_ids, relations_by_company)
    for fair_id, cids in fair_map.items():
        if len(cids) > 1:
            conflicts.append(
                {
                    "legacy_fair_id": fair_id,
                    "legacy_company_ids": sorted(cids),
                }
            )
    return bool(conflicts), conflicts


def has_country_mismatch(company_ids: list[int], companies: dict[int, dict[str, Any]]) -> bool:
    countries = {companies[cid]["country_id"] for cid in company_ids if cid in companies}
    countries.discard(None)
    return len(countries) > 1


def has_serious_contact_conflict(
    company_ids: list[int],
    companies: dict[int, dict[str, Any]],
    emails_by_company: dict[int, list[str]],
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    phone_sets: set[str] = set()
    website_hosts: set[str] = set()
    email_domains: set[str] = set()

    for cid in company_ids:
        company = companies.get(cid, {})
        for phone in company.get("phone_values_clean") or []:
            digits = normalize_phone_digits(phone)
            if digits:
                phone_sets.add(digits)
        for website in company.get("website_values_clean") or []:
            host = website_host(website)
            if host:
                website_hosts.add(host)
        for email in emails_by_company.get(cid, []):
            domain = email_domain(email)
            if domain:
                email_domains.add(domain)

    if len(phone_sets) > 1:
        reasons.append("phone_conflict")
    if len(website_hosts) > 1:
        reasons.append("website_conflict")
    if len(email_domains) > 1:
        reasons.append("email_domain_conflict")
    return bool(reasons), reasons


def any_manual_review(company_ids: list[int], companies: dict[int, dict[str, Any]]) -> bool:
    return any(companies.get(cid, {}).get("manual_review") for cid in company_ids)


def select_canonical_company_id(
    company_ids: list[int],
    companies: dict[int, dict[str, Any]],
    relations_by_company: dict[int, list[int]],
    emails_by_company: dict[int, list[str]],
) -> tuple[int, str]:
    def sort_key(cid: int) -> tuple[int, int, int, int]:
        fair_count = len(relations_by_company.get(cid, []))
        richness = contact_richness(companies[cid], emails_by_company.get(cid, []))
        name_len = len(companies[cid].get("name_clean") or "")
        return (-fair_count, -richness, -name_len, cid)

    canonical_id = min(company_ids, key=sort_key)
    canonical = companies[canonical_id]
    fair_count = len(relations_by_company.get(canonical_id, []))
    richness = contact_richness(canonical, emails_by_company.get(canonical_id, []))
    reason = (
        f"Most fair participations ({fair_count}), richest contact data ({richness} fields), "
        f"then smallest legacy_company_id tie-break ({canonical_id})"
    )
    return canonical_id, reason


def merge_emails(company_ids: list[int], emails_by_company: dict[int, list[str]]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for cid in sorted(company_ids):
        for email in emails_by_company.get(cid, []):
            lowered = email.lower().strip()
            if lowered and lowered not in seen:
                seen.add(lowered)
                merged.append(lowered)
    merged.sort()
    return merged


def merge_phones(company_ids: list[int], companies: dict[int, dict[str, Any]]) -> tuple[list[str], list[str]]:
    seen_digits: set[str] = set()
    seen_text: set[str] = set()
    merged: list[str] = []
    issues: list[str] = []

    for cid in sorted(company_ids):
        for phone in companies.get(cid, {}).get("phone_values_clean") or []:
            has_letters = bool(re.search(r"[a-zA-Z\u0080-\uFFFF]", phone))
            if has_letters:
                key = phone.strip().lower()
                if key in seen_text:
                    continue
                seen_text.add(key)
                merged.append(phone)
                issues.append(f"risky_phone:{cid}:{phone}")
            else:
                digits = normalize_phone_digits(phone)
                if not digits or digits in seen_digits:
                    continue
                seen_digits.add(digits)
                merged.append(phone)
    return merged, issues


def merge_websites(
    company_ids: list[int],
    companies: dict[int, dict[str, Any]],
) -> tuple[str | None, list[str]]:
    seen_hosts: set[str] = set()
    ordered: list[str] = []
    for cid in sorted(company_ids):
        for website in companies.get(cid, {}).get("website_values_clean") or []:
            host = website_host(website)
            if host and host not in seen_hosts:
                seen_hosts.add(host)
                ordered.append(website)
    if not ordered:
        return None, []
    return ordered[0], ordered[1:]


def merge_notes(company_ids: list[int], companies: dict[int, dict[str, Any]]) -> list[str]:
    notes: list[str] = []
    seen: set[str] = set()
    for cid in sorted(company_ids):
        note = companies.get(cid, {}).get("notes_clean")
        if note and note not in seen:
            seen.add(note)
            notes.append(note)
    return notes


def build_field_merge_plan(
    company_ids: list[int],
    canonical_id: int,
    companies: dict[int, dict[str, Any]],
    emails_by_company: dict[int, list[str]],
) -> dict[str, Any]:
    canonical = companies[canonical_id]
    aliases = sorted(
        {
            companies[cid]["name_clean"]
            for cid in company_ids
            if cid != canonical_id and companies.get(cid, {}).get("name_clean")
        }
    )
    emails_merged = merge_emails(company_ids, emails_by_company)
    phones_merged, phone_issues = merge_phones(company_ids, companies)
    website_canonical, website_aliases = merge_websites(company_ids, companies)
    notes_merged = merge_notes(company_ids, companies)

    return {
        "name_clean": canonical.get("name_clean"),
        "aliases": aliases,
        "emails_merged": emails_merged,
        "emails_canonical_semicolon": ";".join(emails_merged),
        "phones_merged": phones_merged,
        "phone_issues": phone_issues,
        "website_canonical": website_canonical,
        "website_aliases": website_aliases,
        "notes_merged": notes_merged,
        "country_id": canonical.get("country_id"),
    }


def build_fair_relation_merge_plan(
    company_ids: list[int],
    relations_by_company: dict[int, list[int]],
) -> list[dict[str, Any]]:
    fair_sources: dict[int, set[int]] = defaultdict(set)
    for cid in company_ids:
        for fair_id in relations_by_company.get(cid, []):
            fair_sources[fair_id].add(cid)
    return [
        {
            "legacy_fair_id": fair_id,
            "source_legacy_company_ids": sorted(source_ids),
        }
        for fair_id, source_ids in sorted(fair_sources.items())
    ]


@dataclass
class MergePlanStats:
    total_companies: int = 0
    duplicate_groups: int = 0
    auto_merge_groups: int = 0
    auto_merged_company_records: int = 0
    manual_review_groups: int = 0
    risk_groups: int = 0
    keep_records: int = 0
    same_fair_conflict_blocked: int = 0
    manual_review_blocked: int = 0
    country_mismatch_blocked: int = 0
    contact_conflict_blocked: int = 0
    relation_conflicts_blocked: int = 0


def evaluate_high_group_for_auto_merge(
    group: dict[str, Any],
    companies: dict[int, dict[str, Any]],
    relations_by_company: dict[int, list[int]],
    emails_by_company: dict[int, list[str]],
) -> tuple[bool, list[str], list[dict[str, Any]]]:
    company_ids = group["company_ids"]
    blocked: list[str] = []
    relation_conflicts: list[dict[str, Any]] = []

    same_fair, conflicts = has_same_fair_conflict(company_ids, relations_by_company)
    if same_fair or group.get("same_fair_overlap"):
        blocked.append("same_fair_conflict")
        relation_conflicts = conflicts

    if any_manual_review(company_ids, companies):
        blocked.append("manual_review_company")

    if has_country_mismatch(company_ids, companies):
        blocked.append("country_mismatch")

    contact_conflict, contact_reasons = has_serious_contact_conflict(
        company_ids, companies, emails_by_company
    )
    if contact_conflict:
        blocked.extend(contact_reasons)

    return not blocked, blocked, relation_conflicts


def build_merge_plan(
    companies: list[dict[str, Any]],
    email_groups: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    duplicate_groups: list[dict[str, Any]],
) -> dict[str, Any]:
    company_map = {c["legacy_company_id"]: c for c in companies}
    emails_by_company = {e["legacy_company_id"]: e.get("emails_clean") or [] for e in email_groups}

    relations_by_company: dict[int, list[int]] = defaultdict(list)
    for rel in relations:
        relations_by_company[rel["legacy_company_id"]].append(rel["legacy_fair_id"])

    all_company_ids = sorted(company_map.keys())
    duplicate_company_ids: set[int] = set()
    for group in duplicate_groups:
        duplicate_company_ids.update(group["company_ids"])

    auto_merge_plans: list[dict[str, Any]] = []
    manual_review_queue: list[dict[str, Any]] = []
    risk_groups_out: list[dict[str, Any]] = []
    stats = MergePlanStats(total_companies=len(all_company_ids), duplicate_groups=len(duplicate_groups))

    group_counter = 0
    review_counter = 0
    risk_counter = 0

    for group in duplicate_groups:
        company_ids = group["company_ids"]
        confidence = group.get("confidence", "REVIEW")
        normalized_name = group.get("normalized_name", "")
        group_counter += 1
        merge_group_id = f"grp_{group_counter:04d}"

        base_entry = {
            "merge_group_id": merge_group_id,
            "normalized_name": normalized_name,
            "confidence": confidence,
            "company_ids": company_ids,
            "original_names": group.get("original_names", []),
            "same_fair_overlap": group.get("same_fair_overlap", False),
            "scenario": group.get("scenario"),
            "recommendation": group.get("recommendation"),
        }

        if confidence == "RISK":
            risk_counter += 1
            risk_group_id = f"grp_risk_{risk_counter:04d}"
            _, relation_conflicts = has_same_fair_conflict(company_ids, relations_by_company)
            risk_groups_out.append(
                {
                    **base_entry,
                    "merge_group_id": risk_group_id,
                    "auto_merge": False,
                    "blocked_reasons": ["risk_confidence"],
                    "relation_conflicts": relation_conflicts,
                }
            )
            stats.risk_groups += 1
            continue

        if confidence == "REVIEW":
            review_counter += 1
            review_group_id = f"grp_review_{review_counter:04d}"
            _, relation_conflicts = has_same_fair_conflict(company_ids, relations_by_company)
            manual_review_queue.append(
                {
                    **base_entry,
                    "merge_group_id": review_group_id,
                    "auto_merge": False,
                    "blocked_reasons": ["review_confidence"],
                    "relation_conflicts": relation_conflicts,
                }
            )
            stats.manual_review_groups += 1
            continue

        # HIGH confidence — evaluate safety gates
        can_auto, blocked_reasons, relation_conflicts = evaluate_high_group_for_auto_merge(
            group, company_map, relations_by_company, emails_by_company
        )

        if can_auto:
            canonical_id, reason = select_canonical_company_id(
                company_ids, company_map, relations_by_company, emails_by_company
            )
            field_merge = build_field_merge_plan(
                company_ids, canonical_id, company_map, emails_by_company
            )
            fair_relations = build_fair_relation_merge_plan(company_ids, relations_by_company)
            auto_merge_plans.append(
                {
                    **base_entry,
                    "auto_merge": True,
                    "canonical_legacy_company_id": canonical_id,
                    "merged_legacy_company_ids": sorted(company_ids),
                    "canonical_selection_reason": reason,
                    "field_merge": field_merge,
                    "fair_relations_merged": fair_relations,
                    "distinct_fair_count": len(fair_relations),
                    "blocked_reasons": [],
                    "relation_conflicts": [],
                }
            )
            stats.auto_merge_groups += 1
            stats.auto_merged_company_records += len(company_ids)
        else:
            review_counter += 1
            review_group_id = f"grp_review_{review_counter:04d}"
            manual_review_queue.append(
                {
                    **base_entry,
                    "merge_group_id": review_group_id,
                    "auto_merge": False,
                    "blocked_reasons": blocked_reasons,
                    "relation_conflicts": relation_conflicts,
                    "proposed_canonical_legacy_company_id": select_canonical_company_id(
                        company_ids, company_map, relations_by_company, emails_by_company
                    )[0],
                }
            )
            stats.manual_review_groups += 1
            if "same_fair_conflict" in blocked_reasons:
                stats.same_fair_conflict_blocked += 1
                stats.relation_conflicts_blocked += 1
            if "manual_review_company" in blocked_reasons:
                stats.manual_review_blocked += 1
            if "country_mismatch" in blocked_reasons:
                stats.country_mismatch_blocked += 1
            if any(
                r in blocked_reasons
                for r in ("phone_conflict", "website_conflict", "email_domain_conflict")
            ):
                stats.contact_conflict_blocked += 1

    # ID mapping
    id_mapping: dict[str, dict[str, Any]] = {}
    company_to_merge_group: dict[int, str] = {}

    for plan in auto_merge_plans:
        gid = plan["merge_group_id"]
        canonical = plan["canonical_legacy_company_id"]
        for cid in plan["merged_legacy_company_ids"]:
            company_to_merge_group[cid] = gid
            if cid == canonical:
                id_mapping[str(cid)] = {
                    "action": "merge",
                    "target_legacy_company_id": canonical,
                    "merge_group_id": gid,
                    "role": "canonical",
                }
            else:
                id_mapping[str(cid)] = {
                    "action": "merge",
                    "target_legacy_company_id": canonical,
                    "merge_group_id": gid,
                    "role": "merged",
                }

    for entry in manual_review_queue:
        gid = entry["merge_group_id"]
        for cid in entry["company_ids"]:
            if cid not in company_to_merge_group:
                company_to_merge_group[cid] = gid
                id_mapping[str(cid)] = {
                    "action": "manual_review",
                    "target_legacy_company_id": None,
                    "merge_group_id": gid,
                }

    for entry in risk_groups_out:
        gid = entry["merge_group_id"]
        for cid in entry["company_ids"]:
            if cid not in company_to_merge_group:
                company_to_merge_group[cid] = gid
                id_mapping[str(cid)] = {
                    "action": "risk",
                    "target_legacy_company_id": None,
                    "merge_group_id": gid,
                }

    for cid in all_company_ids:
        if str(cid) not in id_mapping:
            id_mapping[str(cid)] = {
                "action": "keep",
                "target_legacy_company_id": cid,
                "merge_group_id": None,
            }
            stats.keep_records += 1

    auto_merge_removed = sum(len(p["merged_legacy_company_ids"]) - 1 for p in auto_merge_plans)
    estimated_after_auto = stats.total_companies - auto_merge_removed

    review_company_ids: set[int] = set()
    for entry in manual_review_queue:
        review_company_ids.update(entry["company_ids"])
    review_removed_if_merged = sum(len(entry["company_ids"]) - 1 for entry in manual_review_queue)
    estimated_if_review_merged = estimated_after_auto - review_removed_if_merged

    risk_company_ids: set[int] = set()
    for entry in risk_groups_out:
        risk_company_ids.update(entry["company_ids"])

    return {
        "auto_merge_plans": auto_merge_plans,
        "manual_review_queue": manual_review_queue,
        "risk_groups": risk_groups_out,
        "id_mapping": id_mapping,
        "stats": stats,
        "estimated_final_customers_after_auto_merge": estimated_after_auto,
        "estimated_final_customers_if_review_merged": estimated_if_review_merged,
        "review_company_ids": sorted(review_company_ids),
        "risk_company_ids": sorted(risk_company_ids),
    }


def top_examples(items: list[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    return items[:limit]
