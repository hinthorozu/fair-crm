from datetime import UTC, date, datetime
from uuid import uuid4

import httpx
import pytest

from app.modules.fairs.application.sync_tobb_system_fairs import SyncTobbSystemFairsUseCase
from app.modules.fairs.domain.entities import Fair
from app.modules.fairs.domain.exceptions import TobbCalendarReadError
from app.modules.fairs.domain.services.normalizers import (
    compute_identity_name,
    compute_normalized_name,
    edition_key,
)
from app.modules.fairs.domain.value_objects import FairStatus
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
from app.modules.fairs.domain.services.normalizers import (
    system_fair_display_name,
    system_fair_status_for_dates,
)
from app.modules.fairs.infrastructure.tobb_calendar import TobbCalendarClient, parse_tobb_calendar_html

_HEADERS = (
    "Sıra No",
    "Başlangıç Tar.",
    "Bitiş Tar.",
    "Fuarın Adı",
    "Konusu",
    "Başlıca Ürün Hizmet Grupları",
    "Türü",
    "Fuar Yeri",
    "Şehir",
    "Düzenleyici",
    "Konu 1.",
    "Konu 2.",
    "Konu 3.",
    "Web",
    "E-Mail",
)


def _html(rows: list[list[str]]) -> str:
    header = "".join(f"<th>{column}</th>" for column in _HEADERS)
    body = []
    for row in rows:
        padded = row + [""] * (len(_HEADERS) - len(row))
        body.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in padded) + "</tr>")
    return f"<html><body><table><tr>{header}</tr>{''.join(body)}</table></body></html>"


def _sample_row() -> list[str]:
    return [
        "15",
        "01.03.2026",
        "04.03.2026",
        "İstanbul Fuarı",
        "Teknoloji",
        "Yazılım",
        "Genel",
        "İFM",
        "İstanbul",
        "TOBB",
        "",
        "",
        "",
        "https://www.istanbul-fuari.com/about",
        "info@example.com",
    ]


class _HtmlReader:
    def __init__(self, html: str) -> None:
        self.html = html

    def read(self, year: int) -> list:
        return parse_tobb_calendar_html(self.html)


def _sync(db_session, html: str, year: int = 2026, today: date | None = None):
    return SyncTobbSystemFairsUseCase(
        SqlAlchemyFairRepository(db_session),
        _HtmlReader(html),
    ).execute(year, today=today)


def _system(
    db_session,
    *,
    name: str,
    external_id: str,
    adapter_key: str | None = None,
    source_url: str | None = None,
    start_date: date | None = date(2026, 3, 1),
    end_date: date | None = date(2026, 3, 4),
    organizer: str | None = "Old Organizer",
    city: str = "İstanbul",
    scraper_config: dict | None = None,
) -> Fair:
    now = datetime.now(tz=UTC)
    fair = Fair(
        id=uuid4(),
        organization_id=None,
        name=name,
        organizer=organizer,
        venue="Old Venue",
        city=city,
        country="Türkiye",
        start_date=start_date,
        end_date=end_date,
        website=None,
        status=FairStatus.PLANNED,
        description=None,
        normalized_name=compute_normalized_name(name=name),
        created_at=now,
        updated_at=now,
        deleted_at=None,
        origin="system",
        source="tobb",
        external_id=external_id,
        adapter_key=adapter_key,
        source_url=source_url,
        scraper_config=scraper_config,
    )
    return SqlAlchemyFairRepository(db_session).add(fair)


def _system_rows(db_session) -> list[FairModel]:
    return (
        db_session.query(FairModel)
        .filter(FairModel.origin == "system", FairModel.source == "tobb")
        .all()
    )


_LONG_AMBALAJ = (
    "AVRASYA AMBALAJ 2026- İSTANBUL 31.ULUSLARARASI AMBALAJ ENDÜSTRİSİ FUARI "
    "(PRİNTPACK&CONVERTİNG-AMBALAJ BASKI TEKNOLOJİLERİ, OLUKLU MUKAVVA-KAĞIT-KARTON "
    "AMBALAJ ÜRETİM TEKNOLOJİLERİ ÖZEL BÖLÜMÜ) /FOODTECH EURASİA GIDA İÇECEK ÜRETİM "
    "VE İŞLEME TEKNOLOJİLERİ ÖZEL BÖLÜMÜ"
)


def test_system_fair_display_name_keeps_official_name_and_shortens_catalog_tail():
    display = system_fair_display_name(name=_LONG_AMBALAJ, city="İSTANBUL", origin="system")
    assert display == "AVRASYA AMBALAJ 2026 – İSTANBUL"
    assert _LONG_AMBALAJ.startswith("AVRASYA AMBALAJ 2026- İSTANBUL 31.")
    assert len(_LONG_AMBALAJ) > len(display)


def test_system_fair_display_name_falls_back_when_tail_is_not_a_catalog():
    official = "ICFE 2026 - INTERNATİONAL CARPET AND FLOORİNG EXPO - HALI, KİLİM FUARI"
    assert system_fair_display_name(name=official, city="İSTANBUL", origin="system") == official
    assert system_fair_display_name(name="DENİZLİ 2026", city="DENİZLİ", origin="system") == "DENİZLİ 2026"


def test_organization_fair_display_name_is_the_official_name():
    name = "AVRASYA AMBALAJ 2026- İSTANBUL 31.ULUSLARARASI FUARI"
    assert system_fair_display_name(name=name, city="İSTANBUL", origin="organization") == name


def test_parser_reads_tobb_columns_dates_and_identity_inputs():
    rows = parse_tobb_calendar_html(_html([_sample_row()]))
    assert len(rows) == 1
    row = rows[0]
    assert row.sequence_no == "15"
    assert row.name == "İstanbul Fuarı"
    assert row.organizer == "TOBB"
    assert row.venue == "İFM"
    assert row.city == "İstanbul"
    assert row.start_date.isoformat() == "2026-03-01"
    assert row.end_date.isoformat() == "2026-03-04"
    assert row.website == "https://www.istanbul-fuari.com/about"


def test_first_sync_inserts_system_fair(db_session):
    result = _sync(db_session, _html([_sample_row()]))
    assert result.inserted == 1
    assert result.updated == 0
    assert result.conflicts == 0

    saved = _system_rows(db_session)
    assert len(saved) == 1
    fair = saved[0]
    assert fair.origin == "system"
    assert fair.organization_id is None
    assert fair.source == "tobb"
    assert fair.external_id == "2026:15"
    assert fair.name == "İSTANBUL FUARI"
    assert fair.normalized_name == compute_normalized_name(name="İstanbul Fuarı")
    assert fair.organizer == "TOBB"
    assert fair.venue == "İFM"
    assert fair.city == "İstanbul"
    assert fair.country == "Türkiye"
    assert fair.start_date.isoformat() == "2026-03-01"
    assert fair.end_date.isoformat() == "2026-03-04"
    assert fair.website == "istanbul-fuari.com"
    assert fair.adapter_key is None
    assert fair.source_url is None
    assert fair.scraper_config is None


def test_tobb_insert_and_update_store_turkish_uppercase_name(db_session):
    inserted_row = _sample_row()
    inserted_row[3] = "istanbul mobilya fuarı"
    inserted = _sync(db_session, _html([inserted_row]))
    assert inserted.inserted == 1
    saved = _system_rows(db_session)[0]
    assert saved.name == "İSTANBUL MOBİLYA FUARI"
    assert saved.normalized_name == compute_normalized_name(name="istanbul mobilya fuarı")

    updated_row = _sample_row()
    updated_row[0] = "40"
    updated_row[3] = "istanbul mobilya fuarı"
    updated = _sync(db_session, _html([updated_row]))
    assert updated.updated == 1
    assert updated.inserted == 0
    db_session.expire_all()
    saved = _system_rows(db_session)[0]
    assert saved.name == "İSTANBUL MOBİLYA FUARI"
    assert saved.external_id == "2026:40"
    assert len(_system_rows(db_session)) == 1


def test_same_sync_updates_existing_without_duplicate(db_session):
    _sync(db_session, _html([_sample_row()]))
    result = _sync(db_session, _html([_sample_row()]))
    assert result.inserted == 0
    assert result.updated == 1
    assert result.conflicts == 0
    assert len(_system_rows(db_session)) == 1


def test_same_external_id_updates_changed_fields_without_touching_scraper_fields(db_session):
    existing = _system(
        db_session,
        name="İstanbul Fuarı",
        external_id="2026:15",
        adapter_key="keep-adapter",
        source_url="https://participant.example/list",
        scraper_config={"max_pages": 2},
    )
    changed = _sample_row()
    changed[9] = "Yeni Düzenleyici"
    result = _sync(db_session, _html([changed]))
    assert result.updated == 1
    assert result.inserted == 0

    db_session.expire_all()
    saved = db_session.get(FairModel, existing.id)
    assert saved.organizer == "Old Organizer"
    assert any(item["kind"] == "organizer" and item["proposed_values"] == {"organizer": "Yeni Düzenleyici"}
               for item in result.changes if item["action"] == "review")
    assert saved.external_id == "2026:15"
    assert saved.adapter_key == "keep-adapter"
    assert saved.source_url == "https://participant.example/list"
    assert saved.scraper_config == {"max_pages": 2}
    assert len(_system_rows(db_session)) == 1


def test_changed_sequence_matches_same_year_name_and_updates_external_id(db_session):
    existing = _system(db_session, name="İstanbul Fuarı", external_id="2026:15",
                       start_date=date(2026, 3, 1), end_date=date(2026, 3, 4))
    moved = _sample_row()
    moved[0] = "99"
    result = _sync(db_session, _html([moved]))
    assert result.inserted == 0
    assert result.updated == 1
    assert result.conflicts == 0

    db_session.expire_all()
    saved = db_session.get(FairModel, existing.id)
    assert saved.external_id == "2026:99"
    assert len(_system_rows(db_session)) == 1


def test_fallback_without_name_match_inserts(db_session):
    kept = _system(db_session, name="Başka Fuar", external_id="2026:1")
    result = _sync(db_session, _html([_sample_row()]))
    assert result.inserted == 1
    assert result.updated == 0

    db_session.expire_all()
    assert db_session.get(FairModel, kept.id).external_id == "2026:1"
    assert len(_system_rows(db_session)) == 2


