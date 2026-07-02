"""Unit tests for UMCRM merge plan builder."""

from __future__ import annotations

import sys
from pathlib import Path

LEGACY_DIR = Path(__file__).resolve().parents[1]
if str(LEGACY_DIR) not in sys.path:
    sys.path.insert(0, str(LEGACY_DIR))

from umcrm_merge_plan import (  # noqa: E402
    build_field_merge_plan,
    build_merge_plan,
    evaluate_high_group_for_auto_merge,
    has_same_fair_conflict,
    merge_emails,
    merge_phones,
    select_canonical_company_id,
)


def _company(
    cid: int,
    name: str,
    *,
    manual_review: bool = False,
    phones: list[str] | None = None,
    websites: list[str] | None = None,
    country_id: int = 1,
    notes: str | None = None,
) -> dict:
    return {
        "legacy_company_id": cid,
        "name_original": name,
        "name_clean": name,
        "normalized_name": name.lower(),
        "phone_values_clean": phones or [],
        "website_values_clean": websites or [],
        "country_id": country_id,
        "notes_clean": notes,
        "manual_review": manual_review,
        "issues": [],
    }


def test_select_canonical_prefers_most_fair_participations():
    companies = {
        10: _company(10, "Alpha Corp"),
        20: _company(20, "Alpha Corporation"),
    }
    relations = {10: [1, 2], 20: [1]}
    emails = {10: ["a@alpha.com"], 20: []}
    canonical, _ = select_canonical_company_id([10, 20], companies, relations, emails)
    assert canonical == 10


def test_high_group_auto_merge():
    companies = [
        _company(1, "ACME A", phones=["1111111111"], websites=["https://acme.com"]),
        _company(2, "ACME B", phones=["1111111111"], websites=["https://acme.com"]),
    ]
    emails = [
        {"legacy_company_id": 1, "emails_clean": ["info@acme.com"], "emails_original": [], "issues": []},
        {"legacy_company_id": 2, "emails_clean": ["sales@acme.com"], "emails_original": [], "issues": []},
    ]
    relations = [
        {"legacy_fair_id": 1, "legacy_company_id": 1, "legacy_relation_id": 1, "issues": []},
        {"legacy_fair_id": 2, "legacy_company_id": 2, "legacy_relation_id": 2, "issues": []},
    ]
    groups = [
        {
            "normalized_name": "acme",
            "company_ids": [1, 2],
            "original_names": ["ACME A", "ACME B"],
            "confidence": "HIGH",
            "same_fair_overlap": False,
            "scenario": "A",
            "recommendation": "Auto merge candidate",
        }
    ]
    result = build_merge_plan(companies, emails, relations, groups)
    assert len(result["auto_merge_plans"]) == 1
    assert result["id_mapping"]["2"]["action"] == "merge"
    assert result["id_mapping"]["2"]["target_legacy_company_id"] == result["auto_merge_plans"][0][
        "canonical_legacy_company_id"
    ]


def test_same_fair_conflict_blocks_auto_merge():
    companies = [_company(1, "A"), _company(2, "B")]
    relations = [
        {"legacy_fair_id": 99, "legacy_company_id": 1, "legacy_relation_id": 1, "issues": []},
        {"legacy_fair_id": 99, "legacy_company_id": 2, "legacy_relation_id": 2, "issues": []},
    ]
    groups = [
        {
            "normalized_name": "acme",
            "company_ids": [1, 2],
            "original_names": ["A", "B"],
            "confidence": "HIGH",
            "same_fair_overlap": True,
            "scenario": "B",
        }
    ]
    result = build_merge_plan(companies, [], relations, groups)
    assert result["auto_merge_plans"] == []
    assert len(result["manual_review_queue"]) == 1
    assert "same_fair_conflict" in result["manual_review_queue"][0]["blocked_reasons"]


def test_manual_review_company_blocks_auto_merge():
    companies = [_company(1, "A"), _company(2, "B", manual_review=True)]
    groups = [
        {
            "normalized_name": "acme",
            "company_ids": [1, 2],
            "original_names": ["A", "B"],
            "confidence": "HIGH",
            "same_fair_overlap": False,
        }
    ]
    company_map = {c["legacy_company_id"]: c for c in companies}
    can_auto, blocked, _ = evaluate_high_group_for_auto_merge(
        groups[0], company_map, {1: [1], 2: [2]}, {1: [], 2: []}
    )
    assert can_auto is False
    assert "manual_review_company" in blocked


def test_country_mismatch_blocks_auto_merge():
    companies = [_company(1, "A", country_id=1), _company(2, "B", country_id=2)]
    groups = [
        {
            "normalized_name": "acme",
            "company_ids": [1, 2],
            "original_names": ["A", "B"],
            "confidence": "HIGH",
            "same_fair_overlap": False,
        }
    ]
    company_map = {c["legacy_company_id"]: c for c in companies}
    can_auto, blocked, _ = evaluate_high_group_for_auto_merge(
        groups[0], company_map, {1: [1], 2: [2]}, {1: [], 2: []}
    )
    assert can_auto is False
    assert "country_mismatch" in blocked


def test_email_union_merge():
    merged = merge_emails([1, 2], {1: ["B@x.com", "a@x.com"], 2: ["a@x.com"]})
    assert merged == ["a@x.com", "b@x.com"]


def test_phone_union_merge_dedupes_digits():
    companies = {
        1: _company(1, "A", phones=["532-111-1111"]),
        2: _company(2, "B", phones=["5321111111"]),
    }
    merged, issues = merge_phones([1, 2], companies)
    assert len(merged) == 1
    assert issues == []


def test_non_duplicate_keep_mapping():
    companies = [_company(1, "Only One")]
    result = build_merge_plan(companies, [], [], [])
    assert result["id_mapping"]["1"]["action"] == "keep"
    assert result["stats"].keep_records == 1


def test_review_group_manual_review():
    companies = [_company(1, "A"), _company(2, "B")]
    groups = [
        {
            "normalized_name": "acme",
            "company_ids": [1, 2],
            "original_names": ["A", "B"],
            "confidence": "REVIEW",
            "same_fair_overlap": False,
        }
    ]
    result = build_merge_plan(companies, [], [], groups)
    assert result["auto_merge_plans"] == []
    assert result["id_mapping"]["1"]["action"] == "manual_review"
    assert result["id_mapping"]["2"]["action"] == "manual_review"


def test_risk_group_risk_action():
    companies = [_company(1, "A"), _company(2, "B")]
    groups = [
        {
            "normalized_name": "acme",
            "company_ids": [1, 2],
            "original_names": ["A", "B"],
            "confidence": "RISK",
            "same_fair_overlap": True,
        }
    ]
    result = build_merge_plan(companies, [], [], groups)
    assert result["id_mapping"]["1"]["action"] == "risk"
    assert len(result["risk_groups"]) == 1


def test_field_merge_plan_email_semicolon_format():
    companies = {
        1: _company(1, "ACME"),
        2: _company(2, "ACME INC"),
    }
    emails = {1: ["z@acme.com"], 2: ["a@acme.com"]}
    plan = build_field_merge_plan([1, 2], 1, companies, emails)
    assert plan["emails_canonical_semicolon"] == "a@acme.com;z@acme.com"
    assert "ACME INC" in plan["aliases"]


def test_has_same_fair_conflict_detects_overlap():
    conflict, details = has_same_fair_conflict([1, 2], {1: [5, 6], 2: [5, 7]})
    assert conflict is True
    assert details[0]["legacy_fair_id"] == 5
