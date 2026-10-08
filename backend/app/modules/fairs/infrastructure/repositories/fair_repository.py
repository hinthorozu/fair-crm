from datetime import date, datetime
from uuid import UUID

from sqlalchemy import and_, asc, case, desc, not_, nullslast, or_
from sqlalchemy.orm import Query, Session

from app.core.pagination import build_order_clause, build_paginated_meta, normalize_page_params
from app.modules.fairs.domain.entities import Fair
from app.modules.fairs.domain.services.normalizers import compute_identity_name
from app.modules.fairs.domain.ports import FairListResult
from app.modules.fairs.domain.value_objects import FairStatus
from app.modules.fairs.infrastructure.persistence.mappers import (
    entity_to_model,
    model_to_entity,
    update_model_from_entity,
)
from app.modules.fairs.infrastructure.persistence.models import FairModel

SEARCH_FIELDS = (
    FairModel.name,
    FairModel.normalized_name,
    FairModel.organizer,
    FairModel.venue,
    FairModel.city,
    FairModel.country,
    FairModel.website,
    FairModel.description,
)

def _default_date_order(today: date):
    """Upcoming dates ascending, then past dates descending. Null dates stay last."""
    has_date = FairModel.start_date.isnot(None)
    upcoming = and_(has_date, FairModel.start_date >= today)
    past = and_(has_date, FairModel.start_date < today)
    group = case((upcoming, 0), (past, 1), else_=2)
    upcoming_key = case((upcoming, FairModel.start_date), else_=None)
    past_key = case((past, FairModel.start_date), else_=None)
    return (
        asc(group),
        nullslast(asc(upcoming_key)),
        nullslast(desc(past_key)),
        asc(FairModel.id),
    )


FAIR_SORT_FIELDS = {
    "created_at": FairModel.created_at,
    "updated_at": FairModel.updated_at,
    "name": FairModel.name,
    "start_date": FairModel.start_date,
    "city": FairModel.city,
    "country": FairModel.country,
    "organizer": FairModel.organizer,
    "venue": FairModel.venue,
    "status": FairModel.status,
}


def _visible_to(organization_id: UUID):
    return or_(
        FairModel.organization_id == organization_id,
        FairModel.origin == "system",
    )


def _status_clause(status: FairStatus, today: date):
    """Organization fairs match the stored status. System fairs match the date lifecycle."""
    terminal = (FairStatus.CANCELLED.value, FairStatus.ARCHIVED.value)
    past = and_(FairModel.end_date.isnot(None), FairModel.end_date < today)
    future = and_(FairModel.start_date.isnot(None), FairModel.start_date > today)
    current = and_(
        FairModel.start_date.isnot(None),
        FairModel.start_date <= today,
        or_(FairModel.end_date.is_(None), FairModel.end_date >= today),
    )
    undetermined = and_(
        FairModel.start_date.is_(None),
        or_(FairModel.end_date.is_(None), FairModel.end_date >= today),
    )
    derived = {
        FairStatus.COMPLETED: past,
        FairStatus.PLANNED: and_(future, not_(past)),
        FairStatus.ACTIVE: current,
    }.get(status)
    open_system = and_(
        FairModel.origin == "system",
        FairModel.status.notin_(terminal),
    )
    clauses = [
        and_(FairModel.origin != "system", FairModel.status == status.value),
        and_(FairModel.origin == "system", FairModel.status == status.value, FairModel.status.in_(terminal)),
    ]
    if derived is not None:
        clauses.append(and_(open_system, derived))
        clauses.append(and_(open_system, undetermined, FairModel.status == status.value))
    return or_(*clauses)


class SqlAlchemyFairRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, fair: Fair) -> Fair:
        model = entity_to_model(fair)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return model_to_entity(model)

    def get_by_id(self, organization_id: UUID, fair_id: UUID) -> Fair | None:
        model = (
            self._session.query(FairModel)
            .filter(
                FairModel.organization_id == organization_id,
                FairModel.id == fair_id,
                FairModel.deleted_at.is_(None),
            )
            .one_or_none()
        )
        return model_to_entity(model) if model else None

    def get_by_id_including_archived(
        self, organization_id: UUID, fair_id: UUID
    ) -> Fair | None:
        model = (
            self._session.query(FairModel)
            .filter(
                FairModel.organization_id == organization_id,
                FairModel.id == fair_id,
            )
            .one_or_none()
        )
        return model_to_entity(model) if model else None

    def get_visible(self, organization_id: UUID, fair_id: UUID) -> Fair | None:
        model = (
            self._session.query(FairModel)
            .filter(
                FairModel.id == fair_id,
                FairModel.deleted_at.is_(None),
                _visible_to(organization_id),
            )
            .one_or_none()
        )
        return model_to_entity(model) if model else None

    def get_visible_including_archived(
        self, organization_id: UUID, fair_id: UUID
    ) -> Fair | None:
        model = (
            self._session.query(FairModel)
            .filter(
                FairModel.id == fair_id,
                _visible_to(organization_id),
            )
            .one_or_none()
        )
        return model_to_entity(model) if model else None

    def update(self, fair: Fair) -> Fair:
        query = self._session.query(FairModel).filter(FairModel.id == fair.id)
        if fair.organization_id is None:
            query = query.filter(
                FairModel.organization_id.is_(None),
                FairModel.origin == "system",
            )
        else:
            query = query.filter(FairModel.organization_id == fair.organization_id)
        model = query.one()
        update_model_from_entity(model, fair)
        self._session.flush()
        self._session.refresh(model)
        return model_to_entity(model)

    def get_system_fair_by_external_id(self, *, source: str, external_id: str) -> Fair | None:
        model = (
            self._session.query(FairModel)
            .filter(
                FairModel.origin == "system",
                FairModel.source == source,
                FairModel.external_id == external_id,
            )
            .one_or_none()
        )
        return model_to_entity(model) if model else None

    def list_system_fairs_for_source(self, *, source: str) -> list[Fair]:
        models = (
            self._session.query(FairModel)
            .filter(
                FairModel.origin == "system",
                FairModel.source == source,
                FairModel.deleted_at.is_(None),
            )
            .all()
        )
        return [model_to_entity(model) for model in models]

    def get_system_fair(self, fair_id: UUID) -> Fair | None:
        model = (
            self._session.query(FairModel)
            .filter(FairModel.id == fair_id, FairModel.origin == "system")
            .one_or_none()
        )
        return model_to_entity(model) if model else None

    def list_system_fair_separation_ids(self, *, source: str) -> set[UUID]:
        from app.modules.fairs.infrastructure.persistence.models import SystemFairSeparationModel

        rows = (
            self._session.query(SystemFairSeparationModel.fair_id)
            .filter(SystemFairSeparationModel.source == source)
            .all()
        )
        return {row[0] for row in rows}

    def update_system_fair(self, fair: Fair) -> Fair:
        model = (
            self._session.query(FairModel)
            .filter(
                FairModel.id == fair.id,
                FairModel.origin == "system",
                FairModel.source == fair.source,
            )
            .one()
        )
        model.name = fair.name
        model.normalized_name = fair.normalized_name
        model.organizer = fair.organizer
        model.venue = fair.venue
        model.city = fair.city
        model.country = fair.country
        model.start_date = fair.start_date
        model.end_date = fair.end_date
        model.website = fair.website
        model.external_id = fair.external_id
        model.identity_name = fair.identity_name or compute_identity_name(name=fair.name)
        model.status = fair.status.value
        model.updated_at = fair.updated_at
        self._session.flush()
        self._session.refresh(model)
        return model_to_entity(model)

    def _filtered_query(
        self,
        organization_id: UUID,
        *,
        status: FairStatus | None = None,
        include_archived: bool = False,
        country: str | None = None,
        search: str | None = None,
        include_system: bool = False,
    ) -> Query:
        ownership = (
            _visible_to(organization_id)
            if include_system
            else FairModel.organization_id == organization_id
        )
        query = self._session.query(FairModel).filter(ownership)

        if status == FairStatus.ARCHIVED:
            query = query.filter(FairModel.deleted_at.isnot(None))
        elif status is not None:
            query = query.filter(FairModel.deleted_at.is_(None))
            query = query.filter(_status_clause(status, date.today()))
        elif include_archived:
            query = query.filter(FairModel.deleted_at.isnot(None))
        # else: no status filter → return all fairs (active + archived)

        if country:
            query = query.filter(FairModel.country.ilike(country.strip()))
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(or_(*[field.ilike(pattern) for field in SEARCH_FIELDS]))

        return query

    def list_by_organization(
        self,
        organization_id: UUID,
        *,
        status: FairStatus | None = None,
        include_archived: bool = False,
        country: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "start_date",
        sort_dir: str = "desc",
    ) -> FairListResult:
        page_params = normalize_page_params(page, page_size)
        query = self._filtered_query(
            organization_id,
            status=status,
            include_archived=include_archived,
            country=country,
            search=search,
        )

        total = query.count()
        sort_column = FAIR_SORT_FIELDS.get(sort_by, FairModel.start_date)
        nulls_last = sort_by == "start_date"
        order = build_order_clause(
            sort_column,
            sort_dir if sort_dir in ("asc", "desc") else "desc",
            tie_breaker=FairModel.id,
            nulls_last=nulls_last,
        )

        models = (
            query.order_by(*order)
            .offset(page_params.offset)
            .limit(page_params.page_size)
            .all()
        )

        meta = build_paginated_meta(page_params.page, page_params.page_size, total)
        return FairListResult(
            items=[model_to_entity(model) for model in models],
            page=meta.page,
            page_size=meta.page_size,
            total=meta.total,
            total_pages=meta.total_pages,
        )

    def list_visible(
        self,
        organization_id: UUID,
        *,
        status: FairStatus | None = None,
        include_archived: bool = False,
        country: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "start_date",
        sort_dir: str = "desc",
        default_date_order: bool = False,
        today: date | None = None,
    ) -> FairListResult:
        page_params = normalize_page_params(page, page_size)
        query = self._filtered_query(
            organization_id,
            status=status,
            include_archived=include_archived,
            country=country,
            search=search,
            include_system=True,
        )

        total = query.count()
        if default_date_order:
            order = _default_date_order(today if today is not None else date.today())
        else:
            sort_column = FAIR_SORT_FIELDS.get(sort_by, FairModel.start_date)
            nulls_last = sort_by == "start_date"
            order = build_order_clause(
                sort_column,
                sort_dir if sort_dir in ("asc", "desc") else "desc",
                tie_breaker=FairModel.id,
                nulls_last=nulls_last,
            )

        models = (
            query.order_by(*order)
            .offset(page_params.offset)
            .limit(page_params.page_size)
            .all()
        )

        meta = build_paginated_meta(page_params.page, page_params.page_size, total)
        return FairListResult(
            items=[model_to_entity(model) for model in models],
            page=meta.page,
            page_size=meta.page_size,
            total=meta.total,
            total_pages=meta.total_pages,
        )

    def list_linked_to_adapter(self, organization_id: UUID, adapter_key: str) -> list[Fair]:
        normalized_key = adapter_key.strip().lower()
        models = (
            self._session.query(FairModel)
            .filter(
                FairModel.organization_id == organization_id,
                FairModel.deleted_at.is_(None),
                FairModel.adapter_key == normalized_key,
            )
            .order_by(FairModel.name.asc())
            .all()
        )
        return [model_to_entity(model) for model in models]

    def unlink_adapter_key(self, organization_id: UUID, adapter_key: str, *, now: datetime) -> int:
        normalized_key = adapter_key.strip().lower()
        updated = (
            self._session.query(FairModel)
            .filter(
                FairModel.organization_id == organization_id,
                FairModel.deleted_at.is_(None),
                FairModel.adapter_key == normalized_key,
            )
            .update(
                {"adapter_key": None, "updated_at": now},
                synchronize_session=False,
            )
        )
        self._session.flush()
        return int(updated or 0)
