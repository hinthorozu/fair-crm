"""Tests for UMCRM → KYROX migration plan builder."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

LEGACY_DIR = Path(__file__).resolve().parents[1]
if str(LEGACY_DIR) not in sys.path:
    sys.path.insert(0, str(LEGACY_DIR))

from umcrm_migration_engine import (  # noqa: E402
    build_migration_plan,
    join_emails,
    parse_iso_date,
)


ORG = "00000000-0000-4000-8000-000000000010"


def _company(cid: int, name: str, **kwargs):
    return {
        "legacy_company_id": cid,
        "name_original": name,
        "name_clean": name,
        "normalized_name": name.lower(),
        "phone_values_clean": kwargs.get("phones", []),
        "website_values_clean": kwargs.get("websites", []),
        "country_id": kwargs.get("country_id", 1),
        "notes_clean": kwargs.get("notes"),
        "manual_review": kwargs.get("manual_review", False),
        "issues": kwargs.get("issues", []),
    }


def test_dry_run_counts_keep_customer():
    companies = [_company(100, "Solo Corp")]
    id_mapping = {"100": {"action": "keep", "target_legacy_company_id": 100, "merge_group_id": None}}
    plan = build_migration_plan(
        org_id=ORG,
        companies=companies,
        email_groups=[],
        fairs=[],
        relations=[],
        id_mapping=id_mapping,
        merge_plan={"auto_merge_groups": []},
    )
    assert plan.stats["customers_to_create"] == 1
    assert plan.customers[0].action == "keep"


def test_merge_customer_mapping_single_kyrox_customer():
    companies = [_company(1, "ACME A"), _company(2, "ACME B")]
    id_mapping = {
        "1": {"action": "merge", "target_legacy_company_id": 1, "merge_group_id": "grp_0001", "role": "canonical"},
        "2": {"action": "merge", "target_legacy_company_id": 1, "merge_group_id": "grp_0001", "role": "merged"},
    }
    merge_plan = {
        "auto_merge_groups": [
            {
                "merge_group_id": "grp_0001",
                "canonical_legacy_company_id": 1,
                "merged_legacy_company_ids": [1, 2],
                "field_merge": {
                    "name_clean": "ACME",
                    "emails_merged": ["a@acme.com", "b@acme.com"],
                    "emails_canonical_semicolon": "a@acme.com;b@acme.com",
                    "phones_merged": ["111"],
                    "website_canonical": "https://acme.com",
                    "country_id": 1,
                    "aliases": ["ACME B"],
                    "notes_merged": [],
                    "phone_issues": [],
                },
            }
        ]
    }
    plan = build_migration_plan(
        org_id=ORG,
        companies=companies,
        email_groups=[],
        fairs=[],
        relations=[],
        id_mapping=id_mapping,
        merge_plan=merge_plan,
    )
    assert plan.stats["customers_to_create"] == 1
    assert plan.customers[0].email == "a@acme.com;b@acme.com"
    assert plan.legacy_company_to_kyrox["1"] == plan.legacy_company_to_kyrox["2"]


def test_manual_review_separate_customers():
    companies = [_company(1, "A"), _company(2, "B")]
    id_mapping = {
        "1": {"action": "manual_review", "target_legacy_company_id": None, "merge_group_id": "grp_review_1"},
        "2": {"action": "manual_review", "target_legacy_company_id": None, "merge_group_id": "grp_review_1"},
    }
    plan = build_migration_plan(
        org_id=ORG,
        companies=companies,
        email_groups=[],
        fairs=[],
        relations=[],
        id_mapping=id_mapping,
        merge_plan={"auto_merge_groups": []},
    )
    assert plan.stats["customers_to_create"] == 2
    assert all(c.migration_review_status == "manual_review" for c in plan.customers)


def test_risk_separate_customers():
    companies = [_company(5, "Risk Co")]
    id_mapping = {"5": {"action": "risk", "target_legacy_company_id": None, "merge_group_id": "grp_risk_1"}}
    plan = build_migration_plan(
        org_id=ORG,
        companies=companies,
        email_groups=[],
        fairs=[],
        relations=[],
        id_mapping=id_mapping,
        merge_plan={"auto_merge_groups": []},
    )
    assert plan.customers[0].migration_review_status == "risk"


def test_fair_mapping():
    fairs = [
        {
            "legacy_fair_id": 10,
            "name_clean": "Demo Fair",
            "start_date_clean": "2024-01-01",
            "end_date_clean": "2024-01-05",
            "fair_area_clean": "Hall A",
            "website_clean": "https://demo.com",
            "email_subject_clean": "Welcome",
            "issues": [],
        }
    ]
    plan = build_migration_plan(
        org_id=ORG,
        companies=[],
        email_groups=[],
        fairs=fairs,
        relations=[],
        id_mapping={},
        merge_plan={"auto_merge_groups": []},
    )
    assert plan.stats["fairs_to_create"] == 1
    assert plan.fairs[0].name == "Demo Fair"
    assert plan.legacy_fair_to_kyrox["10"]


def test_participation_duplicate_skip_after_merge_resolution():
    companies = [_company(1, "A"), _company(2, "B")]
    id_mapping = {
        "1": {"action": "merge", "target_legacy_company_id": 1, "merge_group_id": "g1", "role": "canonical"},
        "2": {"action": "merge", "target_legacy_company_id": 1, "merge_group_id": "g1", "role": "merged"},
    }
    merge_plan = {
        "auto_merge_groups": [
            {
                "merge_group_id": "g1",
                "canonical_legacy_company_id": 1,
                "merged_legacy_company_ids": [1, 2],
                "field_merge": {"name_clean": "AB", "country_id": 1},
            }
        ]
    }
    relations = [
        {"legacy_fair_id": 99, "legacy_company_id": 1, "legacy_relation_id": 1, "issues": []},
        {"legacy_fair_id": 99, "legacy_company_id": 2, "legacy_relation_id": 2, "issues": []},
    ]
    fairs = [{"legacy_fair_id": 99, "name_clean": "F", "issues": []}]
    plan = build_migration_plan(
        org_id=ORG,
        companies=companies,
        email_groups=[],
        fairs=fairs,
        relations=relations,
        id_mapping=id_mapping,
        merge_plan=merge_plan,
    )
    assert plan.stats["participations_to_create"] == 1
    assert plan.stats["participation_duplicates_skipped"] == 1


def test_email_canonical_format():
    assert join_emails(["B@x.com", "a@x.com"]) == "a@x.com;b@x.com"


def test_idempotency_mapping_stable():
    companies = [_company(7, "Stable")]
    id_mapping = {"7": {"action": "keep", "target_legacy_company_id": 7, "merge_group_id": None}}
    plan1 = build_migration_plan(
        org_id=ORG,
        companies=companies,
        email_groups=[],
        fairs=[],
        relations=[],
        id_mapping=id_mapping,
        merge_plan={"auto_merge_groups": []},
    )
    plan2 = build_migration_plan(
        org_id=ORG,
        companies=companies,
        email_groups=[],
        fairs=[],
        relations=[],
        id_mapping=id_mapping,
        merge_plan={"auto_merge_groups": []},
    )
    assert plan1.customers[0].kyrox_customer_id == plan2.customers[0].kyrox_customer_id


def test_2126_date_nullify_in_fair_spec():
    fairs = [{"legacy_fair_id": 1, "name_clean": "X", "start_date_clean": None, "issues": []}]
    plan = build_migration_plan(
        org_id=ORG,
        companies=[],
        email_groups=[],
        fairs=fairs,
        relations=[],
        id_mapping={},
        merge_plan={"auto_merge_groups": []},
    )
    assert plan.fairs[0].start_date is None


def test_email_truncation_for_db_limit():
    from umcrm_migration_engine import fit_semicolon_emails

    emails = ";".join(f"user{i}@example.com" for i in range(30))
    primary, overflow = fit_semicolon_emails(emails, 255)
    assert primary is not None
    assert len(primary) <= 255
    assert overflow is not None


def test_parse_iso_date():
    from datetime import date

    assert parse_iso_date("2024-03-15") == date(2024, 3, 15)
    assert parse_iso_date(None) is None
