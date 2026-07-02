from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.core.pagination import build_order_clause, build_paginated_meta, normalize_page_params
from app.modules.fairs.domain.entities import Fair
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

    def update(self, fair: Fair) -> Fair:
        model = (
            self._session.query(FairModel)
            .filter(
                FairModel.organization_id == fair.organization_id,
                FairModel.id == fair.id,
            )
            .one()
        )
        update_model_from_entity(model, fair)
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
    ) -> Query:
        query = self._session.query(FairModel).filter(
            FairModel.organization_id == organization_id,
        )

        if status == FairStatus.ARCHIVED:
            query = query.filter(FairModel.deleted_at.isnot(None))
        elif status is not None:
            query = query.filter(FairModel.deleted_at.is_(None))
            query = query.filter(FairModel.status == status.value)
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
