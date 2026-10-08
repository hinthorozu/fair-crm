from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol
from uuid import UUID, uuid4

from app.modules.fairs.domain.entities import Fair
from app.modules.fairs.domain.exceptions import InvalidFairDateRangeError, InvalidFairNameError
from app.modules.fairs.domain.ports import FairRepository
from app.modules.fairs.domain.services.normalizers import (
    canonicalize_fair_name,
    compute_identity_name,
    compute_normalized_name,
    edition_key,
    fair_city_key,
    normalize_website,
    system_fair_status_for_dates,
)
from app.modules.fairs.domain.value_objects import FairStatus
from app.modules.fairs.infrastructure.tobb_calendar import TobbFairRow

TOBB_SOURCE = "tobb"
TOBB_COUNTRY = "Türkiye"


def _edition_year(external_id: str | None) -> int | None:
    if not external_id or ":" not in external_id:
        return None
    prefix = external_id.split(":", 1)[0]
    if not prefix.isdigit():
        return None
    return int(prefix)


def _occurrence_year(fair: Fair) -> int | None:
    year = _edition_year(fair.external_id)
    if year is not None:
        return year
    if fair.start_date is not None:
        return fair.start_date.year
    return None


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
class TobbSyncConflict:
    name: str
    identity_name: str
    city: str | None
    fair_ids: tuple[UUID, ...]


@dataclass(frozen=True)
class TobbSyncResult:
    inserted: int
    updated: int
    conflicts: int
    conflict_items: tuple[TobbSyncConflict, ...] = ()


@dataclass(frozen=True)
class _PreparedRow:
    row: TobbFairRow
    external_id: str
    display_name: str
    normalized_name: str
    identity_name: str
    city_key: str
    edition_key: tuple[str, ...]


@dataclass(frozen=True)
class _Action:
    kind: str
    prepared: _PreparedRow
    fair: Fair | None = None
    involved: tuple[Fair, ...] = ()


