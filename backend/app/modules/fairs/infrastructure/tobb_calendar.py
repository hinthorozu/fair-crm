from dataclasses import dataclass
from datetime import date, datetime

import httpx
from bs4 import BeautifulSoup

from app.modules.fairs.domain.exceptions import TobbCalendarReadError

TOBB_CALENDAR_URL = "https://fuarlar.tobb.org.tr/FuarTakvimi/{year}"
_REQUIRED_COLUMNS = (
    "Sıra No",
    "Başlangıç Tar.",
    "Bitiş Tar.",
    "Fuarın Adı",
    "Fuar Yeri",
    "Şehir",
    "Düzenleyici",
    "Web",
)


@dataclass(frozen=True)
class TobbFairRow:
    sequence_no: str
    name: str
    organizer: str | None
    venue: str | None
    city: str | None
    start_date: date | None
    end_date: date | None
    website: str | None


def _cell_text(cell) -> str:
    return " ".join(cell.get_text(" ", strip=True).replace("\xa0", " ").split())


def _optional(value: str) -> str | None:
    text = value.strip()
    return text or None


def _parse_date(value: str) -> date | None:
    text = value.strip()
    if not text or text in {"-", "—"}:
        return None
    try:
        return datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError as exc:
        raise TobbCalendarReadError(f"Invalid TOBB date: {text}") from exc


def _find_calendar_table(soup: BeautifulSoup):
    required = set(_REQUIRED_COLUMNS)
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            labels = {_cell_text(cell) for cell in row.find_all(["th", "td"])}
            if required.issubset(labels):
                return table, row
    return None


def parse_tobb_calendar_html(html: str) -> list[TobbFairRow]:
    if not html or not html.strip():
        raise TobbCalendarReadError("TOBB calendar response is empty")
    found = _find_calendar_table(BeautifulSoup(html, "html.parser"))
    if found is None:
        raise TobbCalendarReadError("TOBB calendar table was not found")
    table, header = found
    indexes = {
        _cell_text(cell): index
        for index, cell in enumerate(header.find_all(["th", "td"]))
    }
    missing = [column for column in _REQUIRED_COLUMNS if column not in indexes]
    if missing:
        raise TobbCalendarReadError("TOBB calendar columns are missing")

    rows: list[TobbFairRow] = []
    for row in header.find_all_next("tr"):
        if row.find_parent("table") is not table:
            break
        cells = [_cell_text(cell) for cell in row.find_all(["th", "td"])]
        if not any(cells):
            continue

        def value(column: str) -> str:
            index = indexes[column]
            return cells[index] if index < len(cells) else ""

        if value("Sıra No") == "Sıra No" and value("Fuarın Adı") == "Fuarın Adı":
            continue
        sequence_no = value("Sıra No").strip()
        name = value("Fuarın Adı").strip()
        if not sequence_no.isdigit():
            raise TobbCalendarReadError("TOBB sequence number is missing")
        if not name:
            raise TobbCalendarReadError("TOBB fair name is missing")
        rows.append(
            TobbFairRow(
                sequence_no=sequence_no,
                name=name,
                organizer=_optional(value("Düzenleyici")),
                venue=_optional(value("Fuar Yeri")),
                city=_optional(value("Şehir")),
                start_date=_parse_date(value("Başlangıç Tar.")),
                end_date=_parse_date(value("Bitiş Tar.")),
                website=_optional(value("Web")),
            )
        )
    return rows


class TobbCalendarClient:
    def __init__(
        self,
        *,
        timeout: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._timeout = timeout
        self._transport = transport

    def read(self, year: int) -> list[TobbFairRow]:
        return parse_tobb_calendar_html(self._fetch(year))

    def _fetch(self, year: int) -> str:
        if year < 1990 or year > 2100:
            raise TobbCalendarReadError("Invalid TOBB calendar year")
        url = TOBB_CALENDAR_URL.format(year=year)
        try:
            with httpx.Client(
                timeout=self._timeout,
                transport=self._transport,
                follow_redirects=True,
            ) as client:
                response = client.get(url)
        except httpx.TimeoutException as exc:
            raise TobbCalendarReadError("TOBB calendar request timed out") from exc
        except httpx.HTTPError as exc:
            raise TobbCalendarReadError("TOBB calendar request failed") from exc
        if response.status_code < 200 or response.status_code >= 300:
            raise TobbCalendarReadError(
                f"TOBB calendar request failed with status {response.status_code}"
            )
        if not response.text or not response.text.strip():
            raise TobbCalendarReadError("TOBB calendar response is empty")
        return response.text
