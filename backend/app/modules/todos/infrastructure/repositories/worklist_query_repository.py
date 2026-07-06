from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.core.pagination import build_order_clause, build_paginated_meta, normalize_page_params
from app.modules.contacts.infrastructure.persistence.models import ContactModel
from app.modules.customers.infrastructure.persistence.communication_query_helpers import (
    email_search_exists,
    phone_search_exists,
    primary_email_subquery,
    primary_phone_subquery,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
from app.modules.todos.domain.worklist_query import (
    TodoWorklistListResult,
    TodoWorklistProgress,
    TodoWorklistRow,
    resolve_added_after_completion,
    resolve_row_primary_status,
)
from app.modules.todos.domain.worklist_value_objects import StoredWorklistPrimaryStatus, WorklistFilter
from app.modules.todos.infrastructure.persistence.models import (
    TodoOutcomeDefinitionModel,
    TodoWorklistStateModel,
)

WORKLIST_SEARCH_FIELDS = (CustomerModel.display_name,)

WORKLIST_SORT_FIELDS = {
    "company_name": CustomerModel.display_name,
    "last_activity_at": TodoWorklistStateModel.last_activity_at,
    "follow_up_at": TodoWorklistStateModel.follow_up_at,
    "primary_status": case(
        (TodoWorklistStateModel.id.is_(None), 0),
        (TodoWorklistStateModel.primary_status == StoredWorklistPrimaryStatus.IN_FOLLOW_UP, 1),
        (TodoWorklistStateModel.primary_status == StoredWorklistPrimaryStatus.CLOSED, 2),
        else_=0,
    ),
}


def _contact_count_subquery(organization_id: UUID):
    return (
        select(func.count(ContactModel.id))
        .where(
            ContactModel.organization_id == organization_id,
            ContactModel.customer_id == CustomerModel.id,
            ContactModel.deleted_at.is_(None),
        )
        .correlate(CustomerModel)
        .scalar_subquery()
    )


class SqlAlchemyTodoWorklistQueryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _base_query(
        self,
        organization_id: UUID,
        todo_id: UUID,
        source_fair_id: UUID,
    ):
        primary_phone = primary_phone_subquery()
        primary_email = primary_email_subquery()
        contact_count = _contact_count_subquery(organization_id)
        return (
            self._session.query(
                CustomerFairParticipationModel,
                CustomerModel,
                TodoWorklistStateModel,
                TodoOutcomeDefinitionModel,
                primary_phone,
                primary_email,
                contact_count,
            )
            .join(
                CustomerModel,
                CustomerFairParticipationModel.customer_id == CustomerModel.id,
            )
            .outerjoin(
                TodoWorklistStateModel,
                and_(
                    TodoWorklistStateModel.organization_id == organization_id,
                    TodoWorklistStateModel.todo_id == todo_id,
                    TodoWorklistStateModel.customer_id == CustomerFairParticipationModel.customer_id,
                ),
            )
            .outerjoin(
                TodoOutcomeDefinitionModel,
                TodoWorklistStateModel.last_outcome_id == TodoOutcomeDefinitionModel.id,
            )
            .filter(
                CustomerFairParticipationModel.organization_id == organization_id,
                CustomerFairParticipationModel.fair_id == source_fair_id,
                CustomerFairParticipationModel.deleted_at.is_(None),
            )
        )

    def _apply_filter(self, query, worklist_filter: WorklistFilter):
        if worklist_filter == WorklistFilter.YAPILMADI:
            return query.filter(TodoWorklistStateModel.id.is_(None))
        if worklist_filter == WorklistFilter.TAKIPTE:
            return query.filter(
                TodoWorklistStateModel.primary_status == StoredWorklistPrimaryStatus.IN_FOLLOW_UP
            )
        if worklist_filter == WorklistFilter.KONU_KAPANDI:
            return query.filter(
                TodoWorklistStateModel.primary_status == StoredWorklistPrimaryStatus.CLOSED
            )
        return query

    def _apply_search(self, query, search: str | None):
        if not search:
            return query
        pattern = f"%{search.strip()}%"
        return query.filter(
            or_(
                *[field.ilike(pattern) for field in WORKLIST_SEARCH_FIELDS],
                phone_search_exists(pattern),
                email_search_exists(pattern),
            )
        )

    def _row_from_result(
        self,
        row,
        *,
        todo_completed_at: datetime | None,
    ) -> TodoWorklistRow:
        (
            participation,
            customer,
            state,
            outcome,
            phone_summary,
            email_summary,
            contact_count,
        ) = row
        stored_status = state.primary_status if state is not None else None
        return TodoWorklistRow(
            customer_id=customer.id,
            customer_name=customer.display_name,
            city=customer.city,
            country=customer.country,
            phone_summary=phone_summary,
            email_summary=email_summary,
            contact_count=int(contact_count or 0),
            participation_id=participation.id,
            primary_status=resolve_row_primary_status(stored_status),
            last_outcome_id=state.last_outcome_id if state is not None else None,
            last_outcome_name=outcome.name if outcome is not None else None,
            last_note_summary=state.last_note_summary if state is not None else None,
            last_activity_at=state.last_activity_at if state is not None else None,
            follow_up_at=state.follow_up_at if state is not None else None,
            action_required=state.action_required if state is not None else False,
            data_problem=state.data_problem if state is not None else False,
            added_after_completion=resolve_added_after_completion(
                participation_created_at=participation.created_at,
                todo_completed_at=todo_completed_at,
            ),
        )

    def list_for_todo(
        self,
        organization_id: UUID,
        todo_id: UUID,
        source_fair_id: UUID,
        *,
        todo_completed_at: datetime | None,
        worklist_filter: WorklistFilter,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "company_name",
        sort_dir: str = "asc",
    ) -> TodoWorklistListResult:
        page_params = normalize_page_params(page, page_size)
        query = self._base_query(organization_id, todo_id, source_fair_id)
        query = self._apply_filter(query, worklist_filter)
        query = self._apply_search(query, search)

        total = query.count()
        sort_column = WORKLIST_SORT_FIELDS.get(sort_by, CustomerModel.display_name)
        nulls_last = sort_by in {"last_activity_at", "follow_up_at"}
        order = build_order_clause(
            sort_column,
            sort_dir if sort_dir in ("asc", "desc") else "asc",
            tie_breaker=CustomerFairParticipationModel.id,
            nulls_last=nulls_last,
        )
        rows = query.order_by(*order).offset(page_params.offset).limit(page_params.page_size).all()
        items = [
            self._row_from_result(row, todo_completed_at=todo_completed_at) for row in rows
        ]
        meta = build_paginated_meta(page_params.page, page_params.page_size, total)
        return TodoWorklistListResult(
            items=items,
            page=meta.page,
            page_size=meta.page_size,
            total=meta.total,
            total_pages=meta.total_pages,
        )

    def progress_for_todo(
        self,
        organization_id: UUID,
        todo_id: UUID,
        source_fair_id: UUID,
    ) -> TodoWorklistProgress:
        participation_query = self._session.query(CustomerFairParticipationModel.id).filter(
            CustomerFairParticipationModel.organization_id == organization_id,
            CustomerFairParticipationModel.fair_id == source_fair_id,
            CustomerFairParticipationModel.deleted_at.is_(None),
        )
        total = participation_query.count()

        status_counts = (
            self._session.query(
                TodoWorklistStateModel.primary_status,
                func.count(TodoWorklistStateModel.id),
            )
            .filter(
                TodoWorklistStateModel.organization_id == organization_id,
                TodoWorklistStateModel.todo_id == todo_id,
            )
            .group_by(TodoWorklistStateModel.primary_status)
            .all()
        )
        in_follow_up = 0
        closed = 0
        for status, count in status_counts:
            if status == StoredWorklistPrimaryStatus.IN_FOLLOW_UP:
                in_follow_up = count
            elif status == StoredWorklistPrimaryStatus.CLOSED:
                closed = count
        not_started = total - in_follow_up - closed
        return TodoWorklistProgress(
            total=total,
            not_started=not_started,
            in_follow_up=in_follow_up,
            closed=closed,
        )

    def get_row_for_customer(
        self,
        organization_id: UUID,
        todo_id: UUID,
        source_fair_id: UUID,
        customer_id: UUID,
        *,
        todo_completed_at: datetime | None,
    ) -> TodoWorklistRow | None:
        query = self._base_query(organization_id, todo_id, source_fair_id).filter(
            CustomerFairParticipationModel.customer_id == customer_id,
        )
        row = query.one_or_none()
        if row is None:
            return None
        return self._row_from_result(row, todo_completed_at=todo_completed_at)