def test_fallback_conflict_does_not_insert_or_update(db_session):
    first = _system(db_session, name="İstanbul Fuarı", external_id="2026:1")
    second = _system(db_session, name="İstanbul Fuarı", external_id="2026:2")
    before = {
        first.id: (first.external_id, first.organizer),
        second.id: (second.external_id, second.organizer),
    }
    result = _sync(db_session, _html([_sample_row()]))
    assert result.inserted == 0
    assert result.updated == 0
    assert result.conflicts == 1
    assert {fair_id for item in result.conflict_items for fair_id in item.fair_ids} == {
        first.id,
        second.id,
    }

    db_session.expire_all()
    assert len(_system_rows(db_session)) == 2
    for fair_id, snapshot in before.items():
        saved = db_session.get(FairModel, fair_id)
        assert (saved.external_id, saved.organizer) == snapshot


def test_organization_fair_with_same_name_is_not_matched(db_session, organization_id):
    now = datetime.now(tz=UTC)
    organization_fair = SqlAlchemyFairRepository(db_session).add(
        Fair.create(
            organization_id=organization_id,
            name="İstanbul Fuarı",
            organizer="Org Organizer",
            now=now,
        )
    )
    result = _sync(db_session, _html([_sample_row()]))
    assert result.inserted == 1
    assert result.updated == 0
    assert result.conflicts == 0

    db_session.expire_all()
    saved = db_session.get(FairModel, organization_fair.id)
    assert saved.origin == "organization"
    assert saved.organization_id == organization_id
    assert saved.organizer == "Org Organizer"
    assert saved.source is None
    assert saved.external_id is None
    assert len(_system_rows(db_session)) == 1


def test_same_logical_fair_in_another_year_updates_the_existing_row(db_session):
    previous = _system(db_session, name="İstanbul Fuarı", external_id="2025:15",
                       start_date=date(2025, 3, 1), end_date=date(2025, 3, 4))
    result = _sync(db_session, _html([_sample_row()]), year=2026)
    assert result.inserted == 0
    assert result.updated == 1
    assert result.conflicts == 0

    db_session.expire_all()
    saved = db_session.get(FairModel, previous.id)
    assert saved.external_id == "2026:15"
    assert saved.start_date.isoformat() == "2026-03-01"
    assert len(_system_rows(db_session)) == 1


def test_system_fair_missing_from_tobb_is_left_unchanged(db_session):
    missing = _system(db_session, name="Eski Fuar", external_id="2026:99")
    result = _sync(db_session, _html([_sample_row()]))
    assert result.inserted == 1

    db_session.expire_all()
    saved = db_session.get(FairModel, missing.id)
    assert saved.name == "Eski Fuar"
    assert saved.external_id == "2026:99"
    assert saved.deleted_at is None
    assert saved.status == FairStatus.PLANNED.value


def test_system_fair_status_follows_calendar_dates():
    today = date(2026, 9, 30)
    assert (
        system_fair_status_for_dates(
            start_date=date(2026, 10, 5),
            end_date=date(2026, 10, 8),
            today=today,
        )
        == FairStatus.PLANNED
    )
    assert (
        system_fair_status_for_dates(
            start_date=date(2026, 9, 30),
            end_date=date(2026, 10, 2),
            today=today,
        )
        == FairStatus.ACTIVE
    )
    assert (
        system_fair_status_for_dates(
            start_date=date(2026, 9, 28),
            end_date=date(2026, 9, 30),
            today=today,
        )
        == FairStatus.ACTIVE
    )
    assert (
        system_fair_status_for_dates(
            start_date=date(2026, 9, 20),
            end_date=date(2026, 9, 29),
            today=today,
        )
        == FairStatus.COMPLETED
    )
    assert (
        system_fair_status_for_dates(
            start_date=date(2026, 1, 6),
            end_date=date(2026, 1, 9),
            today=today,
        )
        == FairStatus.COMPLETED
    )
    assert (
        system_fair_status_for_dates(start_date=None, end_date=None, today=today) is None
    )


def test_sync_persists_date_based_status_for_a_past_system_fair(db_session):
    row = _sample_row()
    row[1] = "06.01.2026"
    row[2] = "09.01.2026"
    result = _sync(db_session, _html([row]))
    assert result.inserted == 1

    db_session.expire_all()
    saved = _system_rows(db_session)[0]
    assert saved.start_date == date(2026, 1, 6)
    assert saved.end_date == date(2026, 1, 9)
    assert saved.status == system_fair_status_for_dates(
        start_date=saved.start_date,
        end_date=saved.end_date,
        today=date.today(),
    ).value


def test_parser_skips_tobb_summary_footer():
    second = _sample_row()
    second[0] = "16"
    second[3] = "Ankara Fuarı"
    footer = [""] * len(_HEADERS)
    footer[3] = "Toplam Fuar Sayısı(2026): 439"
    rows = parse_tobb_calendar_html(_html([_sample_row(), second, footer]))
    assert [row.sequence_no for row in rows] == ["15", "16"]
    assert [row.name for row in rows] == ["İstanbul Fuarı", "Ankara Fuarı"]


def test_normal_row_missing_sequence_is_a_failure():
    broken = _sample_row()
    broken[0] = ""
    with pytest.raises(TobbCalendarReadError, match="TOBB sequence number is missing"):
        parse_tobb_calendar_html(_html([_sample_row(), broken]))


