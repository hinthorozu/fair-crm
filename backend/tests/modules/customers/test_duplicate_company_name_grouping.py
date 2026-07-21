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


def test_anadolu_distinct_sectors_stay_separate():
    gida = _model("ANADOLU GIDA")
    makina = _model("ANADOLU MAKINA")
    buckets = {
        "ANADOLU GIDA": {gida.id: gida},
        "ANADOLU MAKINA": {makina.id: makina},
    }

    result = merge_similar_company_name_buckets(buckets)

    assert len(result.buckets) == 2
    assert len(result.merge_events) == 0
    assert score_company_name_pair("ANADOLU GIDA", "ANADOLU MAKINA") is None


def test_acarlar_single_shared_token_does_not_merge():
    vagon = _model("ACARLAR VAGON SAN. VE TİC. A.Ş.")
    yapi = _model("ACARLAR YAPI MALZEMELERİ PAZARLAMA TİCARET LTD ŞTİ")
    buckets = {
        "acarlar vagon": {vagon.id: vagon},
        "acarlar yapi malzemeleri": {yapi.id: yapi},
    }

    result = merge_similar_company_name_buckets(buckets)

    assert len(result.buckets) == 2
    assert len(result.merge_events) == 0


def test_acarlar_bare_brand_hub_does_not_bridge_distinct_companies():
    """Regression: bare ACARLAR must not union-find VAGON and YAPI into one group."""
    hub = _model("ACARLAR")
    vagon = _model("ACARLAR VAGON SAN.VE TİC.A.Ş.")
    yapi = _model("ACARLAR YAPI MALZEMELERİ PAZARLAMA TİCARET LTD ŞTİ")
    buckets = {
        "acarlar": {hub.id: hub},
        "acarlar vagon": {vagon.id: vagon},
        "acarlar yapi malzemeleri": {yapi.id: yapi},
    }

    # Pairwise engine still allows hub↔long (Import 1:1); Admin clustering must not bridge.
    assert score_company_name_pair("ACARLAR", "ACARLAR VAGON SAN.VE TİC.A.Ş.") is not None
    assert score_company_name_pair("ACARLAR", "ACARLAR YAPI MALZEMELERİ PAZARLAMA TİCARET LTD ŞTİ") is not None
    assert (
        score_company_name_pair(
            "ACARLAR VAGON SAN.VE TİC.A.Ş.",
            "ACARLAR YAPI MALZEMELERİ PAZARLAMA TİCARET LTD ŞTİ",
        )
        is None
    )

    result = merge_similar_company_name_buckets(buckets)

    assert len(result.merge_events) == 0
    assert len(result.buckets) == 3
    assert {frozenset(group.keys()) for group in result.buckets.values()} == {
        frozenset({hub.id}),
        frozenset({vagon.id}),
        frozenset({yapi.id}),
    }


def test_ideal_bare_brand_hub_does_not_bridge_makina_and_gida():
    hub = _model("IDEAL")
    makina = _model("IDEAL MAKINA SANAYI")
    gida = _model("IDEAL GIDA PAZARLAMA")
    buckets = {
        "ideal": {hub.id: hub},
        "ideal makina": {makina.id: makina},
        "ideal gida": {gida.id: gida},
    }

    result = merge_similar_company_name_buckets(buckets)

    assert len(result.merge_events) == 0
    assert len(result.buckets) == 3
    member_sets = {frozenset(group.keys()) for group in result.buckets.values()}
    assert frozenset({makina.id, gida.id}) not in member_sets
    assert frozenset({hub.id, makina.id, gida.id}) not in member_sets


def test_akm_alarm_legal_suffix_variants_merge():
    ltd = _model("AKM ALARM KONTROL MERKEZİ LTD ŞTİ")
    as_form = _model("AKM ALARM KONTROL MERKEZİ A.Ş.")
    buckets = {
        "akm alarm kontrol merkezi ltd": {ltd.id: ltd},
        "akm alarm kontrol merkezi as": {as_form.id: as_form},
    }

    result = merge_similar_company_name_buckets(buckets)

    assert len(result.buckets) == 1
    assert len(result.merge_events) == 1


