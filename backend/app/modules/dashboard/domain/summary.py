from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class DashboardOverviewCards:
    total_customers: int
    total_fairs: int
    open_todos: int
    today_follow_ups: int
    sent_mails: int
    failed_mails: int


@dataclass(frozen=True)
class DashboardTaskSummary:
    not_started: int
    in_follow_up: int
    closed: int
    overdue_follow_ups: int


@dataclass(frozen=True)
class DashboardRecentActivity:
    id: UUID
    customer_id: UUID
    customer_name: str
    activity_type: str
    note_summary: str | None
    activity_date: datetime


@dataclass(frozen=True)
class DashboardFairSummary:
    fair_id: UUID
    fair_name: str
    customer_count: int
    customers_with_activity: int
    customers_with_mail_sent: int
    failed_mail_count: int


@dataclass(frozen=True)
class DashboardMailStatusSummary:
    queued: int
    sending: int
    sent: int
    failed: int
    timeout: int


@dataclass(frozen=True)
class DashboardSummary:
    overview: DashboardOverviewCards
    task_summary: DashboardTaskSummary
    recent_activities: list[DashboardRecentActivity]
    fair_summaries: list[DashboardFairSummary]
    mail_status: DashboardMailStatusSummary
