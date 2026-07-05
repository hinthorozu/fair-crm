from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.customers.application.duplicate_company_name_grouping import (
    merge_similar_company_name_buckets,
)
from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.imports.domain.services.company_name_matcher import score_company_name_pair


def _model(display_name: str, *, legal_name: str | None = None) -> CustomerModel:
    now = datetime.now(tz=UTC)
    return CustomerModel(
        id=uuid4(),
        organization_id=uuid4(),
        display_name=display_name,
        legal_name=legal_name,
        normalized_name=display_name.lower(),
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )


def test_merge_similar_company_name_buckets_unions_probable_matches():
    first = _model("ABC GIDA LTD")
    second = _model("ABC GIDA LIMITED SIRKETI")
    buckets = {
        "ABC GIDA": {first.id: first},
        "ABC GIDA LIMITED": {second.id: second},
    }

    result = merge_similar_company_name_buckets(buckets)

    assert len(result.buckets) == 1
    only_group = next(iter(result.buckets.values()))
    assert {first.id, second.id} == set(only_group.keys())
    assert len(result.merge_events) == 1
    assert result.merge_events[0].match_type == "fuzzy"


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("ABC", "ABC KIMYA"),
        ("ABC KIMYA", "ABC TEKSTIL"),
        ("ABC TEKNOLOJI", "ABC TEKSTIL"),
        ("SDK Teknoloji Mimarlık", "SDK Yazılım Hizmetleri"),
    ],
)
def test_score_company_name_pair_rejects_short_hub_and_distinct_tails(left: str, right: str):
    assert score_company_name_pair(left, right) is None


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("ABC Kimya", "ABC Kimya Ltd Şti"),
        ("SDK Teknoloji Mimarlık", "SDK Teknoloji Mimarlık Ltd Şti"),
        ("SDK Yazılım Hizmetleri", "SDK Yazilim Hizmetleri San Tic Ltd Sti"),
    ],
)
def test_score_company_name_pair_allows_legal_suffix_variants(left: str, right: str):
    scored = score_company_name_pair(left, right)
    assert scored is not None
    assert scored.confidence >= 85


def test_short_hub_buckets_do_not_fuzzy_merge_with_longer_names():
    abc = _model("ABC")
    kimya = _model("ABC KİMYA")
    tekstil = _model("ABC TEKSTİL")
    buckets = {
        "ABC": {abc.id: abc},
        "ABC KIMYA": {kimya.id: kimya},
        "ABC TEKSTIL": {tekstil.id: tekstil},
    }

    result = merge_similar_company_name_buckets(buckets)

    assert len(result.buckets) == 3
    assert len(result.merge_events) == 0


def test_sdk_distinct_business_lines_stay_separate():
    mimarlik = _model("SDK Teknoloji Mimarlık")
    yazilim = _model("SDK Yazılım Hizmetleri")
    buckets = {
        "SDK TEKNOLOJI MIMARLIK": {mimarlik.id: mimarlik},
        "SDK YAZILIM HIZMETLERI": {yazilim.id: yazilim},
    }

    result = merge_similar_company_name_buckets(buckets)

    assert len(result.buckets) == 2
    assert len(result.merge_events) == 0


def test_sdk_same_line_with_legal_suffix_merges():
    short = _model("SDK Teknoloji Mimarlık")
    long_form = _model("SDK Teknoloji Mimarlık Ltd Şti")
    buckets = {
        "SDK TEKNOLOJI MIMARLIK": {short.id: short},
        "SDK TEKNOLOJI MIMARLIK LTD": {long_form.id: long_form},
    }

    result = merge_similar_company_name_buckets(buckets)

    assert len(result.buckets) == 1
    assert len(result.merge_events) == 1