def test_akm_distinct_lines_do_not_merge():
    guvenlik = _model("AKM GÜVENLİK SİSTEMLERİ A.Ş.")
    alarm = _model("AKM ALARM KONTROL MERKEZİ LTD.")
    buckets = {
        "akm guvenlik sistemleri": {guvenlik.id: guvenlik},
        "akm alarm kontrol merkezi": {alarm.id: alarm},
    }

    result = merge_similar_company_name_buckets(buckets)

    assert len(result.buckets) == 2
    assert len(result.merge_events) == 0


def test_zhongshan_sector_generic_overlap_does_not_merge():
    alfa = _model("ZHONGSHAN ALFA ELECTRICAL APPLIANCE CO LTD")
    beta = _model("ZHONGSHAN BETA ELECTRICAL EQUIPMENT CO LTD")
    buckets = {
        "zhongshan alfa electrical appliance": {alfa.id: alfa},
        "zhongshan beta electrical equipment": {beta.id: beta},
    }

    assert score_company_name_pair(alfa.display_name, beta.display_name) is None
    result = merge_similar_company_name_buckets(buckets)
    assert len(result.buckets) == 2
    assert len(result.merge_events) == 0


def test_same_brand_electrical_legal_variants_still_merge():
    left = _model("ABC ELECTRICAL APPLIANCE LTD")
    right = _model("ABC ELECTRICAL APPLIANCE CO LTD")
    buckets = {
        "abc electrical appliance ltd": {left.id: left},
        "abc electrical appliance co": {right.id: right},
    }

    result = merge_similar_company_name_buckets(buckets)
    assert len(result.buckets) == 1
    assert len(result.merge_events) == 1


def test_anadolu_isuzu_variants_merge_strong():
    short = _model("ANADOLU ISUZU")
    long_form = _model("Anadolu Isuzu Otomotiv Sanayii")
    buckets = {
        "anadolu isuzu": {short.id: short},
        "anadolu isuzu otomotiv": {long_form.id: long_form},
    }

    scored = score_company_name_pair(short.display_name, long_form.display_name)
    assert scored is not None
    assert scored.confidence >= 95

    result = merge_similar_company_name_buckets(buckets)
    assert len(result.buckets) == 1
    assert len(result.merge_events) == 1
    assert result.merge_events[0].score >= 95


def test_global_gida_variants_merge():
    short = _model("GLOBAL GIDA")
    long_form = _model("GLOBAL GIDA PAZARLAMA DIS TICARET")
    buckets = {
        "global gida": {short.id: short},
        "global gida pazarlama dis ticaret": {long_form.id: long_form},
    }

    scored = score_company_name_pair(short.display_name, long_form.display_name)
    assert scored is not None
    assert scored.confidence >= 70

    result = merge_similar_company_name_buckets(buckets)
    assert len(result.buckets) == 1
    assert len(result.merge_events) == 1


def test_teknik_kimya_donatim_variants_merge():
    short = _model("TEKNIK KIMYA DONATIM")
    long_form = _model("TEKNIK KIMYA DONATIM ENERJI")
    buckets = {
        "teknik kimya donatim": {short.id: short},
        "teknik kimya donatim enerji": {long_form.id: long_form},
    }

    scored = score_company_name_pair(short.display_name, long_form.display_name)
    assert scored is not None
    assert scored.confidence >= 70

    result = merge_similar_company_name_buckets(buckets)
    assert len(result.buckets) == 1
    assert len(result.merge_events) == 1