def test_missing_table_is_a_failure():
    with pytest.raises(TobbCalendarReadError):
        parse_tobb_calendar_html("<html><body><p>no table</p></body></html>")


def test_missing_required_column_is_a_failure():
    html = "<html><body><table><tr><th>Fuarın Adı</th></tr><tr><td>Fuar</td></tr></table></body></html>"
    with pytest.raises(TobbCalendarReadError):
        parse_tobb_calendar_html(html)


def test_non_2xx_tobb_response_is_a_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/FuarTakvimi/2026"
        return httpx.Response(503, text="down")

    client = TobbCalendarClient(transport=httpx.MockTransport(handler))
    with pytest.raises(TobbCalendarReadError):
        client.read(2026)


_TODAY = date(2026, 10, 1)


def _named_row(
    *,
    sequence: str,
    name: str,
    start: str,
    end: str,
) -> list[str]:
    row = _sample_row()
    row[0] = sequence
    row[1] = start
    row[2] = end
    row[3] = name
    return row


def test_annual_rollover_updates_finished_edition(db_session):
    existing = _system(
        db_session,
        name="X Fuarı",
        external_id="2026:10",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 30),
    )
    result = _sync(
        db_session,
        _html([_named_row(sequence="25", name="X Fuarı", start="01.08.2027", end="05.08.2027")]),
        year=2027,
        today=_TODAY,
    )
    assert result.inserted == 0
    assert result.updated == 1
    assert result.conflicts == 0

    db_session.expire_all()
    saved = db_session.get(FairModel, existing.id)
    assert saved.external_id == "2027:25"
    assert saved.start_date == date(2027, 8, 1)
    assert saved.end_date == date(2027, 8, 5)
    assert saved.name == "X Fuarı"
    assert len(_system_rows(db_session)) == 1


def test_next_year_is_blocked_when_the_current_edition_ends_today(db_session):
    existing = _system(
        db_session,
        name="X Fuarı",
        external_id="2026:10",
        start_date=date(2026, 9, 28),
        end_date=date(2026, 10, 1),
    )
    result = _sync(
        db_session,
        _html([_named_row(sequence="25", name="X Fuarı", start="01.08.2027", end="05.08.2027")]),
        year=2027,
        today=_TODAY,
    )
    assert (result.inserted, result.updated, result.conflicts) == (0, 0, 0)
    db_session.expire_all()
    saved = db_session.get(FairModel, existing.id)
    assert saved.external_id == "2026:10"
    assert saved.end_date == date(2026, 10, 1)
    assert len(_system_rows(db_session)) == 1


def test_next_year_is_blocked_for_a_future_edition(db_session):
    existing = _system(
        db_session,
        name="X Fuarı",
        external_id="2026:10",
        start_date=date(2026, 10, 15),
        end_date=date(2026, 10, 18),
    )
    result = _sync(
        db_session,
        _html([_named_row(sequence="25", name="X Fuarı", start="03.10.2027", end="06.10.2027")]),
        year=2027,
        today=_TODAY,
    )
    assert (result.inserted, result.updated, result.conflicts) == (0, 0, 0)
    db_session.expire_all()
    saved = db_session.get(FairModel, existing.id)
    assert saved.external_id == "2026:10"
    assert saved.start_date == date(2026, 10, 15)
    assert saved.end_date == date(2026, 10, 18)
    assert len(_system_rows(db_session)) == 1


def test_next_year_is_blocked_while_the_current_edition_is_active(db_session):
    existing = _system(
        db_session,
        name="X Fuarı",
        external_id="2026:10",
        start_date=date(2026, 9, 28),
        end_date=date(2026, 10, 3),
    )
    result = _sync(
        db_session,
        _html([_named_row(sequence="25", name="X Fuarı", start="01.08.2027", end="05.08.2027")]),
        year=2027,
        today=_TODAY,
    )
    assert (result.inserted, result.updated, result.conflicts) == (0, 0, 0)
    db_session.expire_all()
    saved = db_session.get(FairModel, existing.id)
    assert saved.external_id == "2026:10"
    assert saved.end_date == date(2026, 10, 3)
    assert len(_system_rows(db_session)) == 1


def test_older_sync_year_does_not_downgrade_a_newer_edition(db_session):
    existing = _system(
        db_session,
        name="X Fuarı",
        external_id="2027:25",
        start_date=date(2027, 8, 1),
        end_date=date(2027, 8, 5),
    )
    result = _sync(
        db_session,
        _html([_named_row(sequence="10", name="X Fuarı", start="01.09.2026", end="05.09.2026")]),
        year=2026,
        today=_TODAY,
    )
    assert (result.inserted, result.updated, result.conflicts) == (0, 0, 1)
    assert result.conflict_items[0].name == "X FUARI"
    assert result.conflict_items[0].fair_ids == (existing.id,)
    db_session.expire_all()
    saved = db_session.get(FairModel, existing.id)
    assert saved.external_id == "2027:25"
    assert saved.start_date == date(2027, 8, 1)
    assert saved.end_date == date(2027, 8, 5)
    assert saved.organizer == "Old Organizer"
    assert len(_system_rows(db_session)) == 1


