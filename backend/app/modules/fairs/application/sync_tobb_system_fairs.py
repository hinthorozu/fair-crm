from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from typing import Protocol
from collections.abc import Callable
from zoneinfo import ZoneInfo
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
    fair_identity_names_match,
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
class TobbSyncDateChange:
    fair_id: UUID
    name: str
    old_start_date: date | None
    old_end_date: date | None
    new_start_date: date | None
    new_end_date: date | None


@dataclass(frozen=True)
class TobbSyncResult:
    inserted: int
    updated: int
    conflicts: int
    conflict_items: tuple[TobbSyncConflict, ...] = ()
    date_change_warnings: tuple[TobbSyncDateChange, ...] = ()
    changes: tuple[dict, ...] = ()


class TobbReviewWriter(Protocol):
    def mapped_fair_id(self, identity: str, city: str) -> UUID | None: ...
    def propose(self, *, kind: str, fair_id: UUID | None, name: str,
                stored: dict, proposed: dict, source: dict) -> bool: ...


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
    def __init__(self, repository: FairRepository, reader: TobbCalendarReader,
                 reviews: TobbReviewWriter | None = None) -> None:
        self._repository = repository
        self._reader = reader
        self._reviews = reviews

    def execute(self, year: int, *, today: date | None = None, preview: bool = False,
                rows: list[TobbFairRow] | None = None,
                checkpoint: Callable[[], None] | None = None,
                committed_item: Callable[[dict], None] | None = None) -> TobbSyncResult:
        rows = self._reader.read(year) if rows is None else rows
        now = datetime.now(tz=UTC)
        current_day = today if today is not None else datetime.now(ZoneInfo("Europe/Istanbul")).date()
        prepared = [self._prepare(year, row) for row in rows]
        grouped: dict[tuple[str, str], list[_PreparedRow]] = defaultdict(list)
        for item in prepared:
            grouped[(item.identity_name, item.city_key)].append(item)

        catalog = self._repository.list_system_fairs_for_source(source=TOBB_SOURCE)
        retired = [fair for fair in self._repository.list_system_fairs_for_source(source=TOBB_SOURCE, include_archived=True)
                   if fair.deleted_at is not None]
        separated_ids = self._repository.list_system_fair_separation_ids(source=TOBB_SOURCE)
        actions: list[_Action] = []
        matched_groups: dict[tuple[UUID, ...], list[_PreparedRow]] = defaultdict(list)
        candidates_by_ids: dict[tuple[UUID, ...], list[Fair]] = {}
        for key, items in grouped.items():
            mapped_id = self._reviews.mapped_fair_id(*key) if self._reviews else None
            if mapped_id is not None and all(fair.id != mapped_id for fair in catalog):
                mapped = self._repository.get_system_fair(mapped_id)
                if mapped is not None:
                    catalog.append(mapped)
                else:
                    claims = tuple(fair for fair in retired if fair.id == mapped_id)
                    actions.extend(_Action("conflict", item, involved=claims) for item in items)
                    continue
            existing = [
                fair for fair in catalog
                if (mapped_id == fair.id if mapped_id is not None else fair_city_key(fair.city) == key[1]
                and any(fair_identity_names_match(key[0], label) for label in (
                    fair.name, fair.normalized_name, fair.identity_name or "",
                )))
            ]
            if not existing:
                other_city = [fair for fair in catalog if any(fair_identity_names_match(key[0], label)
                              for label in (fair.name, fair.normalized_name, fair.identity_name or ""))]
                if other_city:
                    actions.extend(_Action("conflict", item, involved=tuple(other_city)) for item in items)
                    continue
                retired_claims = [fair for fair in retired if any(fair_identity_names_match(key[0], label)
                    for label in (fair.name, fair.normalized_name, fair.identity_name or ""))]
                if retired_claims:
                    actions.extend(_Action("conflict", item, involved=tuple(retired_claims)) for item in items)
                    continue
                actions.extend(self._plan_without_catalog(items, current_day))
                continue
            ids = tuple(sorted((fair.id for fair in existing), key=str))
            matched_groups[ids].extend(items)
            candidates_by_ids[ids] = existing

        for ids, items in matched_groups.items():
            existing = candidates_by_ids[ids]
            pooled = [fair for fair in existing if fair.id not in separated_ids]
            separated = [fair for fair in existing if fair.id in separated_ids]
            if pooled:
                actions.extend(self._plan(year, items, existing, current_day))
            elif separated:
                actions.extend(self._plan_separated(year, items, separated))

        # Different incoming labels must not independently write the same catalog row.
        targets: dict[UUID, int] = defaultdict(int)
        for action in actions:
            if action.fair is not None and action.kind == "updated":
                targets[action.fair.id] += 1
        actions = [
            _Action("conflict", action.prepared, involved=(action.fair,))
            if action.fair is not None and targets[action.fair.id] > 1 else action
            for action in actions
        ]

        date_change_warnings: list[TobbSyncDateChange] = []
        changes: list[dict] = []
        safe_actions: list[_Action] = []
        for action in actions:
            fair = action.fair
            row = action.prepared.row
            if (action.kind == "updated" and fair is not None
                    and self._same_occurrence(year, action.prepared, fair)
                    and ((fair.start_date, fair.end_date) != (row.start_date, row.end_date)
                         or row.start_date is None or row.end_date is None)):
                date_change_warnings.append(TobbSyncDateChange(
                    fair_id=fair.id, name=fair.name,
                    old_start_date=fair.start_date, old_end_date=fair.end_date,
                    new_start_date=row.start_date, new_end_date=row.end_date,
                ))
                safe_actions.append(_Action("date_review", action.prepared, fair=fair))
            else:
                safe_actions.append(action)
        actions = self._validate_occurrence_claims(safe_actions)

        inserted = 0
        updated = 0
        conflict_items: list[TobbSyncConflict] = []
        seen_conflicts: set[tuple] = set()
        # Sequence swaps form one dependency batch: never commit a released
        # reference before every affected fair has received its replacement.
        deferred_commit = any(
            holder is not None and holder.id != (action.fair.id if action.fair else None)
            for action in actions if action.kind in {"updated", "inserted"}
            for holder in [self._repository.get_system_fair_by_external_id(
                source=TOBB_SOURCE, external_id=action.prepared.external_id)]
        )
        if not preview:
            self._release_replaced_external_ids(actions, now)
        for action in actions:
            if checkpoint:
                checkpoint()
            if action.kind == "date_review":
                changes.append(self._review_change("dates", action, ("start_date", "end_date"), preview))
                self._metadata_reviews(action, changes, preview)
                if committed_item and not preview and not deferred_commit:
                    committed_item(changes[-1])
                continue
            if action.kind == "metadata_review":
                before = len(changes)
                self._metadata_reviews(action, changes, preview)
                if action.fair and (action.fair.start_date is None or action.fair.end_date is None):
                    changes.append(self._review_change("dates", action, ("start_date", "end_date"), preview))
                changes.append({"action": "skipped", "fair_id": str(action.fair.id), "name": action.fair.name,
                                "reason": "end_date_lock", "source": self._source(action.prepared)})
                if committed_item and not preview and not deferred_commit:
                    committed_item(changes[-1])
                continue
            if action.kind == "conflict":
                conflict_items.append(self._conflict(action))
                fair = action.involved[0] if len(action.involved) == 1 else None
                identity_matches = fair and fair.deleted_at is None and any(fair_identity_names_match(action.prepared.identity_name, label)
                    for label in (fair.name, fair.normalized_name, fair.identity_name or ""))
                kind = "city" if identity_matches and fair_city_key(fair.city) != action.prepared.city_key else (
                    "edition" if identity_matches else "name")
                key = (kind, fair.id if fair else None, action.prepared.identity_name, action.prepared.city_key)
                if key in seen_conflicts:
                    continue
                seen_conflicts.add(key)
                source = self._source(action.prepared)
                choices = [self._source(other.prepared) for other in actions if other.kind == "conflict"
                           and other.prepared.identity_name == action.prepared.identity_name
                           and other.prepared.city_key == action.prepared.city_key
                           and tuple(f.id for f in other.involved) == tuple(f.id for f in action.involved)]
                if len(choices) > 1:
                    source["choices"] = choices
                stored = {"city": fair.city} if kind == "city" else {
                    "fair_ids": [str(f.id) for f in action.involved], "names": [f.name for f in action.involved]}
                proposed = {"city": source["city"]} if kind == "city" else {
                    "choices": choices} if len(choices) > 1 else {"source": source}
                changes.append({"action": "review", "kind": kind, "fair_id": str(fair.id) if fair else None,
                                "name": action.prepared.display_name, "stored_values": stored, "proposed_values": proposed})
                if self._reviews and not preview:
                    self._reviews.propose(kind=kind, fair_id=fair.id if fair else None, name=action.prepared.display_name,
                                          stored=stored, proposed=proposed, source=source)
                if committed_item and not preview and not deferred_commit:
                    committed_item(changes[-1])
                continue
            if action.kind in {"updated", "mapped_update"} and action.fair is not None:
                self._metadata_reviews(action, changes, preview)
                changes.append({"action": "updated", "fair_id": str(action.fair.id), "name": action.fair.name,
                                "source": self._source(action.prepared)})
                if not preview:
                    self._apply(action.fair, action.prepared, now=now, today=current_day)
                    if action.kind == "mapped_update":
                        action.fair.external_id = None
                    self._repository.update_system_fair(action.fair)
                updated += 1
            if action.kind == "inserted":
                changes.append({"action": "inserted", "name": action.prepared.display_name,
                                "source": self._source(action.prepared)})
                new_fair = self._new_fair(action.prepared, now, current_day)
                if not preview:
                    self._repository.add(new_fair)
                if new_fair.start_date is None or new_fair.end_date is None:
                    changes.append(self._review_change("dates", _Action("date_review", action.prepared, fair=new_fair),
                                                      ("start_date", "end_date"), preview))
                inserted += 1
            if committed_item and not preview and not deferred_commit:
                committed_item(changes[-1])
        if committed_item and not preview and deferred_commit:
            committed_item({"action": "batch", "name": "TOBB sıra referansları", "changes": changes})
        return TobbSyncResult(
            inserted=inserted,
            updated=updated,
            conflicts=len(conflict_items),
            conflict_items=tuple(conflict_items),
            date_change_warnings=tuple(date_change_warnings),
            changes=tuple(changes),
        )

    @staticmethod
    def _source(prepared: _PreparedRow) -> dict:
        result = asdict(prepared.row)
        for key in ("start_date", "end_date"):
            result[key] = result[key].isoformat() if result[key] else None
        result.update(external_id=prepared.external_id, normalized_name=prepared.normalized_name,
                      identity_name=prepared.identity_name)
        if result["website"]:
            result["website"] = normalize_website(result["website"])
        return result

    def _review_change(self, kind: str, action: _Action, fields: tuple[str, ...], preview: bool) -> dict:
        fair = action.fair
        assert fair is not None
        source = self._source(action.prepared)
        stored = {field: (value.isoformat() if isinstance(value, date) else value)
                  for field in fields for value in [getattr(fair, field)]}
        if kind == "dates":
            stored["_date_revision"] = fair.tobb_date_revision
        proposed = {field: source[field] for field in fields}
        active = True
        if self._reviews and not preview:
            active = self._reviews.propose(kind=kind, fair_id=fair.id, name=fair.name,
                                          stored=stored, proposed=proposed, source=source)
        return {"action": "review" if active else "skipped", "kind": kind, "fair_id": str(fair.id),
                "name": fair.name, "stored_values": stored, "proposed_values": proposed}

    def _metadata_reviews(self, action: _Action, changes: list[dict], preview: bool) -> None:
        fair = action.fair
        assert fair is not None
        for field in ("organizer", "venue", "website", "city"):
            incoming = getattr(action.prepared.row, field)
            if field == "website" and incoming:
                incoming = normalize_website(incoming)
            if incoming and incoming != getattr(fair, field):
                changes.append(self._review_change(field, action, (field,), preview))

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

    def _plan(self, year: int, items: list[_PreparedRow], existing: list[Fair], today: date) -> list[_Action]:
        if not existing:
            return self._plan_without_catalog(items, today)
        if len(existing) == 1:
            return self._plan_sole(year, items, existing[0], today)
        return [_Action("conflict", item, involved=tuple(existing)) for item in items]

    @staticmethod
    def _select_occurrence(items: list[_PreparedRow], today: date) -> _PreparedRow | None:
        if len(items) == 1:
            return items[0]
        ongoing = [item for item in items if item.row.start_date is not None
                   and item.row.end_date is not None
                   and item.row.start_date <= today <= item.row.end_date]
        return ongoing[0] if len(ongoing) == 1 else None

    def _plan_without_catalog(self, items: list[_PreparedRow], today: date) -> list[_Action]:
        selected = self._select_occurrence(items, today)
        if selected is None:
            return [_Action("conflict", item) for item in items]
        return [_Action("inserted", selected)]

    @staticmethod
    def _same_occurrence(year: int, item: _PreparedRow, fair: Fair) -> bool:
        if _occurrence_year(fair) != year:
            return False
        stored_edition = edition_key(fair.normalized_name)
        if stored_edition and item.edition_key:
            return stored_edition == item.edition_key
        # A sequence is only an occurrence reference after identity and city match.
        return fair.external_id == item.external_id or (
            fair.start_date is not None and fair.end_date is not None
            and (fair.start_date, fair.end_date) == (item.row.start_date, item.row.end_date)
        )

    def _plan_sole(self, year: int, items: list[_PreparedRow], fair: Fair, today: date) -> list[_Action]:
        stored_year = _occurrence_year(fair)
        if stored_year is not None and year < stored_year:
            return [_Action("conflict", item, involved=(fair,)) for item in items]
        same = [item for item in items if self._same_occurrence(year, item, fair)]
        if len(same) > 1:
            return [_Action("conflict", item, involved=(fair,)) for item in items]
        if same and (fair.start_date, fair.end_date) != (same[0].row.start_date, same[0].row.end_date):
            # A correction warning takes precedence over replacing this record.
            return [_Action("updated", same[0], fair=fair)]
        if fair.end_date is None or fair.end_date >= today:
            # Metadata refresh is valid; a new edition cannot replace it.
            if same:
                return [_Action("updated", same[0], fair=fair)]
            return ([_Action("conflict", item, involved=(fair,)) for item in items] if len(items) > 1
                    else [_Action("metadata_review", items[0], fair=fair)])
        if stored_year == year and not same and any(
            not edition_key(fair.normalized_name) or not item.edition_key for item in items
        ):
            return [_Action("conflict", item, involved=(fair,)) for item in items]
        newer = [item for item in items if item not in same
                 and item.row.start_date is not None
                 and item.row.start_date > fair.end_date]
        selected = self._select_occurrence(newer, today) if newer else None
        if selected is not None:
            return [_Action("updated", selected, fair=fair)]
        if newer:
            return [_Action("conflict", item, involved=(fair,)) for item in newer]
        if same:
            return [_Action("updated", same[0], fair=fair)]
        return [_Action("conflict", item, involved=(fair,)) for item in items]

    def _plan_separated(
        self, year: int, items: list[_PreparedRow], separated: list[Fair]
    ) -> list[_Action]:
        """Fairs the user kept distinct are not conflicts and are not guessed across years."""
        same_year = [fair for fair in separated if _occurrence_year(fair) == year]
        actions: list[_Action] = []
        for fair in same_year:
            matches = [item for item in items if self._same_occurrence(year, item, fair)]
            if len(matches) != 1:
                continue
            item = matches[0]
            candidates = [candidate for candidate in same_year
                          if self._same_occurrence(year, item, candidate)]
            if len(candidates) == 1:
                actions.append(_Action("updated", item, fair=fair))
        return actions

    def _validate_occurrence_claims(self, actions: list[_Action]) -> list[_Action]:
        """A reused TOBB sequence cannot mutate a blocked or unrelated fair."""
        holders = {
            action.prepared.external_id: self._repository.get_system_fair_by_external_id(
                source=TOBB_SOURCE, external_id=action.prepared.external_id,
            ) for action in actions if action.kind in {"updated", "inserted"}
        }
        while True:
            moving = {
                action.fair.id for action in actions
                if action.kind == "updated" and action.fair is not None
            }
            claims: dict[str, int] = defaultdict(int)
            for action in actions:
                if action.kind in {"updated", "inserted"}:
                    claims[action.prepared.external_id] += 1
            result: list[_Action] = []
            changed = False
            for action in actions:
                if action.kind not in {"updated", "inserted"}:
                    result.append(action)
                    continue
                holder = holders[action.prepared.external_id]
                owner_id = action.fair.id if action.fair is not None else None
                if claims[action.prepared.external_id] > 1 or (
                    holder is not None and holder.id != owner_id and holder.id not in moving
                ):
                    if (claims[action.prepared.external_id] == 1 and action.fair is not None and self._reviews
                            and self._reviews.mapped_fair_id(action.prepared.identity_name, action.prepared.city_key) == action.fair.id):
                        # An explicit identity decision never transfers another
                        # fair's sequence reference or any tenant relationships.
                        result.append(_Action("mapped_update", action.prepared, fair=action.fair))
                        changed = True
                        continue
                    involved = tuple(fair for fair in (action.fair, holder) if fair is not None)
                    result.append(_Action("conflict", action.prepared, involved=involved))
                    changed = True
                else:
                    result.append(action)
            if not changed:
                return result
            actions = result

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
        fair.normalized_name = prepared.normalized_name
        fair.identity_name = prepared.identity_name
        fair.start_date = row.start_date
        fair.end_date = row.end_date
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