def test_sanayii_sanayi_legal_suffix_equivalence():
    left = _model("ANADOLU ISUZU OTOMOTIV SANAYI")
    right = _model("ANADOLU ISUZU OTOMOTIV SANAYII")
    buckets = {
        "anadolu isuzu otomotiv sanayi": {left.id: left},
        "anadolu isuzu otomotiv sanayii": {right.id: right},
    }

    scored = score_company_name_pair(left.display_name, right.display_name)
    assert scored is not None
    assert scored.confidence >= 95

    result = merge_similar_company_name_buckets(buckets)
    assert len(result.buckets) == 1


def _first_token_noise_buckets(
    brand: str,
    *,
    count: int,
    seed_pair: tuple[tuple[str, str], tuple[str, str]],
) -> dict:
    """Build many same-first-token buckets plus one strong duplicate seed pair.

    ``seed_pair`` is ((bucket_key, display_name), (bucket_key, display_name)).
    """
    buckets: dict = {}
    for index in range(count):
        label = f"{brand} UNIQUE{index:03d} LINE"
        key = f"{brand.lower()} unique{index:03d} line"
        model = _model(label)
        buckets[key] = {model.id: model}

    (key_a, name_a), (key_b, name_b) = seed_pair
    left = _model(name_a)
    right = _model(name_b)
    buckets[key_a] = {left.id: left}
    buckets[key_b] = {right.id: right}
    return buckets, left, right


def test_large_bucket_40_plus_still_merges_strong_duplicate():
    """Problem C: first-token blocks >32 must not hard-skip fuzzy merge."""
    buckets, left, right = _first_token_noise_buckets(
        "ANADOLU",
        count=40,
        seed_pair=(
            ("anadolu isuzu", "ANADOLU ISUZU"),
            ("anadolu isuzu otomotiv", "Anadolu Isuzu Otomotiv Sanayii"),
        ),
    )
    assert len(buckets) >= 42

    result = merge_similar_company_name_buckets(buckets)
    assert result.stats is not None
    assert result.stats.blocks_above_direct_pairwise >= 1
    assert result.stats.candidate_pairs_generated < result.stats.theoretical_naive_pairs
    assert result.stats.pairs_scored < result.stats.theoretical_naive_pairs

    merged_ids = {
        frozenset(group.keys())
        for group in result.buckets.values()
        if left.id in group or right.id in group
    }
    assert any(left.id in ids and right.id in ids for ids in merged_ids)


def test_large_bucket_100_plus_still_merges_and_stays_sub_quadratic():
    buckets, left, right = _first_token_noise_buckets(
        "ZHEJIANG",
        count=100,
        seed_pair=(
            ("zhejiang global gida", "ZHEJIANG GLOBAL GIDA"),
            ("zhejiang global gida pazarlama", "ZHEJIANG GLOBAL GIDA PAZARLAMA DIS TICARET"),
        ),
    )
    assert len(buckets) >= 102

    result = merge_similar_company_name_buckets(buckets)
    assert result.stats is not None
    naive = result.stats.theoretical_naive_pairs
    scored = result.stats.pairs_scored
    candidates = result.stats.candidate_pairs_generated
    assert naive >= 100 * 99 // 2
    # Candidate narrowing must evaluate far fewer than N×N (allow headroom for indexes).
    assert candidates < naive // 5
    assert scored <= candidates
    assert scored < naive // 5

    merged_ids = {
        frozenset(group.keys())
        for group in result.buckets.values()
        if left.id in group or right.id in group
    }
    assert any(left.id in ids and right.id in ids for ids in merged_ids)


def test_large_bucket_does_not_merge_distinct_second_tokens():
    """Noise + distinct brands in a huge first-token block must stay separate."""
    buckets, left, right = _first_token_noise_buckets(
        "ANADOLU",
        count=40,
        seed_pair=(
            ("anadolu gida", "ANADOLU GIDA"),
            ("anadolu makina", "ANADOLU MAKINA"),
        ),
    )

    result = merge_similar_company_name_buckets(buckets)
    assert score_company_name_pair(left.display_name, right.display_name) is None
    left_group = next(group for group in result.buckets.values() if left.id in group)
    assert right.id not in left_group