def test_annual_sync_inserts_when_no_normalized_candidate_exists(db_session):
    result = _sync(
        db_session,
        _html([_named_row(sequence="25", name="Yeni Fuar", start="01.08.2027", end="05.08.2027")]),
        year=2027,
        today=_TODAY,
    )
    assert result.inserted == 1
    assert result.updated == 0
    assert result.conflicts == 0
    saved = _system_rows(db_session)
    assert len(saved) == 1
    assert saved[0].external_id == "2027:25"
    assert saved[0].name == "YENİ FUAR"


def test_multiple_annual_candidates_are_a_conflict(db_session):
    first = _system(
        db_session,
        name="X Fuarı",
        external_id="2024:3",
        start_date=date(2024, 9, 1),
        end_date=date(2024, 9, 5),
    )
    second = _system(
        db_session,
        name="X Fuarı",
        external_id="2025:8",
        start_date=date(2025, 9, 1),
        end_date=date(2025, 9, 5),
    )
    result = _sync(
        db_session,
        _html([_named_row(sequence="25", name="X Fuarı", start="01.08.2027", end="05.08.2027")]),
        year=2027,
        today=_TODAY,
    )
    assert (result.inserted, result.updated, result.conflicts) == (0, 0, 1)
    assert set(result.conflict_items[0].fair_ids) == {first.id, second.id}
    db_session.expire_all()
    assert db_session.get(FairModel, first.id).external_id == "2024:3"
    assert db_session.get(FairModel, second.id).external_id == "2025:8"
    assert db_session.get(FairModel, first.id).organizer == "Old Organizer"
    assert len(_system_rows(db_session)) == 2


def test_same_reference_date_correction_warns_without_update(db_session):
    existing = _system(
        db_session,
        name="X Fuarı",
        external_id="2027:25",
        start_date=date(2027, 1, 1),
        end_date=date(2027, 1, 4),
    )
    result = _sync(
        db_session,
        _html([_named_row(sequence="25", name="X Fuarı", start="01.08.2027", end="05.08.2027")]),
        year=2027,
        today=_TODAY,
    )
    assert result.updated == 0
    assert result.inserted == 0
    assert result.conflicts == 0
    db_session.expire_all()
    saved = db_session.get(FairModel, existing.id)
    assert saved.external_id == "2027:25"
    assert saved.start_date == date(2027, 1, 1)
    assert saved.end_date == date(2027, 1, 4)
    assert len(result.date_change_warnings) == 1
    assert len(_system_rows(db_session)) == 1


def test_identity_name_drops_year_and_edition_without_changing_normalized_name():
    raw = "AVRASYA AMBALAJ 2026- İSTANBUL 31.ULUSLARARASI FUARI"
    later = "AVRASYA AMBALAJ 2027- İSTANBUL 32.ULUSLARARASI FUARI"
    assert compute_identity_name(name=raw) == compute_identity_name(name=later)
    assert "2026" in compute_normalized_name(name=raw)
    assert "31" not in compute_identity_name(name=raw).split()
    assert edition_key(raw) == ("31",)
    assert edition_key("IJS 31st İstanbul") == ("31",)
    assert edition_key("31'inci fuar") == ("31",)
    assert edition_key("SHOW XXXI") == ()
    assert "XXXI" in compute_identity_name(name="SHOW XXXI")


def test_next_year_edition_updates_the_same_system_fair(db_session):
    existing = _system(
        db_session,
        name="AVRASYA AMBALAJ 2026- İSTANBUL 31.ULUSLARARASI FUARI",
        external_id="2026:4",
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 13),
        city="İstanbul",
    )
    result = _sync(
        db_session,
        _html(
            [
                _named_row(
                    sequence="80",
                    name="AVRASYA AMBALAJ 2027- İSTANBUL 32.ULUSLARARASI FUARI",
                    start="17.10.2027",
                    end="20.10.2027",
                )
            ]
        ),
        year=2027,
        today=date(2026, 10, 14),
    )

    assert (result.inserted, result.updated, result.conflicts) == (0, 1, 0)
    db_session.expire_all()
    saved = db_session.get(FairModel, existing.id)
    assert saved.external_id == "2027:80"
    assert saved.start_date == date(2027, 10, 17)
    assert saved.end_date == date(2027, 10, 20)
    assert saved.name == existing.name
    assert len(_system_rows(db_session)) == 1


def test_date_correction_warns_and_preserves_the_same_fair(db_session):
    existing = _system(
        db_session,
        name="AVRASYA AMBALAJ 2026- İSTANBUL 31.ULUSLARARASI FUARI",
        external_id="2026:4",
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 13),
    )
    result = _sync(
        db_session,
        _html(
            [
                _named_row(
                    sequence="4",
                    name="AVRASYA AMBALAJ 2026- İSTANBUL 31.ULUSLARARASI FUARI",
                    start="17.10.2026",
                    end="20.10.2026",
                )
            ]
        ),
        year=2026,
        today=_TODAY,
    )
    assert result.updated == 0
    assert result.inserted == 0
    db_session.expire_all()
    saved = db_session.get(FairModel, existing.id)
    assert saved.start_date == date(2026, 10, 10)
    assert saved.end_date == date(2026, 10, 13)
    assert len(result.date_change_warnings) == 1
    warning = result.date_change_warnings[0]
    assert warning.fair_id == existing.id
    assert warning.old_end_date == date(2026, 10, 13)
    assert warning.new_end_date == date(2026, 10, 20)
    assert len(_system_rows(db_session)) == 1


