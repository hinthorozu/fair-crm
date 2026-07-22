from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, case, distinct, func, or_
from sqlalchemy.orm import Session

from app.modules.activities.infrastructure.persistence.models import ActivityModel
from app.modules.customers.domain.value_objects import CustomerStatus
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.mail_send_operations.domain.value_objects import MailSendOperationStatus
from app.modules.mail_send_operations.domain.worker_constants import SENDING_TIMEOUT_ERROR_CODE
from app.modules.mail_send_operations.infrastructure.persistence.models import MailSendOperationModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
from app.modules.smtp.domain.smtp_timeout_errors import SMTP_CONNECT_TIMEOUT_CODE, SMTP_TIMEOUT_CODE
from app.modules.todos.domain.value_objects import TodoStatus
from app.modules.todos.domain.worklist_value_objects import StoredWorklistPrimaryStatus
from app.modules.todos.infrastructure.persistence.models import TodoModel, TodoWorklistStateModel
from app.modules.dashboard.domain.summary import (
    DashboardFairSummary,
    DashboardMailStatusSummary,
    DashboardOverviewCards,
    DashboardRecentActivity,
    DashboardSummary,
    DashboardTaskSummary,
)

MAIL_TIMEOUT_ERROR_CODES = frozenset(
    {
        SENDING_TIMEOUT_ERROR_CODE,
        SMTP_CONNECT_TIMEOUT_CODE,
        SMTP_TIMEOUT_CODE,
    }
)

OPEN_TODO_STATUSES = frozenset(
    {
        TodoStatus.TODO.value,
        TodoStatus.IN_PROGRESS.value,
    }
)

RECENT_ACTIVITY_LIMIT = 20
FAIR_SUMMARY_LIMIT = 50
UNKNOWN_CUSTOMER_NAME = "Bilinmeyen müşteri"


def _as_int(value: int | None) -> int:
    return int(value or 0)


class SqlAlchemyDashboardQueryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_summary(self, organization_id: UUID) -> DashboardSummary:
        now = datetime.now(tz=UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)

        return DashboardSummary(
            overview=self._overview_cards(organization_id, today_start, tomorrow_start),
            task_summary=self._task_summary(organization_id, today_start),
            recent_activities=self._recent_activities(organization_id),
            fair_summaries=self._fair_summaries(organization_id),
            mail_status=self._mail_status(organization_id),
        )

    def _overview_cards(
        self,
        organization_id: UUID,
        today_start: datetime,
        tomorrow_start: datetime,
    ) -> DashboardOverviewCards:
        total_customers = _as_int(
            self._session.query(func.count(CustomerModel.id))
            .filter(
                CustomerModel.organization_id == organization_id,
                CustomerModel.status != CustomerStatus.DELETED.value,
            )
            .scalar()
        )
        total_fairs = _as_int(
            self._session.query(func.count(FairModel.id))
            .filter(
                FairModel.organization_id == organization_id,
                FairModel.deleted_at.is_(None),
            )
            .scalar()
        )
        open_todos = _as_int(
            self._session.query(func.count(TodoModel.id))
            .filter(
                TodoModel.organization_id == organization_id,
                TodoModel.archived_at.is_(None),
                TodoModel.status.in_(tuple(OPEN_TODO_STATUSES)),
            )
            .scalar()
        )
        today_follow_ups = _as_int(
            self._session.query(func.count(TodoWorklistStateModel.id))
            .join(TodoModel, TodoWorklistStateModel.todo_id == TodoModel.id)
            .filter(
                TodoWorklistStateModel.organization_id == organization_id,
                TodoModel.archived_at.is_(None),
                TodoWorklistStateModel.follow_up_at.isnot(None),
                TodoWorklistStateModel.follow_up_at >= today_start,
                TodoWorklistStateModel.follow_up_at < tomorrow_start,
            )
            .scalar()
        )
        sent_mails = _as_int(
            self._session.query(func.count(MailSendOperationModel.id))
            .filter(
                MailSendOperationModel.organization_id == organization_id,
                MailSendOperationModel.status == MailSendOperationStatus.SENT.value,
            )
            .scalar()
        )
        failed_mails = _as_int(
            self._session.query(func.count(MailSendOperationModel.id))
            .filter(
                MailSendOperationModel.organization_id == organization_id,
                MailSendOperationModel.status == MailSendOperationStatus.FAILED.value,
            )
            .scalar()
        )
        return DashboardOverviewCards(
            total_customers=total_customers,
            total_fairs=total_fairs,
            open_todos=open_todos,
            today_follow_ups=today_follow_ups,
            sent_mails=sent_mails,
            failed_mails=failed_mails,
        )

    def _task_summary(self, organization_id: UUID, today_start: datetime) -> DashboardTaskSummary:
        active_todos = (
            self._session.query(TodoModel.id, TodoModel.source_fair_id)
            .filter(
                TodoModel.organization_id == organization_id,
                TodoModel.archived_at.is_(None),
                TodoModel.source_fair_id.isnot(None),
            )
            .all()
        )
        if not active_todos:
            return DashboardTaskSummary(
                not_started=0,
                in_follow_up=0,
                closed=0,
                overdue_follow_ups=0,
            )

        todo_ids = [todo_id for todo_id, _ in active_todos]
        fair_ids = {fair_id for _, fair_id in active_todos if fair_id is not None}

        status_counts = (
            self._session.query(
                TodoWorklistStateModel.primary_status,
                func.count(TodoWorklistStateModel.id),
            )
            .filter(
                TodoWorklistStateModel.organization_id == organization_id,
                TodoWorklistStateModel.todo_id.in_(todo_ids),
            )
            .group_by(TodoWorklistStateModel.primary_status)
            .all()
        )
        in_follow_up = 0
        closed = 0
        for status, count in status_counts:
            normalized_status = str(status or "")
            if normalized_status == StoredWorklistPrimaryStatus.IN_FOLLOW_UP.value:
                in_follow_up = _as_int(count)
            elif normalized_status == StoredWorklistPrimaryStatus.CLOSED.value:
                closed = _as_int(count)

        total_participations = _as_int(
            self._session.query(func.count(CustomerFairParticipationModel.id))
            .filter(
                CustomerFairParticipationModel.organization_id == organization_id,
                CustomerFairParticipationModel.fair_id.in_(fair_ids),
                CustomerFairParticipationModel.deleted_at.is_(None),
            )
            .scalar()
        )
        not_started = max(total_participations - in_follow_up - closed, 0)

        overdue_follow_ups = _as_int(
            self._session.query(func.count(TodoWorklistStateModel.id))
            .join(TodoModel, TodoWorklistStateModel.todo_id == TodoModel.id)
            .filter(
                TodoWorklistStateModel.organization_id == organization_id,
                TodoModel.archived_at.is_(None),
                TodoWorklistStateModel.follow_up_at.isnot(None),
                TodoWorklistStateModel.follow_up_at < today_start,
                TodoWorklistStateModel.primary_status == StoredWorklistPrimaryStatus.IN_FOLLOW_UP.value,
            )
            .scalar()
        )
        return DashboardTaskSummary(
            not_started=not_started,
            in_follow_up=in_follow_up,
            closed=closed,
            overdue_follow_ups=overdue_follow_ups,
        )

    def _recent_activities(self, organization_id: UUID) -> list[DashboardRecentActivity]:
        rows = (
            self._session.query(ActivityModel, CustomerModel.display_name)
            .outerjoin(
                CustomerModel,
                and_(
                    ActivityModel.customer_id == CustomerModel.id,
                    CustomerModel.organization_id == organization_id,
                ),
            )
            .filter(
                ActivityModel.organization_id == organization_id,
                ActivityModel.deleted_at.is_(None),
                ActivityModel.is_active.is_(True),
                or_(
                    CustomerModel.id.is_(None),
                    CustomerModel.status != CustomerStatus.DELETED.value,
                ),
            )
            .order_by(ActivityModel.activity_date.desc(), ActivityModel.id.desc())
            .limit(RECENT_ACTIVITY_LIMIT)
            .all()
        )
        items: list[DashboardRecentActivity] = []
        for activity, customer_name in rows:
            note = activity.description or activity.subject
            if note and len(note) > 200:
                note = note[:197] + "..."
            if customer_name:
                display_name = customer_name
            elif activity.customer_id is None:
                display_name = "—"
            else:
                display_name = UNKNOWN_CUSTOMER_NAME
            items.append(
                DashboardRecentActivity(
                    id=activity.id,
                    customer_id=activity.customer_id,
                    customer_name=display_name,
                    activity_type=activity.activity_type or "other",
                    note_summary=note,
                    activity_date=activity.activity_date,
                )
            )
        return items

    def _fair_summaries(self, organization_id: UUID) -> list[DashboardFairSummary]:
        fairs = (
            self._session.query(FairModel)
            .filter(
                FairModel.organization_id == organization_id,
                FairModel.deleted_at.is_(None),
            )
            .order_by(FairModel.name.asc())
            .limit(FAIR_SUMMARY_LIMIT)
            .all()
        )
        if not fairs:
            return []

        fair_ids = [fair.id for fair in fairs]

        customer_counts = dict(
            self._session.query(
                CustomerFairParticipationModel.fair_id,
                func.count(CustomerFairParticipationModel.id),
            )
            .filter(
                CustomerFairParticipationModel.organization_id == organization_id,
                CustomerFairParticipationModel.fair_id.in_(fair_ids),
                CustomerFairParticipationModel.deleted_at.is_(None),
            )
            .group_by(CustomerFairParticipationModel.fair_id)
            .all()
        )

        activity_customer_counts = dict(
            self._session.query(
                TodoModel.source_fair_id,
                func.count(distinct(TodoWorklistStateModel.customer_id)),
            )
            .join(TodoWorklistStateModel, TodoWorklistStateModel.todo_id == TodoModel.id)
            .filter(
                TodoModel.organization_id == organization_id,
                TodoModel.source_fair_id.in_(fair_ids),
                TodoWorklistStateModel.last_activity_at.isnot(None),
            )
            .group_by(TodoModel.source_fair_id)
            .all()
        )

        mail_sent_customer_counts = dict(
            self._session.query(
                MailSendOperationModel.fair_id,
                func.count(distinct(MailSendOperationModel.customer_id)),
            )
            .filter(
                MailSendOperationModel.organization_id == organization_id,
                MailSendOperationModel.fair_id.in_(fair_ids),
                MailSendOperationModel.status == MailSendOperationStatus.SENT.value,
                MailSendOperationModel.customer_id.isnot(None),
            )
            .group_by(MailSendOperationModel.fair_id)
            .all()
        )

        failed_mail_counts = dict(
            self._session.query(
                MailSendOperationModel.fair_id,
                func.count(MailSendOperationModel.id),
            )
            .filter(
                MailSendOperationModel.organization_id == organization_id,
                MailSendOperationModel.fair_id.in_(fair_ids),
                MailSendOperationModel.status == MailSendOperationStatus.FAILED.value,
            )
            .group_by(MailSendOperationModel.fair_id)
            .all()
        )

        return [
            DashboardFairSummary(
                fair_id=fair.id,
                fair_name=fair.name or "",
                customer_count=_as_int(customer_counts.get(fair.id)),
                customers_with_activity=_as_int(activity_customer_counts.get(fair.id)),
                customers_with_mail_sent=_as_int(mail_sent_customer_counts.get(fair.id)),
                failed_mail_count=_as_int(failed_mail_counts.get(fair.id)),
            )
            for fair in fairs
        ]

    def _mail_status(self, organization_id: UUID) -> DashboardMailStatusSummary:
        timeout_condition = and_(
            MailSendOperationModel.error_code.isnot(None),
            or_(
                MailSendOperationModel.error_code.in_(tuple(MAIL_TIMEOUT_ERROR_CODES)),
                MailSendOperationModel.error_code.ilike("%timeout%"),
            ),
        )
        rows = (
            self._session.query(
                MailSendOperationModel.status,
                func.count(MailSendOperationModel.id),
                func.sum(case((timeout_condition, 1), else_=0)),
            )
            .filter(MailSendOperationModel.organization_id == organization_id)
            .group_by(MailSendOperationModel.status)
            .all()
        )
        counts = {
            MailSendOperationStatus.QUEUED.value: 0,
            MailSendOperationStatus.SENDING.value: 0,
            MailSendOperationStatus.SENT.value: 0,
            MailSendOperationStatus.FAILED.value: 0,
        }
        timeout_total = 0
        for status, count, timeout_count in rows:
            if status in counts:
                counts[status] = _as_int(count)
            timeout_total += _as_int(timeout_count)
        return DashboardMailStatusSummary(
            queued=counts[MailSendOperationStatus.QUEUED.value],
            sending=counts[MailSendOperationStatus.SENDING.value],
            sent=counts[MailSendOperationStatus.SENT.value],
            failed=counts[MailSendOperationStatus.FAILED.value],
            timeout=timeout_total,
        )
