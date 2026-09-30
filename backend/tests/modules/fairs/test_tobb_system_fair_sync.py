from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest

from app.modules.fairs.application.sync_tobb_system_fairs import SyncTobbSystemFairsUseCase
from app.modules.fairs.domain.entities import Fair
from app.modules.fairs.domain.exceptions import TobbCalendarReadError
from app.modules.fairs.domain.services.normalizers import compute_normalized_name
from app.modules.fairs.domain.value_objects import FairStatus
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
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


def _sync(db_session, html: str, year: int = 2026):
    return SyncTobbSystemFairsUseCase(
        SqlAlchemyFairRepository(db_session),
        _HtmlReader(html),
    ).execute(year)


def _system(
    db_session,
    *,
    name: str,
    external_id: str,
    adapter_key: str | None = None,
    source_url: str | None = None,
) -> Fair:
    now = datetime.now(tz=UTC)
    fair = Fair(
        id=uuid4(),
        organization_id=None,
        name=name,
        organizer="Old Organizer",
        venue="Old Venue",
        city="Ankara",
        country="Türkiye",
        start_date=None,
        end_date=None,
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
    )
    return SqlAlchemyFairRepository(db_session).add(fair)


def _system_rows(db_session) -> list[FairModel]:
    return (
        db_session.query(FairModel)
        .filter(FairModel.origin == "system", FairModel.source == "tobb")
        .all()
    )


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
    assert fair.name == "İstanbul Fuarı"
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
    )
    changed = _sample_row()
    changed[9] = "Yeni Düzenleyici"
    result = _sync(db_session, _html([changed]))
    assert result.updated == 1
    assert result.inserted == 0

    db_session.expire_all()
    saved = db_session.get(FairModel, existing.id)
    assert saved.organizer == "Yeni Düzenleyici"
    assert saved.external_id == "2026:15"
    assert saved.adapter_key == "keep-adapter"
    assert saved.source_url == "https://participant.example/list"
    assert len(_system_rows(db_session)) == 1


def test_changed_sequence_matches_same_year_name_and_updates_external_id(db_session):
    existing = _system(db_session, name="İstanbul Fuarı", external_id="2026:15")
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


def test_same_name_in_another_year_is_not_a_fallback_match(db_session):
    previous = _system(db_session, name="İstanbul Fuarı", external_id="2025:15")
    result = _sync(db_session, _html([_sample_row()]), year=2026)
    assert result.inserted == 1
    assert result.updated == 0

    db_session.expire_all()
    assert db_session.get(FairModel, previous.id).external_id == "2025:15"
    current = [row for row in _system_rows(db_session) if row.external_id == "2026:15"]
    assert len(current) == 1


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