def test_same_year_editions_insert_only_the_ongoing_edition(db_session):
    result = _sync(
        db_session,
        _html(
            [
                _named_row(
                    sequence="59",
                    name="IJS İSTANBUL 2026 59. ULUSLARARASI MÜCEVHER FUARI",
                    start="01.10.2026",
                    end="04.10.2026",
                ),
                _named_row(
                    sequence="60",
                    name="IJS İSTANBUL 2026 60. ULUSLARARASI MÜCEVHER FUARI",
                    start="01.03.2026",
                    end="04.03.2026",
                ),
            ]
        ),
        year=2026,
        today=_TODAY,
    )
    assert (result.inserted, result.updated, result.conflicts) == (1, 0, 0)
    saved = _system_rows(db_session)
    assert len(saved) == 1
    assert saved[0].external_id == "2026:59"
    repeated = _sync(db_session, _html([
        _named_row(sequence="59", name="IJS İSTANBUL 2026 59. ULUSLARARASI MÜCEVHER FUARI",
                   start="01.10.2026", end="04.10.2026"),
        _named_row(sequence="60", name="IJS İSTANBUL 2026 60. ULUSLARARASI MÜCEVHER FUARI",
                   start="01.03.2026", end="04.03.2026"),
    ]), today=_TODAY)
    assert (repeated.inserted, repeated.updated, repeated.conflicts) == (0, 1, 0)
    assert len(_system_rows(db_session)) == 1


def test_later_same_year_edition_does_not_overwrite_the_first(db_session):
    first = _system(
        db_session,
        name="IJS İSTANBUL 2026 59. ULUSLARARASI MÜCEVHER FUARI",
        external_id="2026:59",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 4),
        organizer="IJS Organizer",
    )
    result = _sync(
        db_session,
        _html(
            [
                _named_row(
                    sequence="60",
                    name="IJS İSTANBUL 2026 60. ULUSLARARASI MÜCEVHER FUARI",
                    start="01.03.2026",
                    end="04.03.2026",
                )
            ]
        ),
        year=2026,
        today=_TODAY,
    )
    assert result.inserted == 0
    assert result.updated == 0
    db_session.expire_all()
    kept = db_session.get(FairModel, first.id)
    assert kept.external_id == "2026:59"
    assert kept.organizer == "IJS Organizer"
    assert kept.start_date == date(2026, 10, 1)
    assert len(_system_rows(db_session)) == 1


def test_next_year_multi_edition_family_does_not_cross_match(db_session):
    first = _system(
        db_session,
        name="IJS İSTANBUL 2026 59. ULUSLARARASI MÜCEVHER FUARI",
        external_id="2026:59",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 4),
    )
    second = _system(
        db_session,
        name="IJS İSTANBUL 2026 60. ULUSLARARASI MÜCEVHER FUARI",
        external_id="2026:60",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 4),
    )
    result = _sync(
        db_session,
        _html(
            [
                _named_row(
                    sequence="61",
                    name="IJS İSTANBUL 2027 61. ULUSLARARASI MÜCEVHER FUARI",
                    start="01.10.2027",
                    end="04.10.2027",
                ),
                _named_row(
                    sequence="62",
                    name="IJS İSTANBUL 2027 62. ULUSLARARASI MÜCEVHER FUARI",
                    start="01.03.2027",
                    end="04.03.2027",
                ),
            ]
        ),
        year=2027,
        today=_TODAY,
    )
    assert result.inserted == 0
    assert result.updated == 0
    assert result.conflicts == 2
    assert all(set(item.fair_ids) == {first.id, second.id} for item in result.conflict_items)
    db_session.expire_all()
    assert db_session.get(FairModel, first.id).external_id == "2026:59"
    assert db_session.get(FairModel, second.id).external_id == "2026:60"
    assert len(_system_rows(db_session)) == 2


@pytest.mark.parametrize("today, updated", [
    (date(2026, 10, 19), 0), (date(2026, 10, 20), 0), (date(2026, 10, 21), 1),
])
def test_rollover_requires_strictly_past_end_date(db_session, today, updated):
    fair = _system(db_session, name="IJS İSTANBUL", external_id="2026:59",
                   start_date=date(2026, 10, 15), end_date=date(2026, 10, 20))
    row = _named_row(sequence="61", name="61. IJS İSTANBUL 2027",
                     start="02.03.2027", end="05.03.2027")
    result = _sync(db_session, _html([row]), year=2027, today=today)
    assert (result.inserted, result.updated, result.conflicts) == (0, updated, 0)
    db_session.expire_all()
    saved = db_session.get(FairModel, fair.id)
    assert saved.name == "IJS İSTANBUL"
    assert saved.end_date == (date(2027, 3, 5) if updated else date(2026, 10, 20))
    assert len(_system_rows(db_session)) == 1


