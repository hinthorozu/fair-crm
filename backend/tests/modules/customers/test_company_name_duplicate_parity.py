"""Parity: Import Duplicate Detection and Admin Company Name Analysis share one engine.

Same name pairs must match (or not) in both flows via company_name_normalizer +
company_name_matcher (ADR-026). Admin grouping must not invent a second algorithm.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.customers.application.duplicate_company_name_grouping import (
    merge_similar_company_name_buckets,
)
from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.value_objects import CustomerSource, CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.imports.domain.services.company_name_matcher import (
    MATCH_SCORE_MIN,
    MATCH_SCORE_STRONG,
    score_company_name_pair,
)
from app.modules.imports.domain.services.company_name_normalizer import (
    company_name_comparison_key,
    normalize_import_company_name,
)
from app.modules.imports.domain.services.duplicate_detector import (
    CustomerMatchIndex,
    find_customer_match,
)

# Shared regression dataset — Import and Admin must agree on each pair.
PARITY_PAIRS: list[tuple[str, str, bool, str]] = [
    (
        "ACARLAR VAGON SAN. VE TİC. A.Ş.",
        "ACARLAR YAPI MALZEMELERİ PAZARLAMA TİCARET LTD ŞTİ",
        False,
        "single shared brand token must not duplicate",
    ),
    (
        "AKM ALARM KONTROL MERKEZİ LTD ŞTİ",
        "AKM ALARM KONTROL MERKEZİ A.Ş.",
        True,
        "same core name, different legal form — strong duplicate",
    ),
    (
        "AKM GÜVENLİK SİSTEMLERİ A.Ş.",
        "AKM ALARM KONTROL MERKEZİ LTD.",
        False,
        "only AKM shared — must not duplicate",
    ),
    (
        "ABC GIDA SAN. VE TİC. LTD. ŞTİ.",
        "ABC GIDA LIMITED SIRKETI",
        True,
        "legal suffix / abbreviation variants",
    ),
    (
        "ANADOLU GIDA",
        "ANADOLU MAKİNA",
        False,
        "same first token, distinct tails",
    ),
]


def _customer_entity(display_name: str) -> Customer:
    now = datetime.now(tz=UTC)
    return Customer.create(
        organization_id=uuid4(),
        display_name=display_name,
        legal_name=None,
        customer_type=CustomerType.LEAD,
        status=CustomerStatus.ACTIVE,
        source=CustomerSource.MANUAL,
        now=now,
    )


def _customer_model(display_name: str) -> CustomerModel:
    now = datetime.now(tz=UTC)
    return CustomerModel(
        id=uuid4(),
        organization_id=uuid4(),
        display_name=display_name,
        legal_name=None,
        normalized_name=display_name.lower(),
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )


def _import_pair_matches(left: str, right: str) -> bool:
    """Import path: score pair + index find (query left against CRM right)."""
    scored = score_company_name_pair(left, right)
    if scored is not None and scored.confidence >= MATCH_SCORE_MIN:
        return True

    crm = _customer_entity(right)
    index = CustomerMatchIndex.build([crm])
    match = index.find(
        normalize_import_company_name(left),
        raw_company_name=left,
    )
    return match is not None and match.confidence >= MATCH_SCORE_MIN


def _admin_pair_matches(left: str, right: str) -> bool:
    """Admin path: exact buckets via import comparison key + fuzzy merge at MATCH_SCORE_MIN."""
    left_model = _customer_model(left)
    right_model = _customer_model(right)
    key_left = company_name_comparison_key(display_name=left)
    key_right = company_name_comparison_key(display_name=right)

    if key_left and key_left == key_right:
        return True

    buckets: dict[str, dict] = {}
    if key_left:
        buckets[key_left] = {left_model.id: left_model}
    if key_right:
        buckets[key_right] = {right_model.id: right_model}

    if len(buckets) < 2:
        return bool(key_left and key_right and key_left == key_right)

    result = merge_similar_company_name_buckets(buckets)
    return len(result.buckets) == 1 and sum(len(m) for m in result.buckets.values()) == 2


@pytest.mark.parametrize(
    ("left", "right", "should_match", "reason"),
    PARITY_PAIRS,
    ids=[case[3] for case in PARITY_PAIRS],
)
def test_score_engine_parity_dataset(left: str, right: str, should_match: bool, reason: str):
    scored = score_company_name_pair(left, right)
    matched = scored is not None and scored.confidence >= MATCH_SCORE_MIN
    assert matched is should_match, reason
    if should_match and "legal form" in reason:
        assert scored is not None
        assert scored.confidence >= MATCH_SCORE_STRONG


@pytest.mark.parametrize(
    ("left", "right", "should_match", "reason"),
    PARITY_PAIRS,
    ids=[case[3] for case in PARITY_PAIRS],
)
def test_import_and_admin_agree_on_pair(left: str, right: str, should_match: bool, reason: str):
    import_match = _import_pair_matches(left, right)
    admin_match = _admin_pair_matches(left, right)
    assert import_match is should_match, f"import: {reason}"
    assert admin_match is should_match, f"admin: {reason}"
    assert import_match is admin_match


def test_acarlar_not_grouped_in_admin_buckets():
    left = "ACARLAR VAGON SAN. VE TİC. A.Ş."
    right = "ACARLAR YAPI MALZEMELERİ PAZARLAMA TİCARET LTD ŞTİ"
    assert _admin_pair_matches(left, right) is False
    assert find_customer_match(
        normalize_import_company_name(left),
        [_customer_entity(right)],
        raw_company_name=left,
    ) is None


def test_akm_alarm_strong_duplicate_both_flows():
    left = "AKM ALARM KONTROL MERKEZİ LTD ŞTİ"
    right = "AKM ALARM KONTROL MERKEZİ A.Ş."
    assert _import_pair_matches(left, right) is True
    assert _admin_pair_matches(left, right) is True
    scored = score_company_name_pair(left, right)
    assert scored is not None
    assert scored.confidence >= MATCH_SCORE_STRONG


def test_akm_distinct_lines_not_duplicate_both_flows():
    left = "AKM GÜVENLİK SİSTEMLERİ A.Ş."
    right = "AKM ALARM KONTROL MERKEZİ LTD."
    assert _import_pair_matches(left, right) is False
    assert _admin_pair_matches(left, right) is False


def test_admin_exact_bucket_uses_import_comparison_key():
    assert company_name_comparison_key(
        display_name="AKM ALARM KONTROL MERKEZİ LTD ŞTİ",
    ) == company_name_comparison_key(
        display_name="AKM ALARM KONTROL MERKEZİ A.Ş.",
    )
    assert company_name_comparison_key(
        display_name="ACARLAR VAGON SAN. VE TİC. A.Ş.",
    ) != company_name_comparison_key(
        display_name="ACARLAR YAPI MALZEMELERİ PAZARLAMA TİCARET LTD ŞTİ",
    )
