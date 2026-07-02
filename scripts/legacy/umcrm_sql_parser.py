"""Shared streaming parser for UMCRM legacy SQL dumps."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from umcrm_cleaning import parse_company_contact_slots

INSERT_RE = re.compile(
    r"^INSERT\s+INTO\s+`(?P<table>company|companyemail|country|fair|fairtocompany)`\s+VALUES\s+(?P<values>.+);\s*$",
    re.IGNORECASE,
)


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


def iter_insert_rows(path: Path, encoding: str) -> Iterator[tuple[str, str]]:
    with path.open("r", encoding=encoding, errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line.startswith("INSERT INTO `"):
                continue
            match = INSERT_RE.match(line)
            if not match:
                continue
            yield match.group("table"), match.group("values")


@dataclass
class CompanyRow:
    id: int
    name: str
    phone1: str | None
    web1: str | None
    phone2: str | None
    phone3: str | None
    web2: str | None
    country_id: int | None
    notes: str | None = None
    inline_emails: list[str] = field(default_factory=list)
    country_text: str | None = None


@dataclass
class FairRow:
    id: int
    name: str
    start_fair: str | None
    end_fair: str | None
    fair_area: str | None
    fair_website: str | None
    email_subject: str | None


def load_umcrm_dump(path: Path) -> dict[str, Any]:
    companies: dict[int, CompanyRow] = {}
    emails: list[tuple[int, int, str | None]] = []
    countries: dict[int, str] = {}
    fairs: dict[int, FairRow] = {}
    fair_relations: list[tuple[int, int, int]] = []

    encodings = ["utf-8", "latin5", "cp1254"]
    last_error: Exception | None = None

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
                        phones, websites, slot_emails, country_text = parse_company_contact_slots(
                            values[2],
                            values[3],
                            values[4],
                            values[5],
                            values[6],
                        )
                        companies[cid] = CompanyRow(
                            id=cid,
                            name=values[1] or "",
                            phone1=phones[0] if len(phones) > 0 else None,
                            phone2=phones[1] if len(phones) > 1 else None,
                            phone3=phones[2] if len(phones) > 2 else None,
                            web1=websites[0] if len(websites) > 0 else None,
                            web2=websites[1] if len(websites) > 1 else None,
                            country_id=int(values[7]) if values[7] else None,
                            notes=clean_text(values[9]) if len(values) > 9 else None,
                            inline_emails=slot_emails,
                            country_text=country_text,
                        )
                    elif table == "companyemail" and len(values) >= 3:
                        emails.append((int(values[0]), int(values[1]), clean_text(values[2])))
                    elif table == "country" and len(values) >= 2:
                        countries[int(values[0])] = values[1] or ""
                    elif table == "fair" and len(values) >= 2:
                        fid = int(values[0])
                        fairs[fid] = FairRow(
                            id=fid,
                            name=values[1] or "",
                            start_fair=clean_text(values[2]) if len(values) > 2 else None,
                            end_fair=clean_text(values[3]) if len(values) > 3 else None,
                            fair_area=clean_text(values[4]) if len(values) > 4 else None,
                            fair_website=clean_text(values[5]) if len(values) > 5 else None,
                            email_subject=clean_text(values[6]) if len(values) > 6 else None,
                        )
                    elif table == "fairtocompany" and len(values) >= 3:
                        fair_relations.append((int(values[0]), int(values[1]), int(values[2])))
            return {
                "companies": companies,
                "emails": emails,
                "countries": countries,
                "fairs": fairs,
                "fair_relations": fair_relations,
            }
        except Exception as exc:
            last_error = exc
            continue

    raise RuntimeError(f"Failed to parse dump with supported encodings: {last_error}")