def test_short_manual_name_matches_long_title_and_survives_repeated_sync(db_session):
    fair = _system(db_session, name="ANALYTECH", external_id="2026:9",
                   adapter_key="keep", source_url="https://example.test/participants",
                   scraper_config={"max_pages": 5})
    row = _sample_row()
    row[0] = "9"
    row[3] = "9. ANALYTECH ULUSLARARASI ANALİZ VE LABORATUVAR TEKNOLOJİLERİ FUARI"
    for _ in range(2):
        result = _sync(db_session, _html([row]), today=_TODAY)
        assert (result.inserted, result.updated, result.conflicts) == (0, 1, 0)
        db_session.expire_all()
        saved = db_session.get(FairModel, fair.id)
        assert saved.name == "ANALYTECH"
        assert saved.normalized_name == compute_normalized_name(name=row[3])
        assert saved.identity_name == compute_identity_name(name=row[3])
        assert (saved.adapter_key, saved.source_url, saved.scraper_config) == (
            "keep", "https://example.test/participants", {"max_pages": 5},
        )
        assert len(_system_rows(db_session)) == 1


@pytest.mark.parametrize("short_name, city", [
    ("ANALY", "İstanbul"), ("ANALYTECH", "Ankara"), ("FUARI", "İstanbul"),
])
def test_substring_generic_word_or_other_city_does_not_match(db_session, short_name, city):
    existing = _system(db_session, name=short_name, external_id="2026:1", city=city)
    row = _sample_row()
    row[3] = "9. ANALYTECH ULUSLARARASI ANALİZ FUARI"
    result = _sync(db_session, _html([row]), today=_TODAY)
    assert (result.inserted, result.updated, result.conflicts) == ((0, 0, 1) if city == "Ankara" else (1, 0, 0))
    db_session.expire_all()
    assert db_session.get(FairModel, existing.id).name == short_name
    assert len(_system_rows(db_session)) == (1 if city == "Ankara" else 2)


def test_exact_match_does_not_hide_another_short_name_candidate(db_session):
    title = "9. ANALYTECH ULUSLARARASI ANALİZ FUARI"
    short = _system(db_session, name="ANALYTECH", external_id="2026:1")
    exact = _system(db_session, name=title, external_id="2026:2")
    row = _sample_row()
    row[3] = title
    result = _sync(db_session, _html([row]), today=_TODAY)
    assert (result.inserted, result.updated, result.conflicts) == (0, 0, 1)
    assert set(result.conflict_items[0].fair_ids) == {short.id, exact.id}
    db_session.expire_all()
    assert db_session.get(FairModel, short.id).external_id == "2026:1"
    assert db_session.get(FairModel, exact.id).external_id == "2026:2"


def test_same_year_new_edition_reuses_fair_id_after_expiry(db_session):
    fair = _system(db_session, name="59. IJS İSTANBUL", external_id="2026:59",
                   start_date=date(2026, 3, 1), end_date=date(2026, 3, 4))
    row = _named_row(sequence="60", name="60. IJS İSTANBUL",
                     start="01.10.2026", end="04.10.2026")
    result = _sync(db_session, _html([row]), today=_TODAY)
    assert (result.inserted, result.updated, result.conflicts) == (0, 1, 0)
    db_session.expire_all()
    saved = db_session.get(FairModel, fair.id)
    assert saved.external_id == "2026:60"
    assert saved.name == fair.name
    assert saved.start_date == date(2026, 10, 1)
    assert len(_system_rows(db_session)) == 1


@pytest.mark.parametrize("end_date", [None, date(2026, 10, 20)])
def test_unknown_or_active_end_date_blocks_same_year_new_edition(db_session, end_date):
    fair = _system(db_session, name="59. IJS İSTANBUL", external_id="2026:59",
                   start_date=date(2026, 10, 15), end_date=end_date)
    row = _named_row(sequence="60", name="60. IJS İSTANBUL",
                     start="11.11.2026", end="14.11.2026")
    result = _sync(db_session, _html([row]), today=date(2026, 10, 19))
    assert (result.inserted, result.updated, result.conflicts) == (0, 0, 0)
    assert not result.date_change_warnings
    db_session.expire_all()
    assert db_session.get(FairModel, fair.id).end_date == end_date
    assert len(_system_rows(db_session)) == 1


@pytest.mark.parametrize("today", [date(2026, 10, 19), date(2026, 10, 20), date(2026, 10, 21)])
def test_ambalaj_date_change_warns_and_preserves_all_fields(db_session, today):
    fair = _system(db_session, name="AVRASYA AMBALAJ", external_id="2026:31",
                   start_date=date(2026, 10, 17), end_date=date(2026, 10, 20),
                   adapter_key="tuyap_new", source_url="https://example.test/participants",
                   scraper_config={"max_pages": 2})
    row = _named_row(sequence="31", name="31. AVRASYA AMBALAJ 2026 ULUSLARARASI FUARI",
                     start="08.11.2026", end="11.11.2026")
    before = {column.name: getattr(db_session.get(FairModel, fair.id), column.name)
              for column in FairModel.__table__.columns}
    for _ in range(2):
        result = _sync(db_session, _html([row]), today=today)
        assert (result.inserted, result.updated, result.conflicts) == (0, 0, 0)
        assert len(result.date_change_warnings) == 1
        warning = result.date_change_warnings[0]
        assert (warning.fair_id, warning.name) == (fair.id, "AVRASYA AMBALAJ")
        assert (warning.old_start_date, warning.old_end_date) == (date(2026, 10, 17), date(2026, 10, 20))
        assert (warning.new_start_date, warning.new_end_date) == (date(2026, 11, 8), date(2026, 11, 11))
        db_session.expire_all()
        saved = db_session.get(FairModel, fair.id)
        assert {column.name: getattr(saved, column.name) for column in FairModel.__table__.columns} == before


