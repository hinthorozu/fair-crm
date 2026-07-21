"""Company name matching stabilization — sprint test dataset."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.value_objects import CustomerSource, CustomerStatus, CustomerType
from app.modules.imports.domain.services.company_name_matcher import (
    MATCH_SCORE_MIN,
    MATCH_SCORE_POSSIBLE,
    MATCH_SCORE_STRONG,
    score_company_name_pair,
)
from app.modules.imports.domain.services.company_name_normalizer import normalize_import_company_name
from app.modules.imports.domain.services.duplicate_detector import (
    MATCH_TYPE_EXACT,
    MATCH_TYPE_FUZZY,
    CustomerMatchIndex,
    find_customer_match,
)


def _customer(display_name: str, *, legal_name: str | None = None) -> Customer:
    now = datetime.now(tz=UTC)
    return Customer.create(
        organization_id=uuid4(),
        display_name=display_name,
        legal_name=legal_name,
        customer_type=CustomerType.LEAD,
        status=CustomerStatus.ACTIVE,
        source=CustomerSource.MANUAL,
        now=now,
    )


@pytest.mark.parametrize(
    ("import_name", "crm_name"),
    [
        ("SİNAN ELEKTRONİK A.Ş.", "SINAN ELEKTRONIK ANONIM SIRKETI"),
        ("ABC GIDA SAN. VE TİC. LTD. ŞTİ.", "ABC GIDA LIMITED SIRKETI"),
        (
            "AGROZAN TARIM ÜRÜN.GIDA ÜRÜN.İTH.İHR.SAN.TİC.LTD.ŞTİ.",
            "AGROZAN TARIM ÜRÜNLERİ GIDA ÜRÜNLERİ İTHALAT İHRACAT SANAYİ VE TİCARET LİMİTED ŞİRKETİ",
        ),
    ],
)
def test_high_confidence_pairs(import_name: str, crm_name: str):
    scored = score_company_name_pair(import_name, crm_name)
    assert scored is not None
    assert scored.confidence >= MATCH_SCORE_STRONG


@pytest.mark.parametrize(
    ("import_name", "crm_name"),
    [
        ("ABC GIDA", "XYZ GIDA"),
        ("ANADOLU GIDA", "ANADOLU MAKİNA"),
        ("BEYDAĞ GIDA", "BEYPAZARI GIDA"),
        (
            "AGRO SEEDS GIDA SAN. VE TİC. LTD. ŞTİ.",
            "AGROWELL GIDA SANAYİ VE TİCARET A.Ş.",
        ),
        (
            "ACARLAR VAGON SAN. VE TİC. A.Ş.",
            "ACARLAR YAPI MALZEMELERİ PAZARLAMA TİCARET LTD ŞTİ",
        ),
        (
            "AKM GÜVENLİK SİSTEMLERİ A.Ş.",
            "AKM ALARM KONTROL MERKEZİ LTD.",
        ),
        ("ABC ELECTRICAL APPLIANCE LTD", "XYZ ELECTRICAL APPLIANCE LTD"),
        (
            "ZHONGSHAN ALFA ELECTRICAL APPLIANCE CO LTD",
            "ZHONGSHAN BETA ELECTRICAL EQUIPMENT CO LTD",
        ),
        ("OMEGA TEXTILE MACHINERY LTD", "DELTA TEXTILE MACHINERY LTD"),
    ],
)
def test_should_not_match_pairs(import_name: str, crm_name: str):
    scored = score_company_name_pair(import_name, crm_name)
    assert scored is None or scored.confidence < MATCH_SCORE_MIN


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("ABC ELECTRICAL APPLIANCE LTD", "ABC ELECTRICAL APPLIANCE CO LTD"),
        ("OMEGA TEXTILE MACHINERY LTD", "OMEGA TEXTILE MACHINERY A.S."),
        ("AKM ALARM KONTROL MERKEZİ LTD ŞTİ", "AKM ALARM KONTROL MERKEZİ A.Ş."),
    ],
)
def test_sector_generics_do_not_block_same_brand_legal_variants(left: str, right: str):
    scored = score_company_name_pair(left, right)
    assert scored is not None
    assert scored.confidence >= MATCH_SCORE_STRONG


def test_akm_alarm_legal_form_variants_match_strongly():
    scored = score_company_name_pair(
        "AKM ALARM KONTROL MERKEZİ LTD ŞTİ",
        "AKM ALARM KONTROL MERKEZİ A.Ş.",
    )
    assert scored is not None
    assert scored.confidence >= MATCH_SCORE_STRONG


def test_turkish_i_normalization():
    assert normalize_import_company_name("SİNAN") == normalize_import_company_name("SINAN")
    assert normalize_import_company_name("İstanbul") == normalize_import_company_name("Istanbul")


def test_agrozan_via_index():
    crm = _customer(
        "AGROZAN TARIM ÜRÜNLERİ GIDA ÜRÜNLERİ İTHALAT İHRACAT SANAYİ VE TİCARET LİMİTED ŞİRKETİ"
    )
    index = CustomerMatchIndex.build([crm])
    query = "AGROZAN TARIM ÜRÜN.GIDA ÜRÜN.İTH.İHR.SAN.TİC.LTD.ŞTİ."
    match = index.find(
        normalize_import_company_name(query),
        raw_company_name=query,
    )
    assert match is not None
    assert match.confidence >= MATCH_SCORE_STRONG
    assert match.reason in (MATCH_TYPE_EXACT, MATCH_TYPE_FUZZY)


def test_confidence_bands():
    strong = score_company_name_pair("ABC GIDA LTD", "ABC GIDA LIMITED SIRKETI")
    assert strong is not None
    assert strong.confidence >= MATCH_SCORE_STRONG

    partial = score_company_name_pair("ABC GIDA SANAYI", "ABC MAKINA SANAYI")
    assert partial is None or partial.confidence < MATCH_SCORE_POSSIBLE

    assert score_company_name_pair("ABC", "ABC KIMYA") is None
    assert score_company_name_pair("SDK Teknoloji Mimarlık", "SDK Yazılım Hizmetleri") is None


def test_find_customer_match_explanation_stored():
    crm = _customer("SINAN ELEKTRONIK ANONIM SIRKETI")
    match = find_customer_match(
        normalize_import_company_name("SİNAN ELEKTRONİK A.Ş."),
        [crm],
        raw_company_name="SİNAN ELEKTRONİK A.Ş.",
    )
    assert match is not None
    assert match.explanation is not None
