#!/usr/bin/env python3
"""Analyze UMCRM legacy SQL dump for data quality issues and cleaning proposals."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from analyze_umcrm_duplicates import normalize_company_name  # noqa: E402
from umcrm_sql_parser import FairRow, load_umcrm_dump  # noqa: E402

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

COMPANY_PLACEHOLDERS = {
    "test",
    "deneme",
    "null",
    "n/a",
    "na",
    "yok",
    "bilinmiyor",
    "unknown",
    "firma",
    "company",
    "-",
    ".",
    "xxx",
    "xxx xxx",
}

EMAIL_PLACEHOLDERS = {
    "test@test.com",
    "info@test.com",
    "example@example.com",
    "noemail",
    "yok",
    "null",
    "n/a",
    "na",
    "-",
    "xxx@xxx.com",
    "xxx",
}

PHONE_PLACEHOLDERS = {
    "000",
    "0000",
    "00000",
    "000000",
    "0000000",
    "00000000",
    "123456",
    "111111",
    "1234567",
    "12345678",
    "yok",
    "null",
    "n/a",
    "-",
    "0",
}

WEBSITE_PLACEHOLDERS = {
    "yok",
    "null",
    "test",
    "www.test.com",
    "test.com",
    "example.com",
    "www.example.com",
    "n/a",
    "-",
    "xxx",
}

FAIR_PLACEHOLDERS = {
    "test",
    "deneme",
    "null",
    "yok",
    "unknown",
    "-",
}

SUSPICIOUS_FAIR_DATES = {"0000-00-00", "1970-01-01", "2126-01-01"}

EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)

HTML_ENTITY_RE = re.compile(r"&(?:[a-zA-Z]+|#\d+|#x[0-9a-fA-F]+);")
MOJIBAKE_RE = re.compile(r"[ÃÄÅÆØÞÐÑÒÔÕÖ×ÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷ùúûüýþÿ]{2,}")
ENCODING_ARTIFACT_RE = re.compile(r"[\ufffd\u00c2\u00a0]")

MIN_COMPANY_NAME_LEN = 2
MAX_COMPANY_NAME_LEN = 200
MIN_PHONE_DIGITS = 7


@dataclass
class IssueRow:
    issue_type: str
    recommended_action: str
    details: str
    extra: dict[str, Any] = field(default_factory=dict)

    def csv_fields(self, base: dict[str, Any]) -> dict[str, Any]:
        row = dict(base)
        row["issue_type"] = self.issue_type
        row["recommended_action"] = self.recommended_action
        row["details"] = self.details
        return row


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


def normalize_email(value: str | None) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    return text.lower().strip()


def normalize_website_host(value: str | None) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    lowered = text.lower().strip()
    if lowered.startswith("mailto:"):
        lowered = lowered.removeprefix("mailto:")
    if not lowered.startswith(("http://", "https://")):
        lowered = "http://" + lowered
    try:
        parsed = urlparse(lowered)
        host = (parsed.netloc or parsed.path).lower()
        host = host.removeprefix("www.")
        host = host.rstrip("/")
        return host or None
    except Exception:
        return lowered


def is_valid_email(value: str) -> bool:
    if "@" not in value:
        return False
    if any(sep in value for sep in (" ", ",", ";")):
        return False
    local, domain = value.rsplit("@", 1)
    if not local or not domain or "." not in domain:
        return False
    return bool(EMAIL_RE.match(value))


def looks_like_email(value: str) -> bool:
    return "@" in value and "." in value.split("@", 1)[1]


def looks_like_phone(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    return len(digits) >= 7 and len(digits) / max(len(value), 1) > 0.5


def is_valid_website(value: str) -> bool:
    if looks_like_email(value):
        return False
    if looks_like_phone(value):
        return False
    host = normalize_website_host(value)
    if not host:
        return False
    if " " in value:
        return False
    if "." not in host and host not in WEBSITE_PLACEHOLDERS:
        return False
    return True


def needs_website_normalize(value: str) -> bool:
    text = value.strip()
    lowered = text.lower()
    if lowered.startswith(("http://", "https://")):
        return False
    if looks_like_email(text) or looks_like_phone(text):
        return False
    host = normalize_website_host(text)
    return bool(host and "." in host)


def parse_fair_date(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text in SUSPICIOUS_FAIR_DATES or text.startswith("0000"):
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt)
        except ValueError:
            continue
    return None


def company_name_issues(name: str) -> list[tuple[str, str]]:
    issues: list[tuple[str, str]] = []
    raw = name or ""
    stripped = raw.strip()

    if not stripped:
        issues.append(("empty_name", "NULLIFY"))
        return issues

    if len(stripped) < MIN_COMPANY_NAME_LEN:
        issues.append(("too_short", "MANUAL_REVIEW"))

    if len(stripped) > MAX_COMPANY_NAME_LEN:
        issues.append(("too_long", "MANUAL_REVIEW"))

    if re.fullmatch(r"\d+", stripped):
        issues.append(("digits_only", "MANUAL_REVIEW"))

    if not re.search(r"[\w\u0080-\uFFFF]", stripped, re.UNICODE):
        issues.append(("punctuation_only", "MANUAL_REVIEW"))

    folded = stripped.translate(TURKISH_CHAR_MAP).lower()
    normalized = re.sub(r"[^\w\s]", " ", folded)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if normalized in COMPANY_PLACEHOLDERS:
        issues.append(("placeholder", "MANUAL_REVIEW"))

    if HTML_ENTITY_RE.search(stripped):
        issues.append(("html_entity", "NORMALIZE"))

    if MOJIBAKE_RE.search(stripped) or ENCODING_ARTIFACT_RE.search(stripped):
        issues.append(("encoding_issue", "MANUAL_REVIEW"))

    return issues


def email_issues(email: str | None) -> list[tuple[str, str]]:
    issues: list[tuple[str, str]] = []
    if not email:
        issues.append(("empty_email", "NULLIFY"))
        return issues

    if any(sep in email for sep in (" ", ",", ";")):
        issues.append(("delimiter_in_email", "NORMALIZE"))

    lowered = email.lower().strip()
    if lowered in EMAIL_PLACEHOLDERS:
        issues.append(("placeholder", "NULLIFY"))

    if "@" not in email:
        issues.append(("no_domain", "NULLIFY"))
        return issues

    if not is_valid_email(email.replace(" ", "").replace(",", "").replace(";", "")):
        issues.append(("invalid_format", "MANUAL_REVIEW"))

    if email != email.lower():
        issues.append(("case_normalize", "NORMALIZE"))

    return issues


def phone_issues(field: str, value: str | None) -> list[tuple[str, str]]:
    issues: list[tuple[str, str]] = []
    if not value:
        issues.append(("empty_phone", "NULLIFY"))
        return issues

    stripped = value.strip()
    lowered = stripped.lower()
    if lowered in PHONE_PLACEHOLDERS or stripped in PHONE_PLACEHOLDERS:
        issues.append(("placeholder", "NULLIFY"))
        return issues

    digits = normalize_phone(value)
    if not digits:
        issues.append(("no_digits", "NULLIFY"))
        return issues

    if len(digits) < MIN_PHONE_DIGITS:
        issues.append(("too_short", "NULLIFY"))

    if set(digits) == {"0"}:
        issues.append(("all_zeros", "NULLIFY"))

    if re.search(r"[a-zA-Z\u0080-\uFFFF]", stripped):
        issues.append(("contains_letters", "MANUAL_REVIEW"))

    if re.search(r"[/\\|]", stripped) or len(stripped) > 25:
        issues.append(("contains_note", "MANUAL_REVIEW"))

    normalized = re.sub(r"\D", "", stripped)
    if normalized != digits or stripped != digits:
        issues.append(("normalize_format", "NORMALIZE"))

    return issues


def website_issues(field: str, value: str | None) -> list[tuple[str, str]]:
    issues: list[tuple[str, str]] = []
    if not value:
        issues.append(("empty_website", "NULLIFY"))
        return issues

    stripped = value.strip()
    lowered = stripped.lower()
    if lowered in WEBSITE_PLACEHOLDERS:
        issues.append(("placeholder", "NULLIFY"))
        return issues

    if looks_like_email(stripped):
        issues.append(("looks_like_email", "MANUAL_REVIEW"))

    if looks_like_phone(stripped):
        issues.append(("looks_like_phone", "MANUAL_REVIEW"))

    if not is_valid_website(stripped):
        issues.append(("invalid_website", "MANUAL_REVIEW"))
    elif needs_website_normalize(stripped):
        issues.append(("missing_scheme", "NORMALIZE"))

    return issues


def fair_issues(fair: FairRow) -> list[tuple[str, str]]:
    issues: list[tuple[str, str]] = []
    name = (fair.name or "").strip()

    if not name:
        issues.append(("empty_fair_name", "MANUAL_REVIEW"))
    else:
        folded = name.translate(TURKISH_CHAR_MAP).lower()
        if folded in FAIR_PLACEHOLDERS:
            issues.append(("placeholder_fair_name", "MANUAL_REVIEW"))

    for label, raw in (("start_fair", fair.start_fair), ("end_fair", fair.end_fair)):
        if not raw:
            issues.append((f"empty_{label}", "NULLIFY"))
            continue
        if raw.strip() in SUSPICIOUS_FAIR_DATES or raw.strip().startswith("0000"):
            issues.append((f"suspicious_{label}", "NULLIFY"))
        elif raw.strip().startswith("2126"):
            issues.append((f"future_{label}", "NULLIFY"))

    start = parse_fair_date(fair.start_fair)
    end = parse_fair_date(fair.end_fair)
    if start and end and end < start:
        issues.append(("end_before_start", "MANUAL_REVIEW"))

    if fair.fair_area:
        area = fair.fair_area.strip()
        if area.lower() in {"yok", "null", "-", "n/a", "test"}:
            issues.append(("placeholder_fair_area", "NULLIFY"))
    else:
        issues.append(("empty_fair_area", "KEEP"))

    if fair.fair_website:
        ws = fair.fair_website.strip()
        if ws.lower() in WEBSITE_PLACEHOLDERS:
            issues.append(("placeholder_fair_website", "NULLIFY"))
        elif not is_valid_website(ws):
            issues.append(("invalid_fair_website", "MANUAL_REVIEW"))
        elif needs_website_normalize(ws):
            issues.append(("normalize_fair_website", "NORMALIZE"))
    else:
        issues.append(("empty_fair_website", "KEEP"))

    if fair.email_subject:
        subj = fair.email_subject.strip()
        if subj.lower() in {"null", "yok", "-", "test"}:
            issues.append(("placeholder_email_subject", "NULLIFY"))
        else:
            issues.append(("email_subject_present", "KEEP"))
    else:
        issues.append(("empty_email_subject", "KEEP"))

    return issues


def analyze(data: dict[str, Any]) -> dict[str, Any]:
    companies = data["companies"]
    emails = data["emails"]
    countries = data["countries"]
    fairs = data["fairs"]
    fair_relations = data["fair_relations"]

    company_ids = set(companies.keys())
    fair_ids = set(fairs.keys())
    country_ids = set(countries.keys())

    bad_names: list[dict[str, Any]] = []
    name_issue_counts: Counter[str] = Counter()
    action_counts: Counter[str] = Counter()

    for company in companies.values():
        found = company_name_issues(company.name)
        for issue_type, action in found:
            name_issue_counts[issue_type] += 1
            action_counts[action] += 1
            bad_names.append(
                {
                    "company_id": company.id,
                    "company_name": company.name,
                    "issue_type": issue_type,
                    "recommended_action": action,
                    "details": issue_type.replace("_", " "),
                }
            )

    invalid_emails: list[dict[str, Any]] = []
    email_issue_counts: Counter[str] = Counter()
    emails_by_company: dict[int, list[tuple[int, str]]] = defaultdict(list)
    email_to_companies: dict[str, set[int]] = defaultdict(set)

    for email_id, company_id, email in emails:
        emails_by_company[company_id].append((email_id, email or ""))
        norm = normalize_email(email)
        if norm:
            email_to_companies[norm].add(company_id)

        found = email_issues(email)
        for issue_type, action in found:
            email_issue_counts[issue_type] += 1
            action_counts[action] += 1
            invalid_emails.append(
                {
                    "email_id": email_id,
                    "company_id": company_id,
                    "email": email or "",
                    "issue_type": issue_type,
                    "recommended_action": action,
                    "details": issue_type.replace("_", " "),
                }
            )

    for company_id, rows in emails_by_company.items():
        seen: dict[str, list[int]] = defaultdict(list)
        for email_id, email in rows:
            norm = normalize_email(email)
            if norm:
                seen[norm].append(email_id)
        for norm, ids in seen.items():
            if len(ids) > 1:
                email_issue_counts["duplicate_same_company"] += len(ids)
                action_counts["MERGE"] += len(ids)
                for eid in ids:
                    invalid_emails.append(
                        {
                            "email_id": eid,
                            "company_id": company_id,
                            "email": next(e for i, e in rows if i == eid),
                            "issue_type": "duplicate_same_company",
                            "recommended_action": "MERGE",
                            "details": f"duplicate normalized email {norm}",
                        }
                    )

    for norm, cids in email_to_companies.items():
        if len(cids) > 1:
            email_issue_counts["duplicate_cross_company"] += len(cids)
            action_counts["MANUAL_REVIEW"] += len(cids)
            for cid in sorted(cids):
                for email_id, email in emails_by_company[cid]:
                    if normalize_email(email) == norm:
                        invalid_emails.append(
                            {
                                "email_id": email_id,
                                "company_id": cid,
                                "email": email,
                                "issue_type": "duplicate_cross_company",
                                "recommended_action": "MANUAL_REVIEW",
                                "details": f"shared email across {len(cids)} companies",
                            }
                        )

    suspicious_phones: list[dict[str, Any]] = []
    phone_issue_counts: Counter[str] = Counter()

    for company in companies.values():
        phones_raw = [
            ("Phone1", company.phone1),
            ("Phone2", company.phone2),
            ("Phone3", company.phone3),
        ]
        normalized_seen: dict[str, list[str]] = defaultdict(list)
        for field_name, phone in phones_raw:
            found = phone_issues(field_name, phone)
            for issue_type, action in found:
                phone_issue_counts[issue_type] += 1
                action_counts[action] += 1
                suspicious_phones.append(
                    {
                        "company_id": company.id,
                        "company_name": company.name,
                        "field": field_name,
                        "phone": phone or "",
                        "issue_type": issue_type,
                        "recommended_action": action,
                        "details": issue_type.replace("_", " "),
                    }
                )
            norm = normalize_phone(phone)
            if norm:
                normalized_seen[norm].append(field_name)

        for norm, fields in normalized_seen.items():
            if len(fields) > 1:
                phone_issue_counts["duplicate_same_company"] += len(fields)
                action_counts["MERGE"] += len(fields)
                for field_name in fields:
                    phone_val = getattr(company, field_name.lower())
                    suspicious_phones.append(
                        {
                            "company_id": company.id,
                            "company_name": company.name,
                            "field": field_name,
                            "phone": phone_val or "",
                            "issue_type": "duplicate_same_company",
                            "recommended_action": "MERGE",
                            "details": f"duplicate normalized phone {norm}",
                        }
                    )

    suspicious_websites: list[dict[str, Any]] = []
    website_issue_counts: Counter[str] = Counter()

    for company in companies.values():
        webs = [("Web1", company.web1), ("Web2", company.web2)]
        normalized_seen: dict[str, list[str]] = defaultdict(list)
        for field_name, web in webs:
            found = website_issues(field_name, web)
            for issue_type, action in found:
                website_issue_counts[issue_type] += 1
                action_counts[action] += 1
                suspicious_websites.append(
                    {
                        "company_id": company.id,
                        "company_name": company.name,
                        "field": field_name,
                        "website": web or "",
                        "issue_type": issue_type,
                        "recommended_action": action,
                        "details": issue_type.replace("_", " "),
                    }
                )
            host = normalize_website_host(web)
            if host:
                normalized_seen[host].append(field_name)

        for host, fields in normalized_seen.items():
            if len(fields) > 1:
                website_issue_counts["duplicate_same_company"] += len(fields)
                action_counts["MERGE"] += len(fields)
                for field_name in fields:
                    web_val = getattr(company, field_name.lower())
                    suspicious_websites.append(
                        {
                            "company_id": company.id,
                            "company_name": company.name,
                            "field": field_name,
                            "website": web_val or "",
                            "issue_type": "duplicate_same_company",
                            "recommended_action": "MERGE",
                            "details": f"duplicate normalized website {host}",
                        }
                    )

    country_issue_counts: Counter[str] = Counter()
    country_distribution: Counter[str] = Counter()
    missing_country_ids: list[int] = []
    invalid_country_refs: list[dict[str, Any]] = []

    for company in companies.values():
        if company.country_id is None:
            country_issue_counts["empty_country_id"] += 1
            action_counts["NULLIFY"] += 1
            missing_country_ids.append(company.id)
        elif company.country_id not in country_ids:
            country_issue_counts["invalid_country_id"] += 1
            action_counts["MANUAL_REVIEW"] += 1
            invalid_country_refs.append(
                {
                    "company_id": company.id,
                    "country_id": company.country_id,
                    "issue_type": "invalid_country_id",
                    "recommended_action": "MANUAL_REVIEW",
                }
            )
        else:
            country_distribution[countries[company.country_id]] += 1

    suspicious_fairs: list[dict[str, Any]] = []
    fair_issue_counts: Counter[str] = Counter()
    fair_name_groups: dict[str, list[int]] = defaultdict(list)

    for fair in fairs.values():
        folded = (fair.name or "").strip().translate(TURKISH_CHAR_MAP).lower()
        if folded:
            fair_name_groups[folded].append(fair.id)
        found = fair_issues(fair)
        for issue_type, action in found:
            fair_issue_counts[issue_type] += 1
            action_counts[action] += 1
            suspicious_fairs.append(
                {
                    "fair_id": fair.id,
                    "fair_name": fair.name,
                    "start_fair": fair.start_fair or "",
                    "end_fair": fair.end_fair or "",
                    "fair_area": fair.fair_area or "",
                    "fair_website": fair.fair_website or "",
                    "email_subject": fair.email_subject or "",
                    "issue_type": issue_type,
                    "recommended_action": action,
                    "details": issue_type.replace("_", " "),
                }
            )

    for folded, ids in fair_name_groups.items():
        if len(ids) > 1:
            fair_issue_counts["duplicate_fair_name"] += len(ids)
            action_counts["MANUAL_REVIEW"] += len(ids)
            for fid in ids:
                fair = fairs[fid]
                suspicious_fairs.append(
                    {
                        "fair_id": fid,
                        "fair_name": fair.name,
                        "start_fair": fair.start_fair or "",
                        "end_fair": fair.end_fair or "",
                        "fair_area": fair.fair_area or "",
                        "fair_website": fair.fair_website or "",
                        "email_subject": fair.email_subject or "",
                        "issue_type": "duplicate_fair_name",
                        "recommended_action": "MANUAL_REVIEW",
                        "details": f"duplicate name group size {len(ids)}",
                    }
                )

    suspicious_relations: list[dict[str, Any]] = []
    relation_issue_counts: Counter[str] = Counter()
    pair_counts: Counter[tuple[int, int]] = Counter()
    company_fair_counts: Counter[tuple[int, int]] = Counter()

    for rel_id, fair_id, company_id in fair_relations:
        pair_counts[(fair_id, company_id)] += 1
        company_fair_counts[(company_id, fair_id)] += 1

        if company_id not in company_ids:
            relation_issue_counts["missing_company"] += 1
            action_counts["DROP_ROW"] += 1
            suspicious_relations.append(
                {
                    "relation_id": rel_id,
                    "fair_id": fair_id,
                    "company_id": company_id,
                    "issue_type": "missing_company",
                    "recommended_action": "DROP_ROW",
                    "details": "company_id not in company table",
                }
            )
        if fair_id not in fair_ids:
            relation_issue_counts["missing_fair"] += 1
            action_counts["DROP_ROW"] += 1
            suspicious_relations.append(
                {
                    "relation_id": rel_id,
                    "fair_id": fair_id,
                    "company_id": company_id,
                    "issue_type": "missing_fair",
                    "recommended_action": "DROP_ROW",
                    "details": "fair_id not in fair table",
                }
            )

    for (fair_id, company_id), count in pair_counts.items():
        if count > 1:
            relation_issue_counts["duplicate_relation"] += count
            action_counts["DROP_DUPLICATE_RELATION"] += count - 1
            action_counts["KEEP"] += 1
            suspicious_relations.append(
                {
                    "relation_id": "",
                    "fair_id": fair_id,
                    "company_id": company_id,
                    "issue_type": "duplicate_relation",
                    "recommended_action": "DROP_DUPLICATE_RELATION",
                    "details": f"{count} rows for same fair-company pair",
                }
            )

    norm_name_to_companies: dict[str, list[int]] = defaultdict(list)
    for company in companies.values():
        norm = normalize_company_name(company.name)
        if norm:
            norm_name_to_companies[norm].append(company.id)

    merge_relation_conflicts = 0
    for norm, cids in norm_name_to_companies.items():
        if len(cids) < 2:
            continue
        fair_to_companies: dict[int, list[int]] = defaultdict(list)
        for cid in cids:
            for _, fair_id, comp_id in fair_relations:
                if comp_id == cid:
                    fair_to_companies[fair_id].append(cid)
        for fair_id, involved in fair_to_companies.items():
            unique = set(involved)
            if len(unique) > 1:
                merge_relation_conflicts += len(involved)
                relation_issue_counts["merge_conflict"] += len(involved)
                action_counts["MANUAL_REVIEW"] += len(involved)
                for cid in sorted(unique):
                    suspicious_relations.append(
                        {
                            "relation_id": "",
                            "fair_id": fair_id,
                            "company_id": cid,
                            "issue_type": "merge_conflict",
                            "recommended_action": "MANUAL_REVIEW",
                            "details": f"duplicate group '{norm}' shares fair {fair_id}",
                        }
                    )

    return {
        "dataset": {
            "companies": len(companies),
            "emails": len(emails),
            "countries": len(countries),
            "fairs": len(fairs),
            "relations": len(fair_relations),
        },
        "bad_names": bad_names,
        "invalid_emails": invalid_emails,
        "suspicious_phones": suspicious_phones,
        "suspicious_websites": suspicious_websites,
        "suspicious_fairs": suspicious_fairs,
        "suspicious_relations": suspicious_relations,
        "country_distribution": dict(country_distribution.most_common()),
        "issue_counts": {
            "company_names": dict(name_issue_counts),
            "emails": dict(email_issue_counts),
            "phones": dict(phone_issue_counts),
            "websites": dict(website_issue_counts),
            "countries": dict(country_issue_counts),
            "fairs": dict(fair_issue_counts),
            "relations": dict(relation_issue_counts),
        },
        "action_counts": dict(action_counts),
        "invalid_country_refs": invalid_country_refs,
        "missing_country_ids": missing_country_ids,
    }


def dedupe_rows(rows: list[dict[str, Any]], key_fields: list[str]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        key = tuple(row.get(f) for f in key_fields)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_cleaning_rules_md() -> str:
    lines = [
        "# UMCRM Cleaning Rules Proposal",
        "",
        "Recommended actions per issue type. Risky or ambiguous cases are marked **MANUAL_REVIEW**.",
        "",
        "## Company name",
        "",
        "| Issue | Action | Notes |",
        "| --- | --- | --- |",
        "| empty_name | NULLIFY | Blank name before migration |",
        "| too_short | MANUAL_REVIEW | Length < 2 |",
        "| too_long | MANUAL_REVIEW | Length > 200 |",
        "| digits_only | MANUAL_REVIEW | Not a meaningful company name |",
        "| punctuation_only | MANUAL_REVIEW | Symbols only |",
        "| placeholder | MANUAL_REVIEW or DROP_ROW | test, deneme, null, yok, etc. |",
        "| html_entity | NORMALIZE | Decode HTML entities |",
        "| encoding_issue | MANUAL_REVIEW | Mojibake / replacement chars |",
        "",
        "## Email",
        "",
        "| Issue | Action | Notes |",
        "| --- | --- | --- |",
        "| empty_email | NULLIFY | |",
        "| placeholder | NULLIFY | test@test.com, noemail, yok |",
        "| invalid_format | MANUAL_REVIEW | Malformed address |",
        "| no_domain | NULLIFY | Missing @ or TLD |",
        "| delimiter_in_email | NORMALIZE | Strip spaces/commas/semicolons |",
        "| case_normalize | NORMALIZE | Lowercase for dedup |",
        "| duplicate_same_company | MERGE | Keep one row per company |",
        "| duplicate_cross_company | MANUAL_REVIEW | Possible shared inbox or duplicate companies |",
        "",
        "## Phone",
        "",
        "| Issue | Action | Notes |",
        "| --- | --- | --- |",
        "| empty_phone | NULLIFY | |",
        "| placeholder | NULLIFY | 000000, 123456, yok |",
        "| too_short | NULLIFY | < 7 digits |",
        "| all_zeros | NULLIFY | |",
        "| contains_letters | MANUAL_REVIEW | Notes embedded in phone field |",
        "| contains_note | MANUAL_REVIEW | Long or slash-separated values |",
        "| normalize_format | NORMALIZE | Strip formatting chars |",
        "| duplicate_same_company | MERGE | Same digits in Phone1/2/3 |",
        "",
        "## Website",
        "",
        "| Issue | Action | Notes |",
        "| --- | --- | --- |",
        "| empty_website | NULLIFY | |",
        "| placeholder | NULLIFY | test.com, yok |",
        "| looks_like_email | MANUAL_REVIEW | Move to email if valid |",
        "| looks_like_phone | MANUAL_REVIEW | Move to phone if valid |",
        "| invalid_website | MANUAL_REVIEW | |",
        "| missing_scheme | NORMALIZE | Prefix https:// |",
        "| duplicate_same_company | MERGE | Same host in Web1/Web2 |",
        "",
        "## Country",
        "",
        "| Issue | Action | Notes |",
        "| --- | --- | --- |",
        "| empty_country_id | NULLIFY | |",
        "| invalid_country_id | MANUAL_REVIEW | FK not in country table |",
        "",
        "## Fair",
        "",
        "| Issue | Action | Notes |",
        "| --- | --- | --- |",
        "| empty_fair_name | MANUAL_REVIEW | |",
        "| placeholder_fair_name | MANUAL_REVIEW | |",
        "| duplicate_fair_name | MANUAL_REVIEW | May need fair merge |",
        "| suspicious/future dates | NULLIFY | 0000-00-00, 1970-01-01, 2126-01-01 |",
        "| end_before_start | MANUAL_REVIEW | |",
        "| placeholder_fair_area | NULLIFY | |",
        "| empty_fair_area | KEEP | Optional metadata |",
        "| invalid_fair_website | MANUAL_REVIEW | |",
        "| normalize_fair_website | NORMALIZE | |",
        "| email_subject_present | KEEP | Useful for campaign migration context |",
        "| placeholder_email_subject | NULLIFY | |",
        "",
        "## Fair-to-company relations",
        "",
        "| Issue | Action | Notes |",
        "| --- | --- | --- |",
        "| missing_company | DROP_ROW | Orphan relation |",
        "| missing_fair | DROP_ROW | Orphan relation |",
        "| duplicate_relation | DROP_DUPLICATE_RELATION | Keep one row per (FairId, CompanyId) |",
        "| merge_conflict | MANUAL_REVIEW | After company MERGE, dedupe participations |",
        "",
    ]
    return "\n".join(lines) + "\n"


def build_summary_md(result: dict[str, Any], input_path: Path) -> str:
    ds = result["dataset"]
    ic = result["issue_counts"]
    ac = result["action_counts"]
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    def sum_issues(key: str) -> int:
        return sum(ic.get(key, {}).values())

    lines = [
        "# UMCRM Data Quality Summary",
        "",
        f"Generated: {now}",
        f"Source: `{input_path}`",
        "",
        "## Dataset",
        "",
        f"- Companies: **{ds['companies']:,}**",
        f"- Emails: **{ds['emails']:,}**",
        f"- Countries: **{ds['countries']:,}**",
        f"- Fairs: **{ds['fairs']:,}**",
        f"- Fair-company relations: **{ds['relations']:,}**",
        "",
        "## Issue totals (occurrences)",
        "",
        f"- Company name issues: **{sum_issues('company_names'):,}** ({len(result['bad_names']):,} rows in CSV)",
        f"- Email issues: **{sum_issues('emails'):,}** ({len(result['invalid_emails']):,} rows in CSV)",
        f"- Phone issues: **{sum_issues('phones'):,}** ({len(result['suspicious_phones']):,} rows in CSV)",
        f"- Website issues: **{sum_issues('websites'):,}** ({len(result['suspicious_websites']):,} rows in CSV)",
        f"- Country issues: **{sum_issues('countries'):,}**",
        f"- Fair issues: **{sum_issues('fairs'):,}** ({len(result['suspicious_fairs']):,} rows in CSV)",
        f"- Relation issues: **{sum_issues('relations'):,}** ({len(result['suspicious_relations']):,} rows in CSV)",
        "",
        "## Top company name issues",
        "",
    ]
    for k, v in Counter(ic.get("company_names", {})).most_common(10):
        lines.append(f"- {k}: {v:,}")

    lines.extend(["", "## Top email issues", ""])
    for k, v in Counter(ic.get("emails", {})).most_common(10):
        lines.append(f"- {k}: {v:,}")

    lines.extend(["", "## Recommended actions (occurrence count)", ""])
    for action in (
        "KEEP",
        "NORMALIZE",
        "MERGE",
        "NULLIFY",
        "DROP_ROW",
        "DROP_DUPLICATE_RELATION",
        "MANUAL_REVIEW",
    ):
        if ac.get(action):
            lines.append(f"- {action}: **{ac[action]:,}**")

    lines.extend(["", "## Country distribution (top 15)", ""])
    for name, count in list(result["country_distribution"].items())[:15]:
        lines.append(f"- {name}: {count:,}")

    lines.extend(
        [
            "",
            "## Migration notes",
            "",
            "- Company duplicate merge (separate report) may create fair participation conflicts — see `merge_conflict` relation issues.",
            "- EmailSubject on fairs is mostly metadata; KEEP when meaningful, NULLIFY placeholders.",
            "- Automatic NULLIFY/DROP is safe for obvious placeholders; MANUAL_REVIEW required for cross-company email duplicates and bad company names.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def write_reports(result: dict[str, Any], reports_dir: Path, input_path: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)

    issues_json = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": str(input_path),
        "dataset": result["dataset"],
        "issue_counts": result["issue_counts"],
        "action_counts": result["action_counts"],
        "country_distribution": result["country_distribution"],
    }
    (reports_dir / "umcrm_data_quality_issues.json").write_text(
        json.dumps(issues_json, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    (reports_dir / "umcrm_data_quality_summary.md").write_text(
        build_summary_md(result, input_path),
        encoding="utf-8",
    )
    (reports_dir / "umcrm_cleaning_rules_proposal.md").write_text(
        build_cleaning_rules_md(),
        encoding="utf-8",
    )

    write_csv(
        reports_dir / "umcrm_companies_bad_names.csv",
        dedupe_rows(result["bad_names"], ["company_id", "issue_type"]),
        ["company_id", "company_name", "issue_type", "recommended_action", "details"],
    )
    write_csv(
        reports_dir / "umcrm_emails_invalid.csv",
        dedupe_rows(result["invalid_emails"], ["email_id", "issue_type"]),
        ["email_id", "company_id", "email", "issue_type", "recommended_action", "details"],
    )
    write_csv(
        reports_dir / "umcrm_phones_suspicious.csv",
        dedupe_rows(result["suspicious_phones"], ["company_id", "field", "issue_type"]),
        [
            "company_id",
            "company_name",
            "field",
            "phone",
            "issue_type",
            "recommended_action",
            "details",
        ],
    )
    write_csv(
        reports_dir / "umcrm_websites_suspicious.csv",
        dedupe_rows(result["suspicious_websites"], ["company_id", "field", "issue_type"]),
        [
            "company_id",
            "company_name",
            "field",
            "website",
            "issue_type",
            "recommended_action",
            "details",
        ],
    )
    write_csv(
        reports_dir / "umcrm_fairs_suspicious.csv",
        dedupe_rows(result["suspicious_fairs"], ["fair_id", "issue_type"]),
        [
            "fair_id",
            "fair_name",
            "start_fair",
            "end_fair",
            "fair_area",
            "fair_website",
            "email_subject",
            "issue_type",
            "recommended_action",
            "details",
        ],
    )
    write_csv(
        reports_dir / "umcrm_relations_suspicious.csv",
        dedupe_rows(
            result["suspicious_relations"],
            ["relation_id", "fair_id", "company_id", "issue_type"],
        ),
        [
            "relation_id",
            "fair_id",
            "company_id",
            "issue_type",
            "recommended_action",
            "details",
        ],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze UMCRM dump data quality")
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to withdata_u7409970_umycrm.sql",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=SCRIPT_DIR / "reports",
        help="Output directory for reports",
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

    print("Analyzing data quality ...")
    result = analyze(data)
    write_reports(result, args.reports_dir, args.input)
    print(f"Reports written to {args.reports_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