class SyncTobbSystemFairsUseCase:
    def __init__(self, repository: FairRepository, reader: TobbCalendarReader) -> None:
        self._repository = repository
        self._reader = reader

    def execute(self, year: int, *, today: date | None = None) -> TobbSyncResult:
        rows = self._reader.read(year)
        now = datetime.now(tz=UTC)
        current_day = today if today is not None else date.today()
        prepared = [self._prepare(year, row) for row in rows]
        grouped: dict[tuple[str, str], list[_PreparedRow]] = defaultdict(list)
        for item in prepared:
            grouped[(item.identity_name, item.city_key)].append(item)

        catalog = self._repository.list_system_fairs_for_source(source=TOBB_SOURCE)
        separated_ids = self._repository.list_system_fair_separation_ids(source=TOBB_SOURCE)
        by_key: dict[tuple[str, str], list[Fair]] = defaultdict(list)
        for fair in catalog:
            key = (compute_identity_name(name=fair.name), fair_city_key(fair.city))
            by_key[key].append(fair)

        actions: list[_Action] = []
        for key, items in grouped.items():
            existing = by_key.get(key, [])
            pooled = [fair for fair in existing if fair.id not in separated_ids]
            separated = [fair for fair in existing if fair.id in separated_ids]
            if pooled:
                actions.extend(self._plan(year, items, pooled))
            elif separated:
                actions.extend(self._plan_separated(year, items, separated))
            else:
                actions.extend(self._plan(year, items, []))

        inserted = 0
        updated = 0
        conflict_items: list[TobbSyncConflict] = []
        self._release_replaced_external_ids(actions, now)
        for action in actions:
            if action.kind == "conflict":
                conflict_items.append(self._conflict(action))
                continue
            if action.kind == "updated" and action.fair is not None:
                self._apply(action.fair, action.prepared, now=now, today=current_day)
                self._repository.update_system_fair(action.fair)
                updated += 1
                continue
            if action.kind == "inserted":
                self._repository.add(self._new_fair(action.prepared, now, current_day))
                inserted += 1
        return TobbSyncResult(
            inserted=inserted,
            updated=updated,
            conflicts=len(conflict_items),
            conflict_items=tuple(conflict_items),
        )

    def _prepare(self, year: int, row: TobbFairRow) -> _PreparedRow:
        external_id = f"{year}:{row.sequence_no}"
        display_name = canonicalize_fair_name(row.name)
        normalized_name = compute_normalized_name(name=display_name)
        identity_name = compute_identity_name(name=display_name)
        if not display_name or not normalized_name or not identity_name:
            raise InvalidFairNameError("name must not be empty")
        if row.start_date and row.end_date and row.end_date < row.start_date:
            raise InvalidFairDateRangeError("end_date must not be before start_date")
        return _PreparedRow(
            row=row,
            external_id=external_id,
            display_name=display_name,
            normalized_name=normalized_name,
            identity_name=identity_name,
            city_key=fair_city_key(row.city),
            edition_key=edition_key(display_name),
        )

    def _plan(self, year: int, items: list[_PreparedRow], existing: list[Fair]) -> list[_Action]:
        if not existing:
            return self._plan_without_catalog(items)
        if len(existing) == 1:
            return self._plan_sole(year, items, existing[0])
        return self._plan_many(year, items, existing)

    def _plan_without_catalog(self, items: list[_PreparedRow]) -> list[_Action]:
        counts = Counter(item.edition_key for item in items)
        actions: list[_Action] = []
        for item in items:
            if len(items) > 1 and (not item.edition_key or counts[item.edition_key] > 1):
                actions.append(_Action("conflict", item))
                continue
            actions.append(_Action("inserted", item))
        return actions

    def _plan_sole(self, year: int, items: list[_PreparedRow], fair: Fair) -> list[_Action]:
        stored_year = _occurrence_year(fair)
        stored_edition = edition_key(fair.name)
        if len(items) == 1:
            item = items[0]
            if stored_year is not None and year < stored_year:
                return [_Action("conflict", item, involved=(fair,))]
            if (
                stored_year == year
                and item.edition_key
                and stored_edition
                and item.edition_key != stored_edition
            ):
                return [_Action("inserted", item)]
            if stored_year == year and item.edition_key != stored_edition and (
                not item.edition_key or not stored_edition
            ):
                return [_Action("conflict", item, involved=(fair,))]
            return [_Action("updated", item, fair=fair)]

        counts = Counter(item.edition_key for item in items)
        actions: list[_Action] = []
        consumed = False
        for item in items:
            if not item.edition_key or counts[item.edition_key] > 1:
                actions.append(_Action("conflict", item, involved=(fair,)))
                continue
            if (
                not consumed
                and stored_year == year
                and stored_edition == item.edition_key
            ):
                consumed = True
                actions.append(_Action("updated", item, fair=fair))
                continue
            if stored_year == year and stored_edition != item.edition_key:
                actions.append(_Action("inserted", item))
                continue
            actions.append(_Action("conflict", item, involved=(fair,)))
        return actions

    def _plan_separated(
        self, year: int, items: list[_PreparedRow], separated: list[Fair]
    ) -> list[_Action]:
        """Fairs the user kept distinct are not conflicts and are not guessed across years."""
        same_year = [fair for fair in separated if _occurrence_year(fair) == year]
        counts = Counter(item.edition_key for item in items)
        actions: list[_Action] = []
        used: set[UUID] = set()
        for item in items:
            if not item.edition_key or counts[item.edition_key] > 1:
                continue
            matches = [
                fair
                for fair in same_year
                if fair.id not in used and edition_key(fair.name) == item.edition_key
            ]
            if len(matches) == 1:
                used.add(matches[0].id)
                actions.append(_Action("updated", item, fair=matches[0]))
        return actions

    def _plan_many(self, year: int, items: list[_PreparedRow], existing: list[Fair]) -> list[_Action]:
        same_year = [fair for fair in existing if _occurrence_year(fair) == year]
        counts = Counter(item.edition_key for item in items)
        actions: list[_Action] = []
        used: set[UUID] = set()
        for item in items:
            if not item.edition_key or counts[item.edition_key] > 1:
                actions.append(_Action("conflict", item, involved=tuple(existing)))
                continue
            matches = [
                fair
                for fair in same_year
                if fair.id not in used and edition_key(fair.name) == item.edition_key
            ]
            if len(matches) == 1:
                used.add(matches[0].id)
                actions.append(_Action("updated", item, fair=matches[0]))
                continue
            actions.append(_Action("conflict", item, involved=tuple(existing)))
        return actions

    def _release_replaced_external_ids(self, actions: list[_Action], now: datetime) -> None:
        claimed: dict[str, UUID] = {}
        for action in actions:
            if action.kind == "updated" and action.fair is not None:
                claimed[action.prepared.external_id] = action.fair.id
        for action in actions:
            if action.kind != "inserted":
                continue
            external_id = action.prepared.external_id
            claimed.setdefault(external_id, uuid4())
        for external_id, owner_id in claimed.items():
            holder = self._repository.get_system_fair_by_external_id(
                source=TOBB_SOURCE,
                external_id=external_id,
            )
            if holder is None or holder.id == owner_id:
                continue
            holder.external_id = None
            holder.updated_at = now
            self._repository.update_system_fair(holder)

    def _conflict(self, action: _Action) -> TobbSyncConflict:
        fair_ids = tuple(sorted((fair.id for fair in action.involved), key=str))
        return TobbSyncConflict(
            name=action.prepared.display_name,
            identity_name=action.prepared.identity_name,
            city=action.prepared.row.city,
            fair_ids=fair_ids,
        )

    def _apply(
        self,
        fair: Fair,
        prepared: _PreparedRow,
        *,
        now: datetime,
        today: date,
    ) -> None:
        row = prepared.row
        fair.name = prepared.display_name
        fair.normalized_name = prepared.normalized_name
        fair.identity_name = prepared.identity_name
        fair.organizer = row.organizer
        fair.venue = row.venue
        fair.city = row.city
        fair.country = TOBB_COUNTRY
        fair.start_date = row.start_date
        fair.end_date = row.end_date
        fair.website = normalize_website(row.website) if row.website else None
        fair.external_id = prepared.external_id
        fair.status = _system_status(row, today, fair.status)
        fair.updated_at = now

    def _new_fair(self, prepared: _PreparedRow, now: datetime, today: date) -> Fair:
        row = prepared.row
        return Fair(
            id=uuid4(),
            organization_id=None,
            name=prepared.display_name,
            organizer=row.organizer,
            venue=row.venue,
            city=row.city,
            country=TOBB_COUNTRY,
            start_date=row.start_date,
            end_date=row.end_date,
            website=normalize_website(row.website) if row.website else None,
            status=_system_status(row, today, FairStatus.PLANNED),
            description=None,
            normalized_name=prepared.normalized_name,
            created_at=now,
            updated_at=now,
            deleted_at=None,
            origin="system",
            source=TOBB_SOURCE,
            external_id=prepared.external_id,
            identity_name=prepared.identity_name,
        )
