from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from app.modules.fairs.domain.exceptions import (
    FairAlreadyArchivedError,
    FairNotArchivedError,
    InvalidFairAdapterConfigError,
    InvalidFairDateRangeError,
    InvalidFairNameError,
)
from app.modules.fairs.domain.services.normalizers import (
    compute_normalized_name,
    normalize_adapter_key,
    normalize_source_url,
    normalize_website,
    resolve_status_for_dates,
)
from app.modules.fairs.domain.value_objects import FairStatus


def _validate_date_range(start_date: Optional[date], end_date: Optional[date]) -> None:
    if start_date and end_date and end_date < start_date:
        raise InvalidFairDateRangeError("end_date must not be before start_date")


def _validate_adapter_fields(
    adapter_key: Optional[str],
    source_url: Optional[str],
) -> None:
    if adapter_key and not source_url:
        raise InvalidFairAdapterConfigError("source_url is required when adapter_key is set")
    if source_url:
        normalize_source_url(source_url)


@dataclass
class Fair:
    id: UUID
    organization_id: UUID
    name: str
    organizer: Optional[str]
    venue: Optional[str]
    city: Optional[str]
    country: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    website: Optional[str]
    status: FairStatus
    description: Optional[str]
    normalized_name: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]
    archived_from_status: Optional[FairStatus] = None
    adapter_key: Optional[str] = None
    source_url: Optional[str] = None
    scraper_config: Optional[dict[str, Any]] = None

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        name: str,
        organizer: Optional[str] = None,
        venue: Optional[str] = None,
        city: Optional[str] = None,
        country: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        website: Optional[str] = None,
        status: FairStatus = FairStatus.PLANNED,
        description: Optional[str] = None,
        adapter_key: Optional[str] = None,
        source_url: Optional[str] = None,
        scraper_config: Optional[dict[str, Any]] = None,
        now: datetime,
    ) -> "Fair":
        trimmed_name = name.strip()
        if not trimmed_name:
            raise InvalidFairNameError("name must not be empty")

        _validate_date_range(start_date, end_date)

        normalized_adapter_key = normalize_adapter_key(adapter_key)
        normalized_source_url = normalize_source_url(source_url) if source_url else None
        _validate_adapter_fields(normalized_adapter_key, normalized_source_url)

        resolved_status = resolve_status_for_dates(
            requested_status=status,
            start_date=start_date,
            end_date=end_date,
            today=now.date(),
            default=FairStatus.PLANNED,
        )

        return cls(
            id=uuid4(),
            organization_id=organization_id,
            name=trimmed_name,
            organizer=organizer.strip() if organizer else None,
            venue=venue.strip() if venue else None,
            city=city.strip() if city else None,
            country=country.strip() if country else None,
            start_date=start_date,
            end_date=end_date,
            website=normalize_website(website) if website else None,
            status=resolved_status,
            description=description.strip() if description else None,
            normalized_name=compute_normalized_name(name=trimmed_name),
            created_at=now,
            updated_at=now,
            deleted_at=None,
            archived_from_status=None,
            adapter_key=normalized_adapter_key,
            source_url=normalized_source_url,
            scraper_config=scraper_config,
        )

    def ensure_mutable(self) -> None:
        if self.status == FairStatus.ARCHIVED or self.deleted_at is not None:
            raise FairAlreadyArchivedError("Fair is archived")

    def update_fields(
        self,
        *,
        name: Optional[str] = None,
        organizer: Optional[str] = None,
        venue: Optional[str] = None,
        city: Optional[str] = None,
        country: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        website: Optional[str] = None,
        status: Optional[FairStatus] = None,
        description: Optional[str] = None,
        adapter_key: Optional[str] = None,
        source_url: Optional[str] = None,
        scraper_config: Optional[dict[str, Any]] = None,
        now: datetime,
        clear_start_date: bool = False,
        clear_end_date: bool = False,
        clear_scraper_config: bool = False,
        date_fields_updated: bool = False,
    ) -> None:
        self.ensure_mutable()

        if name is not None:
            trimmed = name.strip()
            if not trimmed:
                raise InvalidFairNameError("name must not be empty")
            self.name = trimmed
            self.normalized_name = compute_normalized_name(name=trimmed)

        if organizer is not None:
            self.organizer = organizer.strip() if organizer else None
        if venue is not None:
            self.venue = venue.strip() if venue else None
        if city is not None:
            self.city = city.strip() if city else None
        if country is not None:
            self.country = country.strip() if country else None

        new_start = None if clear_start_date else (start_date if start_date is not None else self.start_date)
        new_end = None if clear_end_date else (end_date if end_date is not None else self.end_date)
        _validate_date_range(new_start, new_end)
        if clear_start_date or start_date is not None:
            self.start_date = new_start
        if clear_end_date or end_date is not None:
            self.end_date = new_end

        if website is not None:
            self.website = normalize_website(website) if website else None

        if description is not None:
            self.description = description.strip() if description else None

        if adapter_key is not None:
            self.adapter_key = normalize_adapter_key(adapter_key)
        if source_url is not None:
            self.source_url = normalize_source_url(source_url) if source_url else None
        if clear_scraper_config:
            self.scraper_config = None
        elif scraper_config is not None:
            self.scraper_config = scraper_config

        # Date-driven Planlandı overrides client status when entered dates are today/future.
        entered_start = start_date if (not clear_start_date and start_date is not None) else None
        entered_end = end_date if (not clear_end_date and end_date is not None) else None
        if date_fields_updated and (entered_start is not None or entered_end is not None):
            self.status = resolve_status_for_dates(
                requested_status=status,
                start_date=entered_start,
                end_date=entered_end,
                today=now.date(),
                default=self.status,
            )
        elif status is not None and status != FairStatus.ARCHIVED:
            self.status = status

        _validate_adapter_fields(self.adapter_key, self.source_url)

        self.updated_at = now

    def is_archived(self) -> bool:
        return self.deleted_at is not None or self.status == FairStatus.ARCHIVED

    def archive(self, *, now: datetime) -> None:
        if self.status == FairStatus.ARCHIVED and self.deleted_at is not None:
            return
        if self.status != FairStatus.ARCHIVED:
            self.archived_from_status = self.status
        self.status = FairStatus.ARCHIVED
        self.deleted_at = now
        self.updated_at = now

    def restore(self, *, now: datetime) -> None:
        if not self.is_archived():
            raise FairNotArchivedError("Fair is not archived")

        restore_status = self.archived_from_status
        if restore_status is None or restore_status == FairStatus.ARCHIVED:
            restore_status = FairStatus.PLANNED

        self.status = restore_status
        self.deleted_at = None
        self.archived_from_status = None
        self.updated_at = now
