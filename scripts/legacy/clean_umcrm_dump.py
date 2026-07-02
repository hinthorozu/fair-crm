#!/usr/bin/env python3
"""Clean UMCRM legacy SQL dump into canonical JSON exports for migration."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from analyze_umcrm_duplicates import normalize_company_name  # noqa: E402
from umcrm_cleaning import (  # noqa: E402
    clean_company_emails,
    clean_company_name,
    clean_company_phones,
    clean_company_websites,
    clean_fair_record,
    clean_fair_relations,
    collapse_whitespace,
    decode_html_entities,
    fix_mojibake,
    sanitize_email_raw,
)
from umcrm_sql_parser import load_umcrm_dump  # noqa: E402


def build_cross_company_duplicate_emails(
    emails: list[tuple[int, int, str | None]],
) -> set[str]:
    email_to_companies: dict[str, set[int]] = defaultdict(set)
    for _, company_id, email in emails:
        if not email:
            continue
        norm = sanitize_email_raw(email)
        if norm:
            email_to_companies[norm].add(company_id)
    return {norm for norm, cids in email_to_companies.items() if len(cids) > 1}


def clean_all(data: dict[str, Any]) -> dict[str, Any]:
    companies_raw = data["companies"]
    emails_raw = data["emails"]
    fairs_raw = data["fairs"]
    relations_raw = data["fair_relations"]

    cross_company_emails = build_cross_company_duplicate_emails(emails_raw)

    emails_by_company: dict[int, list[str]] = defaultdict(list)
    for _, company_id, email in emails_raw:
        if email:
            emails_by_company[company_id].append(email)

    stats: dict[str, int] = defaultdict(int)
    clean_companies: list[dict[str, Any]] = []
    clean_email_groups: list[dict[str, Any]] = []

    for company_id in sorted(companies_raw.keys()):
        company = companies_raw[company_id]
        name_original = company.name or ""
        name_clean, name_issues, name_manual = clean_company_name(name_original)

        phones_clean, phone_issues, phone_stats = clean_company_phones(
            company.phone1, company.phone2, company.phone3
        )
        websites_clean, website_issues, website_stats = clean_company_websites(
            company.web1, company.web2
        )

        notes_clean = None
        if company.notes:
            notes_text = decode_html_entities(company.notes)
            notes_text, _ = fix_mojibake(notes_text)
            notes_clean = collapse_whitespace(notes_text)

        company_issues = list(name_issues) + phone_issues + website_issues
        manual_review = name_manual or any(
            i.startswith("phone_contains") or i == "manual_review_phone" for i in phone_issues
        ) or any(i.startswith("dropped_invalid_website") for i in website_issues)

        stats["dropped_placeholder_phone"] += phone_stats["dropped_placeholder"]
        stats["phones_dropped_empty"] += phone_stats["dropped_empty"]
        stats["phones_duplicate_merged"] += phone_stats["duplicate_merged"]
        stats["dropped_placeholder_website"] += website_stats["dropped_placeholder"]
        stats["dropped_invalid_website"] += website_stats["dropped_invalid"]
        stats["websites_normalized"] += website_stats["normalized"]
        stats["websites_dropped_empty"] += website_stats["dropped_empty"]
        stats["websites_duplicate_merged"] += website_stats["duplicate_merged"]

        if manual_review:
            stats["manual_review_companies"] += 1

        clean_companies.append(
            {
                "legacy_company_id": company_id,
                "name_original": name_original,
                "name_clean": name_clean,
                "normalized_name": normalize_company_name(name_clean),
                "phone_values_clean": phones_clean,
                "website_values_clean": websites_clean,
                "country_id": company.country_id,
                "notes_clean": notes_clean,
                "manual_review": manual_review,
                "issues": company_issues,
            }
        )

        company_emails = emails_by_company.get(company_id, [])
        emails_clean, emails_original, email_issues, email_stats = clean_company_emails(
            company_emails,
            cross_company_duplicates=cross_company_emails,
        )

        stats["dropped_empty_email"] += email_stats["dropped_empty"]
        stats["dropped_placeholder_email"] += email_stats["dropped_placeholder"]
        stats["dropped_invalid_email"] += email_stats["dropped_invalid"]
        stats["emails_duplicate_merged"] += email_stats["duplicate_merged"]

        if email_issues:
            clean_email_groups.append(
                {
                    "legacy_company_id": company_id,
                    "emails_clean": emails_clean,
                    "emails_original": emails_original,
                    "issues": email_issues,
                }
            )
        elif emails_clean:
            clean_email_groups.append(
                {
                    "legacy_company_id": company_id,
                    "emails_clean": emails_clean,
                    "emails_original": emails_original,
                    "issues": [],
                }
            )

    clean_fairs: list[dict[str, Any]] = []
    for fair_id in sorted(fairs_raw.keys()):
        fair = fairs_raw[fair_id]
        record = clean_fair_record(
            fair_id,
            fair.name,
            fair.start_fair,
            fair.end_fair,
            fair.fair_area,
            fair.fair_website,
            fair.email_subject,
        )
        if record["issues"]:
            if "nullified_start_date" in record["issues"]:
                stats["fair_dates_nullified"] += 1
            if "nullified_end_date" in record["issues"]:
                stats["fair_dates_nullified"] += 1
        if record["manual_review"]:
            stats["manual_review_fairs"] += 1
        clean_fairs.append(record)

    company_ids = set(companies_raw.keys())
    fair_ids = set(fairs_raw.keys())
    clean_relations, relation_stats = clean_fair_relations(
        relations_raw, company_ids, fair_ids
    )
    stats["relation_orphans_dropped"] = relation_stats["dropped_orphan"]
    stats["duplicate_relations_dropped"] = relation_stats["duplicate_dropped"]

    return {
        "clean_companies": clean_companies,
        "clean_email_groups": clean_email_groups,
        "clean_fairs": clean_fairs,
        "clean_relations": clean_relations,
        "stats": dict(stats),
        "input": {
            "companies": len(companies_raw),
            "emails": len(emails_raw),
            "fairs": len(fairs_raw),
            "relations": len(relations_raw),
        },
    }


def build_cleaning_report(result: dict[str, Any], input_path: Path) -> str:
    inp = result["input"]
    st = result["stats"]
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# UMCRM Cleaning Report",
        "",
        f"Generated: {now}",
        f"Source: `{input_path}`",
        "",
        "## Input dataset summary",
        "",
        f"- Companies: **{inp['companies']:,}**",
        f"- Emails: **{inp['emails']:,}**",
        f"- Fairs: **{inp['fairs']:,}**",
        f"- Relations: **{inp['relations']:,}**",
        "",
        "## Cleaned output summary",
        "",
        f"- Companies: **{len(result['clean_companies']):,}** (all retained, none dropped)",
        f"- Company email groups: **{len(result['clean_email_groups']):,}**",
        f"- Fairs: **{len(result['clean_fairs']):,}**",
        f"- Relations: **{len(result['clean_relations']):,}**",
        "",
        "## Cleaning actions",
        "",
        f"- Dropped invalid email count: **{st.get('dropped_invalid_email', 0):,}**",
        f"- Dropped placeholder email count: **{st.get('dropped_placeholder_email', 0):,}**",
        f"- Dropped empty email count: **{st.get('dropped_empty_email', 0):,}**",
        f"- Same-company duplicate emails merged: **{st.get('emails_duplicate_merged', 0):,}**",
        f"- Dropped placeholder phone count: **{st.get('dropped_placeholder_phone', 0):,}**",
        f"- Dropped invalid website count: **{st.get('dropped_invalid_website', 0):,}**",
        f"- Dropped placeholder website count: **{st.get('dropped_placeholder_website', 0):,}**",
        f"- Normalized website count: **{st.get('websites_normalized', 0):,}**",
        f"- Nullified fair dates count: **{st.get('fair_dates_nullified', 0):,}**",
        f"- Manual review companies: **{st.get('manual_review_companies', 0):,}**",
        f"- Manual review fairs: **{st.get('manual_review_fairs', 0):,}**",
        f"- Relation duplicate dropped count: **{st.get('duplicate_relations_dropped', 0):,}**",
        f"- Relation orphans dropped: **{st.get('relation_orphans_dropped', 0):,}**",
        "",
        "## Key risks",
        "",
        "- Company duplicate merge is **not** performed in this script; use duplicate intelligence report before migration.",
        "- Cross-company duplicate emails are preserved but flagged in email group issues.",
        "- Companies with placeholder or encoding-damaged names are kept with `manual_review: true`.",
        "- Fair `EmailSubject` values are preserved in `email_subject_clean` for migration metadata.",
        "- Merge-conflict fair participations must be resolved in a separate merge step.",
        "",
        "## Recommended next step",
        "",
        "1. Review `manual_review` companies and fairs.",
        "2. Run duplicate merge planning (`analyze_umcrm_duplicates.py` output).",
        "3. Build migration script consuming `scripts/legacy/cleaned/*.json`.",
        "4. Map legacy fair IDs and company IDs to KYROX CRM entities.",
        "",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(result: dict[str, Any], output_dir: Path, input_path: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "clean_companies.json").write_text(
        json.dumps(result["clean_companies"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "clean_company_emails.json").write_text(
        json.dumps(result["clean_email_groups"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "clean_fairs.json").write_text(
        json.dumps(result["clean_fairs"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "clean_fair_company_relations.json").write_text(
        json.dumps(result["clean_relations"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    issues_payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": str(input_path),
        "input": result["input"],
        "stats": result["stats"],
    }
    (output_dir / "cleaning_issues.json").write_text(
        json.dumps(issues_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "cleaning_report.md").write_text(
        build_cleaning_report(result, input_path),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean UMCRM legacy SQL dump")
    parser.add_argument("--input", required=True, type=Path, help="Path to SQL dump")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=SCRIPT_DIR / "cleaned",
        help="Output directory for cleaned JSON exports",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"Input file not found: {args.input}", file=sys.stderr)
        return 1

    print(f"Loading {args.input} ...")
    data = load_umcrm_dump(args.input)
    print(
        f"Parsed: {len(data['companies'])} companies, {len(data['emails'])} emails, "
        f"{len(data['fairs'])} fairs, {len(data['fair_relations'])} relations"
    )

    print("Cleaning ...")
    result = clean_all(data)
    write_outputs(result, args.output_dir, args.input)

    st = result["stats"]
    print(f"Written to {args.output_dir}")
    print(
        f"  companies={len(result['clean_companies'])}, "
        f"email_groups={len(result['clean_email_groups'])}, "
        f"fairs={len(result['clean_fairs'])}, "
        f"relations={len(result['clean_relations'])}"
    )
    print(
        f"  invalid_emails_dropped={st.get('dropped_invalid_email', 0)}, "
        f"manual_review_companies={st.get('manual_review_companies', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
