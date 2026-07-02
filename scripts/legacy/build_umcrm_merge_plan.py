#!/usr/bin/env python3
"""Build UMCRM duplicate merge plan from cleaned legacy exports and duplicate intelligence."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from umcrm_merge_plan import build_merge_plan, top_examples  # noqa: E402


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def format_group_example(entry: dict[str, Any]) -> str:
    ids = entry.get("company_ids") or entry.get("merged_legacy_company_ids") or []
    names = entry.get("original_names") or []
    label = entry.get("normalized_name", "")
    if entry.get("auto_merge"):
        canonical = entry.get("canonical_legacy_company_id")
        return (
            f"- **{label}** — canonical={canonical}; ids={ids[:6]}{'...' if len(ids) > 6 else ''}; "
            f"fairs={entry.get('distinct_fair_count', '?')}; "
            f"names: {', '.join(names[:2])}{'...' if len(names) > 2 else ''}"
        )
    blocked = entry.get("blocked_reasons") or []
    return (
        f"- **{label}** — ids={ids[:6]}{'...' if len(ids) > 6 else ''}; "
        f"blocked={blocked}; same_fair_overlap={entry.get('same_fair_overlap')}"
    )


def build_summary_md(result: dict[str, Any], plan_meta: dict[str, Any]) -> str:
    st = result["stats"]
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    auto = result["auto_merge_plans"]
    review = result["manual_review_queue"]
    risk = result["risk_groups"]

    lines = [
        "# UMCRM Company Merge Plan Summary",
        "",
        f"Generated: {now}",
        f"Cleaned dir: `{plan_meta['cleaned_dir']}`",
        f"Reports dir: `{plan_meta['reports_dir']}`",
        "",
        "## Counts",
        "",
        f"- Total companies: **{st.total_companies:,}**",
        f"- Duplicate groups: **{st.duplicate_groups:,}**",
        f"- Auto-merge groups: **{st.auto_merge_groups:,}**",
        f"- Auto-merged company records: **{st.auto_merged_company_records:,}**",
        f"- Manual review groups: **{st.manual_review_groups:,}**",
        f"- Risk groups: **{st.risk_groups:,}**",
        f"- Keep records (non-duplicate): **{st.keep_records:,}**",
        "",
        "## Estimated customer counts",
        "",
        f"- After auto-merge only: **{result['estimated_final_customers_after_auto_merge']:,}**",
        f"- If all review groups later merged: **{result['estimated_final_customers_if_review_merged']:,}**",
        "",
        "## Safety gates (HIGH groups blocked from auto-merge)",
        "",
        f"- Same-fair conflict blocked: **{st.same_fair_conflict_blocked:,}**",
        f"- Manual review company blocked: **{st.manual_review_blocked:,}**",
        f"- Country mismatch blocked: **{st.country_mismatch_blocked:,}**",
        f"- Contact conflict blocked: **{st.contact_conflict_blocked:,}**",
        f"- Relation conflicts blocked (total): **{st.relation_conflicts_blocked:,}**",
        "",
        "## Top 20 auto-merge examples",
        "",
    ]
    for entry in top_examples(auto, 20):
        lines.append(format_group_example(entry))

    lines.extend(["", "## Top 20 manual review examples", ""])
    for entry in top_examples(review, 20):
        lines.append(format_group_example(entry))

    lines.extend(["", "## Top 20 risk examples", ""])
    for entry in top_examples(risk, 20):
        lines.append(format_group_example(entry))

    lines.extend(
        [
            "",
            "## Migration recommendation",
            "",
            "1. Apply `umcrm_company_id_mapping.json` during migration — only `action: merge` secondary IDs roll up to canonical.",
            "2. Import auto-merge groups first using `field_merge` union data (emails, phones, websites, notes).",
            "3. Process `umcrm_manual_review_queue.json` after stakeholder review; do not auto-merge blocked HIGH groups.",
            "4. Keep `umcrm_risk_groups.json` separate — resolve same-fair overlaps before any merge.",
            "5. Preserve all fair relations from `fair_relations_merged`; dedupe only at participation import time for canonical IDs.",
            "",
            "## Notes",
            "",
            "- No KYROX DB writes performed.",
            "- Company duplicate merge is planned only; execution happens in a future migration script.",
            "- Fair relations are never dropped in this plan; same-fair conflicts block auto-merge instead.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def write_outputs(result: dict[str, Any], output_dir: Path, plan_meta: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    merge_plan_payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "meta": plan_meta,
        "stats": {
            "total_companies": result["stats"].total_companies,
            "duplicate_groups": result["stats"].duplicate_groups,
            "auto_merge_groups": result["stats"].auto_merge_groups,
            "auto_merged_company_records": result["stats"].auto_merged_company_records,
            "manual_review_groups": result["stats"].manual_review_groups,
            "risk_groups": result["stats"].risk_groups,
            "keep_records": result["stats"].keep_records,
            "estimated_final_customers_after_auto_merge": result[
                "estimated_final_customers_after_auto_merge"
            ],
            "estimated_final_customers_if_review_merged": result[
                "estimated_final_customers_if_review_merged"
            ],
            "safety_gates": {
                "same_fair_conflict_blocked": result["stats"].same_fair_conflict_blocked,
                "manual_review_blocked": result["stats"].manual_review_blocked,
                "country_mismatch_blocked": result["stats"].country_mismatch_blocked,
                "contact_conflict_blocked": result["stats"].contact_conflict_blocked,
                "relation_conflicts_blocked": result["stats"].relation_conflicts_blocked,
            },
        },
        "auto_merge_groups": result["auto_merge_plans"],
    }

    (output_dir / "umcrm_company_merge_plan.json").write_text(
        json.dumps(merge_plan_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "umcrm_company_id_mapping.json").write_text(
        json.dumps(result["id_mapping"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "umcrm_manual_review_queue.json").write_text(
        json.dumps(result["manual_review_queue"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "umcrm_risk_groups.json").write_text(
        json.dumps(result["risk_groups"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "umcrm_merge_plan_summary.md").write_text(
        build_summary_md(result, plan_meta),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build UMCRM duplicate merge plan")
    parser.add_argument(
        "--cleaned-dir",
        type=Path,
        default=SCRIPT_DIR / "cleaned",
        help="Directory with cleaned JSON exports",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=SCRIPT_DIR / "reports",
        help="Directory with duplicate intelligence reports",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=SCRIPT_DIR / "merge_plan",
        help="Output directory for merge plan files",
    )
    args = parser.parse_args()

    companies_path = args.cleaned_dir / "clean_companies.json"
    emails_path = args.cleaned_dir / "clean_company_emails.json"
    relations_path = args.cleaned_dir / "clean_fair_company_relations.json"
    groups_path = args.reports_dir / "umcrm_duplicate_groups.json"

    for path in (companies_path, emails_path, relations_path, groups_path):
        if not path.is_file():
            print(f"Required file not found: {path}", file=sys.stderr)
            return 1

    print("Loading cleaned exports and duplicate groups ...")
    companies = load_json(companies_path)
    email_groups = load_json(emails_path)
    relations = load_json(relations_path)
    duplicate_payload = load_json(groups_path)
    duplicate_groups = duplicate_payload.get("groups", [])

    print(
        f"Loaded: {len(companies)} companies, {len(email_groups)} email groups, "
        f"{len(relations)} relations, {len(duplicate_groups)} duplicate groups"
    )

    print("Building merge plan ...")
    result = build_merge_plan(companies, email_groups, relations, duplicate_groups)

    plan_meta = {
        "cleaned_dir": str(args.cleaned_dir.resolve()),
        "reports_dir": str(args.reports_dir.resolve()),
        "output_dir": str(args.output_dir.resolve()),
    }
    write_outputs(result, args.output_dir, plan_meta)

    st = result["stats"]
    print(f"Written to {args.output_dir}")
    print(
        f"  auto_merge_groups={st.auto_merge_groups}, "
        f"manual_review_groups={st.manual_review_groups}, "
        f"risk_groups={st.risk_groups}, "
        f"keep_records={st.keep_records}"
    )
    print(
        f"  estimated_customers_after_auto_merge="
        f"{result['estimated_final_customers_after_auto_merge']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
