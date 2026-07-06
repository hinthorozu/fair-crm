from app.modules.todos.application.worklist_commands import (
    FollowUpListResultDto,
    FollowUpRowResult,
    TodoWorklistListResultDto,
    TodoWorklistProgressResult,
    TodoWorklistRowResult,
)
from app.modules.todos.domain.follow_up_query import FollowUpListResult, FollowUpRow
from app.modules.todos.domain.worklist_query import TodoWorklistListResult, TodoWorklistProgress, TodoWorklistRow


def worklist_row_to_result(row: TodoWorklistRow) -> TodoWorklistRowResult:
    return TodoWorklistRowResult(
        customer_id=row.customer_id,
        customer_name=row.customer_name,
        city=row.city,
        country=row.country,
        phone_summary=row.phone_summary,
        email_summary=row.email_summary,
        contact_count=row.contact_count,
        participation_id=row.participation_id,
        primary_status=row.primary_status,
        last_outcome_id=row.last_outcome_id,
        last_outcome_name=row.last_outcome_name,
        last_note_summary=row.last_note_summary,
        last_activity_at=row.last_activity_at,
        follow_up_at=row.follow_up_at,
        action_required=row.action_required,
        data_problem=row.data_problem,
        added_after_completion=row.added_after_completion,
    )


def worklist_list_to_dto(result: TodoWorklistListResult) -> TodoWorklistListResultDto:
    return TodoWorklistListResultDto(
        items=[worklist_row_to_result(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )


def worklist_progress_to_result(progress: TodoWorklistProgress) -> TodoWorklistProgressResult:
    return TodoWorklistProgressResult(
        total=progress.total,
        not_started=progress.not_started,
        in_follow_up=progress.in_follow_up,
        closed=progress.closed,
    )


def follow_up_row_to_result(row: FollowUpRow) -> FollowUpRowResult:
    return FollowUpRowResult(
        todo_id=row.todo_id,
        todo_title=row.todo_title,
        customer_id=row.customer_id,
        customer_name=row.customer_name,
        city=row.city,
        country=row.country,
        phone_summary=row.phone_summary,
        email_summary=row.email_summary,
        contact_count=row.contact_count,
        participation_id=row.participation_id,
        primary_status=row.primary_status,
        last_outcome_id=row.last_outcome_id,
        last_outcome_name=row.last_outcome_name,
        last_note_summary=row.last_note_summary,
        last_activity_at=row.last_activity_at,
        follow_up_at=row.follow_up_at,
        action_required=row.action_required,
        data_problem=row.data_problem,
        added_after_completion=row.added_after_completion,
    )


def follow_up_list_to_dto(result: FollowUpListResult) -> FollowUpListResultDto:
    return FollowUpListResultDto(
        items=[follow_up_row_to_result(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )
