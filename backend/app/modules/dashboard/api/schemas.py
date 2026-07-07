from datetime import datetime
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class DashboardOverviewCardsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=True)

    total_customers: int = Field(serialization_alias="totalCustomers")
    total_fairs: int = Field(serialization_alias="totalFairs")
    open_todos: int = Field(serialization_alias="openTodos")
    today_follow_ups: int = Field(serialization_alias="todayFollowUps")
    sent_mails: int = Field(serialization_alias="sentMails")
    failed_mails: int = Field(serialization_alias="failedMails")


class DashboardTaskSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=True)

    not_started: int = Field(serialization_alias="notStarted")
    in_follow_up: int = Field(serialization_alias="inFollowUp")
    closed: int
    overdue_follow_ups: int = Field(serialization_alias="overdueFollowUps")


class DashboardRecentActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=True)

    id: UUID
    customer_id: UUID = Field(serialization_alias="customerId")
    customer_name: str = Field(serialization_alias="customerName")
    activity_type: str = Field(serialization_alias="activityType")
    note_summary: str | None = Field(serialization_alias="noteSummary")
    activity_date: datetime = Field(serialization_alias="activityDate")


class DashboardFairSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=True)

    fair_id: UUID = Field(serialization_alias="fairId")
    fair_name: str = Field(serialization_alias="fairName")
    customer_count: int = Field(serialization_alias="customerCount")
    customers_with_activity: int = Field(serialization_alias="customersWithActivity")
    customers_with_mail_sent: int = Field(serialization_alias="customersWithMailSent")
    failed_mail_count: int = Field(serialization_alias="failedMailCount")


class DashboardMailStatusSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    queued: int
    sending: int
    sent: int
    failed: int
    timeout: int


class DashboardSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=True)

    overview: DashboardOverviewCardsResponse
    task_summary: DashboardTaskSummaryResponse = Field(
        validation_alias=AliasChoices("task_summary", "taskSummary"),
        serialization_alias="taskSummary",
    )
    recent_activities: list[DashboardRecentActivityResponse] = Field(
        validation_alias=AliasChoices("recent_activities", "recentActivities"),
        serialization_alias="recentActivities",
    )
    fair_summaries: list[DashboardFairSummaryResponse] = Field(
        validation_alias=AliasChoices("fair_summaries", "fairSummaries"),
        serialization_alias="fairSummaries",
    )
    mail_status: DashboardMailStatusSummaryResponse = Field(
        validation_alias=AliasChoices("mail_status", "mailStatus"),
        serialization_alias="mailStatus",
    )
