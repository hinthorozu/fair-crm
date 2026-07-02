#!/usr/bin/env python3
"""Analyze UMCRM legacy SQL dump for duplicate company intelligence."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

TURKISH_CHAR_MAP = str.maketrans(
    {
        "Ç": "c",
        "ç": "c",
        "Ğ": "g",
        "ğ": "g",
        "İ": "i",
        "I": "i",
        "ı": "i",
        "Ö": "o",
        "ö": "o",
        "Ş": "s",
        "ş": "s",
        "Ü": "u",
        "ü": "u",
    }
)

LEGAL_SUFFIX_PATTERNS = [
    r"\banonim\s+sirketi\b",
    r"\banonim\s+sirket\b",
    r"\ba\.?\s*s\.?\b",
    r"\bas\b",
    r"\bltd\.?\s*sti\b",
    r"\bltd\s*sti\b",
    r"\bltd\.?\b",
    r"\blimited\s+sirketi\b",
    r"\blimited\b",
    r"\bsanayi\b",
    r"\bsan\.?\b",
    r"\bticaret\b",
    r"\btic\.?\b",
    r"\bdis\s+ticaret\b",
    r"\bdış\s+ticaret\b",
    r"\bithalat\b",
    r"\bihracat\b",
    r"\bve\b",
]

INSERT_RE = re.compile(
    r"^INSERT\s+INTO\s+`(?P<table>company|companyemail|country|fair|fairtocompany)`\s+VALUES\s+(?P<values>.+);\s*$",
    re.IGNORECASE,
)


def normalize_company_name(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    text = text.translate(TURKISH_CHAR_MAP)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    previous = None
    while previous != text:
        previous = text
        for pattern in LEGAL_SUFFIX_PATTERNS:
            text = re.sub(pattern, " ", text)
        text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_sql_values(raw: str) -> list[str | None]:
    values: list[str | None] = []
    i = 0
    n = len(raw)

    def skip_ws() -> None:
        nonlocal i
        while i < n and raw[i] in " \t\r\n":
            i += 1

    while i < n:
        skip_ws()
        if i >= n:
            break
        if raw[i] == ",":
            i += 1
            continue
        if raw[i : i + 4].upper() == "NULL":
            values.append(None)
            i += 4
            continue
        if raw[i] != "'":
            raise ValueError(f"Unexpected token at {i}: {raw[i:i + 20]!r}")
        i += 1
        chars: list[str] = []
        while i < n:
            ch = raw[i]
            if ch == "'":
                if i + 1 < n and raw[i + 1] == "'":
                    chars.append("'")
                    i += 2
                    continue
                i += 1
                break
            if ch == "\\" and i + 1 < n:
                chars.append(raw[i + 1])
                i += 2
                continue
            chars.append(ch)
            i += 1
        values.append("".join(chars))
    return values


def parse_insert_value_rows(raw: str) -> list[list[str | None]]:
    rows: list[list[str | None]] = []
    i = 0
    n = len(raw)

    while i < n:
        while i < n and raw[i] in " \t\r\n,":
            i += 1
        if i >= n:
            break
        if raw[i] != "(":
            raise ValueError(f"Expected '(' at {i}, got {raw[i:i + 20]!r}")

        depth = 0
        start = i
        in_string = False
        while i < n:
            ch = raw[i]
            if in_string:
                if ch == "\\" and i + 1 < n:
                    i += 2
                    continue
                if ch == "'":
                    if i + 1 < n and raw[i + 1] == "'":
                        i += 2
                        continue
                    in_string = False
                    i += 1
                    continue
                i += 1
                continue

            if ch == "'":
                in_string = True
                i += 1
                continue
            if ch == "(":
                depth += 1
                i += 1
                continue
            if ch == ")":
                depth -= 1
                i += 1
                if depth == 0:
                    inner = raw[start + 1 : i - 1]
                    rows.append(parse_sql_values(inner))
                    break
                continue
            i += 1
        else:
            raise ValueError("Unclosed tuple in INSERT values")

    return rows


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def normalize_phone(value: str | None) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    return digits or None


def normalize_website(value: str | None) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    lowered = text.lower()
    if not lowered.startswith(("http://", "https://")):
        lowered = "http://" + lowered
    try:
        parsed = urlparse(lowered)
        host = (parsed.netloc or parsed.path).lower()
        host = host.removeprefix("www.")
        return host or None
    except Exception:
        return lowered


def email_domain(value: str | None) -> str | None:
    text = clean_text(value)
    if not text or "@" not in text:
        return None
    return text.split("@", 1)[1].lower().strip()


@dataclass
class Company:
    id: int
    name: str
    phone1: str | None
    web1: str | None
    phone2: str | None
    phone3: str | None
    web2: str | None
    country_id: int | None
    normalized_name: str = ""


@dataclass
class DuplicateGroup:
    normalized_name: str
    company_ids: list[int] = field(default_factory=list)
    original_names: list[str] = field(default_factory=list)
    country_ids: set[int] = field(default_factory=set)
    phones: set[str] = field(default_factory=set)
    websites: set[str] = field(default_factory=set)
    emails: set[str] = field(default_factory=set)
    fair_ids: set[int] = field(default_factory=set)
    fair_names: set[str] = field(default_factory=set)
    relations: list[tuple[int, int]] = field(default_factory=list)
    same_fair_overlap: bool = False
    scenario: str = ""
    confidence: str = ""
    recommendation: str = ""
    duplicate_relation_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "normalized_name": self.normalized_name,
            "company_ids": self.company_ids,
            "original_names": self.original_names,
            "country_ids": sorted(self.country_ids),
            "phones": sorted(self.phones),
            "websites": sorted(self.websites),
            "emails": sorted(self.emails),
            "fair_ids": sorted(self.fair_ids),
            "fair_names": sorted(self.fair_names),
            "fair_count": len(self.fair_ids),
            "duplicate_relation_count": self.duplicate_relation_count,
            "same_fair_overlap": self.same_fair_overlap,
            "scenario": self.scenario,
            "confidence": self.confidence,
            "recommendation": self.recommendation,
        }


def iter_insert_rows(path: Path, encoding: str) -> Iterator[tuple[str, str]]:
    with path.open("r", encoding=encoding, errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line.startswith("INSERT INTO `"):
                continue
            match = INSERT_RE.match(line)
            if not match:
                continue
            table = match.group("table")
            values_raw = match.group("values")
            yield table, values_raw


def load_dump(path: Path) -> dict[str, Any]:
    companies: dict[int, Company] = {}
    emails: list[tuple[int, int, str | None]] = []
    countries: dict[int, str] = {}
    fairs: dict[int, str] = {}
    fair_relations: list[tuple[int, int, int]] = []

    encodings = ["utf-8", "latin5", "cp1254"]
    last_error: Exception | None = None
    parsed = False

    for encoding in encodings:
        try:
            companies.clear()
            emails.clear()
            countries.clear()
            fairs.clear()
            fair_relations.clear()
            for table, values_raw in iter_insert_rows(path, encoding):
                for values in parse_insert_value_rows(values_raw):
                    if table == "company" and len(values) >= 8:
                        cid = int(values[0])
                        companies[cid] = Company(
                            id=cid,
                            name=values[1] or "",
                            phone1=clean_text(values[2]),
                            web1=clean_text(values[3]),
                            phone2=clean_text(values[4]),
                            phone3=clean_text(values[5]),
                            web2=clean_text(values[6]),
                            country_id=int(values[7]) if values[7] else None,
                        )
                    elif table == "companyemail" and len(values) >= 3:
                        emails.append((int(values[0]), int(values[1]), clean_text(values[2])))
                    elif table == "country" and len(values) >= 2:
                        countries[int(values[0])] = values[1] or ""
                    elif table == "fair" and len(values) >= 2:
                        fairs[int(values[0])] = values[1] or ""
                    elif table == "fairtocompany" and len(values) >= 3:
                        fair_relations.append((int(values[0]), int(values[1]), int(values[2])))
            parsed = True
            break
        except Exception as exc:
            last_error = exc
            continue

    if not parsed:
        raise RuntimeError(f"Failed to parse dump with supported encodings: {last_error}")

    for company in companies.values():
        company.normalized_name = normalize_company_name(company.name)

    return {
        "companies": companies,
        "emails": emails,
        "countries": countries,
        "fairs": fairs,
        "fair_relations": fair_relations,
    }


def build_duplicate_groups(data: dict[str, Any]) -> tuple[list[DuplicateGroup], dict[str, int]]:
    companies: dict[int, Company] = data["companies"]
    emails: list[tuple[int, int, str | None]] = data["emails"]
    fairs: dict[int, str] = data["fairs"]
    fair_relations: list[tuple[int, int, int]] = data["fair_relations"]

    emails_by_company: dict[int, list[str]] = defaultdict(list)
    for _, company_id, email in emails:
        if email:
            emails_by_company[company_id].append(email)

    fairs_by_company: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for rel_id, fair_id, company_id in fair_relations:
        fairs_by_company[company_id].append((rel_id, fair_id))

    groups_map: dict[str, DuplicateGroup] = {}
    for company in companies.values():
        key = company.normalized_name
        if not key:
            continue
        group = groups_map.get(key)
        if group is None:
            group = DuplicateGroup(normalized_name=key)
            groups_map[key] = group
        group.company_ids.append(company.id)
        group.original_names.append(company.name)
        if company.country_id is not None:
            group.country_ids.add(company.country_id)
        for phone in (company.phone1, company.phone2, company.phone3):
            norm = normalize_phone(phone)
            if norm:
                group.phones.add(norm)
        for web in (company.web1, company.web2):
            norm = normalize_website(web)
            if norm:
                group.websites.add(norm)
        for email in emails_by_company.get(company.id, []):
            group.emails.add(email.lower())
        for _, fair_id in fairs_by_company.get(company.id, []):
            group.fair_ids.add(fair_id)
            fair_name = fairs.get(fair_id)
            if fair_name:
                group.fair_names.add(fair_name)
            group.relations.append((company.id, fair_id))

    duplicate_groups = [g for g in groups_map.values() if len(g.company_ids) > 1]

    stats = {
        "duplicate_groups": len(duplicate_groups),
        "duplicate_company_records": sum(len(g.company_ids) for g in duplicate_groups),
        "multi_fair_groups": 0,
        "same_fair_overlap_groups": 0,
        "high": 0,
        "review": 0,
        "risk": 0,
    }

    for group in duplicate_groups:
        relation_pairs = group.relations
        unique_pairs = set(relation_pairs)
        group.duplicate_relation_count = len(relation_pairs) - len(unique_pairs)

        fair_to_companies: dict[int, set[int]] = defaultdict(set)
        for company_id, fair_id in relation_pairs:
            fair_to_companies[fair_id].add(company_id)
        group.same_fair_overlap = any(len(ids) > 1 for ids in fair_to_companies.values())

        country_names = {data["countries"].get(cid, str(cid)) for cid in group.country_ids}
        country_conflict = len(group.country_ids) > 1
        phone_conflict = len(group.phones) > 1
        web_conflict = len(group.websites) > 1
        email_domains = {d for d in (email_domain(e) for e in group.emails) if d}
        email_conflict = len(email_domains) > 1

        severe_field_conflict = country_conflict and (phone_conflict or web_conflict)

        if group.same_fair_overlap:
            group.scenario = "B"
            group.confidence = "RISK"
            group.recommendation = "Manual review or relation dedupe"
            stats["same_fair_overlap_groups"] += 1
        elif len(group.fair_ids) > 1:
            group.scenario = "A"
        elif severe_field_conflict or (country_conflict and email_conflict and len(group.emails) > 1):
            group.scenario = "C"
        else:
            group.scenario = "A" if group.fair_ids else "C"

        if group.confidence != "RISK":
            if group.same_fair_overlap or severe_field_conflict:
                group.confidence = "RISK"
                group.recommendation = "Do not auto merge"
            elif country_conflict or phone_conflict or web_conflict or email_conflict:
                group.confidence = "REVIEW"
                group.recommendation = "Manual review suggested"
            else:
                group.confidence = "HIGH"
                group.recommendation = "Auto merge candidate"

        if group.scenario == "C" and group.confidence == "HIGH":
            group.confidence = "REVIEW"
            group.recommendation = "Manual review suggested"

        if len(group.fair_ids) > 1:
            stats["multi_fair_groups"] += 1
        stats[group.confidence.lower()] += 1

    duplicate_groups.sort(key=lambda g: (-len(g.company_ids), g.normalized_name))
    return duplicate_groups, stats


def compute_integrity(data: dict[str, Any]) -> dict[str, Any]:
    companies = data["companies"]
    fairs = data["fairs"]
    emails = data["emails"]
    fair_relations = data["fair_relations"]

    orphan_emails = sum(1 for _, company_id, _ in emails if company_id not in companies)
    orphan_rel_company = sum(1 for _, _, company_id in fair_relations if company_id not in companies)
    orphan_rel_fair = sum(1 for _, fair_id, _ in fair_relations if fair_id not in fairs)

    pair_counts: dict[tuple[int, int], int] = defaultdict(int)
    for _, fair_id, company_id in fair_relations:
        pair_counts[(fair_id, company_id)] += 1
    duplicate_pairs = sum(count - 1 for count in pair_counts.values() if count > 1)

    return {
        "company_count": len(companies),
        "email_count": len(emails),
        "fair_count": len(fairs),
        "fair_relation_count": len(fair_relations),
        "orphan_email_count": orphan_emails,
        "orphan_fair_relation_company_count": orphan_rel_company,
        "orphan_fair_relation_fair_count": orphan_rel_fair,
        "duplicate_fair_company_pair_count": duplicate_pairs,
    }


def write_csv(path: Path, groups: list[DuplicateGroup]) -> None:
    fieldnames = [
        "normalized_name",
        "company_ids",
        "original_names",
        "fair_count",
        "fair_names",
        "same_fair_overlap",
        "scenario",
        "confidence",
        "recommendation",
        "duplicate_relation_count",
        "country_ids",
        "phones",
        "websites",
        "emails",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for group in groups:
            writer.writerow(
                {
                    "normalized_name": group.normalized_name,
                    "company_ids": "|".join(str(i) for i in group.company_ids),
                    "original_names": " | ".join(group.original_names),
                    "fair_count": len(group.fair_ids),
                    "fair_names": " | ".join(sorted(group.fair_names)),
                    "same_fair_overlap": group.same_fair_overlap,
                    "scenario": group.scenario,
                    "confidence": group.confidence,
                    "recommendation": group.recommendation,
                    "duplicate_relation_count": group.duplicate_relation_count,
                    "country_ids": "|".join(str(i) for i in sorted(group.country_ids)),
                    "phones": " | ".join(sorted(group.phones)),
                    "websites": " | ".join(sorted(group.websites)),
                    "emails": " | ".join(sorted(group.emails)),
                }
            )


def sample_groups(groups: list[DuplicateGroup], confidence: str, limit: int = 10) -> list[DuplicateGroup]:
    filtered = [g for g in groups if g.confidence == confidence]
    return filtered[:limit]


def write_summary(
    path: Path,
    integrity: dict[str, Any],
    stats: dict[str, int],
    groups: list[DuplicateGroup],
) -> None:
    high = sample_groups(groups, "HIGH")
    review = sample_groups(groups, "REVIEW")
    risk = sample_groups(groups, "RISK")

    def fmt_group(group: DuplicateGroup) -> str:
        names = ", ".join(group.original_names[:3])
        if len(group.original_names) > 3:
            names += f" (+{len(group.original_names) - 3} more)"
        fairs = ", ".join(sorted(group.fair_names)[:3]) or "-"
        return (
            f"- **{group.normalized_name}** — ids={group.company_ids}; "
            f"fairs={len(group.fair_ids)} ({fairs}); scenario={group.scenario}; "
            f"same_fair_overlap={group.same_fair_overlap}; names: {names}"
        )

    lines = [
        "# UMCRM Legacy Duplicate Intelligence Summary",
        "",
        f"Generated: {datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "## General counts",
        "",
        f"- Companies: **{integrity['company_count']:,}**",
        f"- Company emails: **{integrity['email_count']:,}**",
        f"- Fairs: **{integrity['fair_count']:,}**",
        f"- Fair-company relations: **{integrity['fair_relation_count']:,}**",
        f"- Orphan emails: **{integrity['orphan_email_count']:,}**",
        f"- Orphan fair-company relations (missing company): **{integrity['orphan_fair_relation_company_count']:,}**",
        f"- Orphan fair-company relations (missing fair): **{integrity['orphan_fair_relation_fair_count']:,}**",
        f"- Duplicate fair-company pair rows: **{integrity['duplicate_fair_company_pair_count']:,}**",
        "",
        "## Duplicate summary",
        "",
        f"- Duplicate groups: **{stats['duplicate_groups']:,}**",
        f"- Duplicate company records involved: **{stats['duplicate_company_records']:,}**",
        f"- Groups spread across multiple fairs: **{stats['multi_fair_groups']:,}**",
        f"- Groups with same-fair overlap: **{stats['same_fair_overlap_groups']:,}**",
        f"- HIGH confidence: **{stats['high']:,}**",
        f"- REVIEW confidence: **{stats['review']:,}**",
        f"- RISK confidence: **{stats['risk']:,}**",
        "",
        "## Example HIGH groups (10)",
        "",
    ]
    lines.extend(fmt_group(g) for g in high)
    lines.extend(["", "## Example REVIEW groups (10)", ""])
    lines.extend(fmt_group(g) for g in review)
    lines.extend(["", "## Example RISK groups (10)", ""])
    lines.extend(fmt_group(g) for g in risk)
    lines.extend(
        [
            "",
            "## Migration recommendation",
            "",
            "1. **HIGH groups** → auto-merge to one Customer; create one `CustomerFairParticipation` per distinct fair.",
            "2. **REVIEW groups** → manual review queue before merge; compare country, phone, website, email domains.",
            "3. **RISK groups** → do not auto-merge; resolve same-fair duplicates and possible homonym companies first.",
            "4. **Scenario A (multi-fair)** → preferred legacy pattern: 1 Customer + N participations.",
            "5. **Scenario B (same-fair overlap)** → dedupe `fairtocompany` relations before migration.",
            "6. **Scenario C (field conflict)** → split or manual merge after human validation.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze UMCRM legacy duplicate companies")
    parser.add_argument("--input", required=True, help="Path to withdata_u7409970_umycrm.sql")
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parent / "reports"),
        help="Directory for generated reports",
    )
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        return 1

    print(f"Loading dump: {input_path}")
    data = load_dump(input_path)
    integrity = compute_integrity(data)
    groups, stats = build_duplicate_groups(data)

    json_path = output_dir / "umcrm_duplicate_groups.json"
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "generated_at": datetime.now(tz=UTC).isoformat(),
                "integrity": integrity,
                "stats": stats,
                "groups": [g.to_dict() for g in groups],
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )

    write_csv(output_dir / "umcrm_merge_candidates_high.csv", [g for g in groups if g.confidence == "HIGH"])
    write_csv(output_dir / "umcrm_merge_candidates_review.csv", [g for g in groups if g.confidence == "REVIEW"])
    write_csv(output_dir / "umcrm_merge_candidates_risk.csv", [g for g in groups if g.confidence == "RISK"])
    write_summary(output_dir / "umcrm_duplicate_summary.md", integrity, stats, groups)

    print("Analysis complete.")
    print(json.dumps({"integrity": integrity, "stats": stats}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