def test_reused_sequence_does_not_mutate_a_blocked_unrelated_fair(db_session):
    holder = _system(db_session, name="IJS İSTANBUL", external_id="2026:15",
                     start_date=date(2026, 10, 15), end_date=date(2026, 10, 20))
    result = _sync(db_session, _html([_sample_row()]), today=date(2026, 10, 19))
    assert (result.inserted, result.updated, result.conflicts) == (0, 0, 1)
    db_session.expire_all()
    assert db_session.get(FairModel, holder.id).external_id == "2026:15"
    assert len(_system_rows(db_session)) == 1


def test_multiple_editions_without_unique_ongoing_occurrence_fail_closed(db_session):
    rows = [_named_row(sequence=str(number), name=f"{number}. IJS İSTANBUL",
                       start=start, end=end) for number, start, end in [
        (59, "01.03.2026", "04.03.2026"), (60, "01.11.2026", "04.11.2026"),
    ]]
    result = _sync(db_session, _html(rows), today=_TODAY)
    assert (result.inserted, result.updated, result.conflicts) == (0, 0, 2)
    assert not _system_rows(db_session)


def test_rollover_preserves_customer_participations_in_both_organizations(db_session, organization_id, other_organization_id):
    from app.modules.customers.infrastructure.persistence.models import CustomerModel
    from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel

    fair = _system(db_session, name="ANALYTECH", external_id="2026:9")
    now = datetime.now(tz=UTC)
    children = []
    for org_id in (organization_id, other_organization_id):
        customer = CustomerModel(id=uuid4(), organization_id=org_id, display_name="Customer",
                                 normalized_name="customer", customer_type="lead", status="active",
                                 source="manual", created_at=now, updated_at=now)
        db_session.add(customer)
        db_session.flush()
        participation = CustomerFairParticipationModel(
            id=uuid4(), organization_id=org_id, customer_id=customer.id, fair_id=fair.id,
            hall="H1", stand="S1", notes="keep", participation_status="exhibitor",
            is_active=True, created_at=now, updated_at=now,
        )
        db_session.add(participation)
        db_session.flush()
        children.append((org_id, customer.id, participation.id))
    row = _named_row(sequence="10", name="10. ANALYTECH 2027 ULUSLARARASI FUARI",
                     start="01.03.2027", end="04.03.2027")
    result = _sync(db_session, _html([row]), year=2027, today=_TODAY)
    assert (result.inserted, result.updated, result.conflicts) == (0, 1, 0)
    db_session.expire_all()
    for org_id, customer_id, participation_id in children:
        saved = db_session.get(CustomerFairParticipationModel, participation_id)
        assert (saved.organization_id, saved.customer_id, saved.fair_id, saved.notes) == (
            org_id, customer_id, fair.id, "keep",
        )
        assert db_session.get(CustomerModel, customer_id).organization_id == org_id
    assert len(_system_rows(db_session)) == 1


def test_correction_warning_blocks_rollover_even_if_another_edition_is_available(db_session):
    fair = _system(db_session, name="31. AVRASYA AMBALAJ", external_id="2026:31",
                   start_date=date(2026, 10, 17), end_date=date(2026, 10, 20))
    rows = [
        _named_row(sequence="31", name="31. AVRASYA AMBALAJ", start="08.11.2026", end="11.11.2026"),
        _named_row(sequence="32", name="32. AVRASYA AMBALAJ", start="01.12.2026", end="04.12.2026"),
    ]
    result = _sync(db_session, _html(rows), today=date(2026, 10, 21))
    assert (result.inserted, result.updated, result.conflicts) == (0, 0, 0)
    assert len(result.date_change_warnings) == 1
    db_session.expire_all()
    assert db_session.get(FairModel, fair.id).end_date == date(2026, 10, 20)
    assert len(_system_rows(db_session)) == 1


def test_unknown_same_year_edition_is_not_guessed_from_a_changed_sequence(db_session):
    fair = _system(db_session, name="AVRASYA AMBALAJ", external_id="2026:31",
                   start_date=date(2026, 10, 17), end_date=date(2026, 10, 20))
    row = _named_row(sequence="32", name="AVRASYA AMBALAJ", start="08.11.2026", end="11.11.2026")
    result = _sync(db_session, _html([row]), today=date(2026, 10, 21))
    assert (result.inserted, result.updated, result.conflicts) == (0, 0, 1)
    db_session.expire_all()
    assert db_session.get(FairModel, fair.id).end_date == date(2026, 10, 20)


def test_archived_identity_requires_review_instead_of_automatic_recreation(db_session):
    fair = _system(db_session, name="İstanbul Fuarı", external_id="2025:15")
    stored = db_session.get(FairModel, fair.id)
    stored.deleted_at = datetime.now(UTC)
    db_session.flush()
    result = _sync(db_session, _html([_sample_row()]), today=date(2026, 10, 12))
    assert result.inserted == 0
    assert result.conflicts == 1
    assert len(_system_rows(db_session)) == 1
    assert stored.deleted_at is not None
