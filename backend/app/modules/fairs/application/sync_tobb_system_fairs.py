from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol
from uuid import uuid4

from app.modules.fairs.domain.entities import Fair
from app.modules.fairs.domain.exceptions import InvalidFairDateRangeError, InvalidFairNameError
from app.modules.fairs.domain.ports import FairRepository
from app.modules.fairs.domain.services.normalizers import (
    canonicalize_fair_name,
    compute_normalized_name,
    normalize_website,
    system_fair_status_for_dates,
)
from app.modules.fairs.domain.value_objects import FairStatus
from app.modules.fairs.infrastructure.tobb_calendar import TobbFairRow

TOBB_SOURCE = "tobb"
TOBB_COUNTRY = "Türkiye"


def _system_status(row: TobbFairRow, today: date, current: FairStatus) -> FairStatus:
    if current == FairStatus.ARCHIVED:
        return current
    derived = system_fair_status_for_dates(
        start_date=row.start_date,
        end_date=row.end_date,
        today=today,
    )
    return derived if derived is not None else current


class TobbCalendarReader(Protocol):
    def read(self, year: int) -> list[TobbFairRow]: ...


@dataclass(frozen=True)
class TobbSyncResult:
    inserted: int
    updated: int
    conflicts: int


class SyncTobbSystemFairsUseCase:
    def __init__(self, repository: FairRepository, reader: TobbCalendarReader) -> None:
        self._repository = repository
        self._reader = reader

    def execute(self, year: int) -> TobbSyncResult:
        rows = self._reader.read(year)
        now = datetime.now(tz=UTC)
        today = date.today()
        inserted = 0
        updated = 0
        conflicts = 0
        for row in rows:
            outcome = self._sync_row(year, row, now, today)
            if outcome == "inserted":
                inserted += 1
            elif outcome == "updated":
                updated += 1
            else:
                conflicts += 1
        return TobbSyncResult(inserted=inserted, updated=updated, conflicts=conflicts)

    def _sync_row(self, year: int, row: TobbFairRow, now: datetime, today: date) -> str:
        external_id = f"{year}:{row.sequence_no}"
        display_name = canonicalize_fair_name(row.name)
        normalized_name = compute_normalized_name(name=display_name)
        if not display_name or not normalized_name:
            raise InvalidFairNameError("name must not be empty")
        if (
            row.start_date
            and row.end_date
            and row.end_date < row.start_date
        ):
            raise InvalidFairDateRangeError("end_date must not be before start_date")

        existing = self._repository.get_system_fair_by_external_id(
            source=TOBB_SOURCE,
            external_id=external_id,
        )
        if existing is not None:
            self._apply(
                existing,
                row,
                display_name=display_name,
                external_id=external_id,
                normalized_name=normalized_name,
                now=now,
                today=today,
            )
            self._repository.update_system_fair(existing)
            return "updated"

        matches = self._repository.list_system_fairs_by_year_and_name(
            source=TOBB_SOURCE,
            year=year,
            normalized_name=normalized_name,
        )
        if len(matches) > 1:
            return "conflict"
        if len(matches) == 1:
            fair = matches[0]
            self._apply(
                fair,
                row,
                display_name=display_name,
                external_id=external_id,
                normalized_name=normalized_name,
                now=now,
                today=today,
            )
            self._repository.update_system_fair(fair)
            return "updated"

        self._repository.add(
            self._new_fair(row, display_name, external_id, normalized_name, now, today)
        )
        return "inserted"

    def _apply(
        self,
        fair: Fair,
        row: TobbFairRow,
        *,
        display_name: str,
        external_id: str,
        normalized_name: str,
        now: datetime,
        today: date,
    ) -> None:
        fair.name = display_name
        fair.normalized_name = normalized_name
        fair.organizer = row.organizer
        fair.venue = row.venue
        fair.city = row.city
        fair.country = TOBB_COUNTRY
        fair.start_date = row.start_date
        fair.end_date = row.end_date
        fair.website = normalize_website(row.website) if row.website else None
        fair.external_id = external_id
        fair.status = _system_status(row, today, fair.status)
        fair.updated_at = now

    def _new_fair(
        self,
        row: TobbFairRow,
        display_name: str,
        external_id: str,
        normalized_name: str,
        now: datetime,
        today: date,
    ) -> Fair:
        return Fair(
            id=uuid4(),
            organization_id=None,
            name=display_name,
            organizer=row.organizer,
            venue=row.venue,
            city=row.city,
            country=TOBB_COUNTRY,
            start_date=row.start_date,
            end_date=row.end_date,
            website=normalize_website(row.website) if row.website else None,
            status=_system_status(row, today, FairStatus.PLANNED),
            description=None,
            normalized_name=normalized_name,
            created_at=now,
            updated_at=now,
            deleted_at=None,
            origin="system",
            source=TOBB_SOURCE,
            external_id=external_id,
        )
