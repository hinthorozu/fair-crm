from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from app.modules.todos.domain.exceptions import (
    InvalidOutcomeCodeError,
    InvalidOutcomeNameError,
    InvalidOutcomePrimaryWorklistStatusError,
)
from app.modules.todos.domain.outcome_value_objects import OutcomePrimaryWorklistStatus


def _validate_code(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        raise InvalidOutcomeCodeError("code must not be empty")
    if trimmed != trimmed.lower():
        raise InvalidOutcomeCodeError("code must be lowercase ASCII slug")
    return trimmed


def _validate_name(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        raise InvalidOutcomeNameError("name must not be empty")
    return trimmed


def _validate_primary_worklist_status(value: str) -> str:
    try:
        return OutcomePrimaryWorklistStatus(value)
    except ValueError as exc:
        raise InvalidOutcomePrimaryWorklistStatusError(
            f"Invalid outcome primary worklist status: {value}"
        ) from exc


@dataclass
class TodoOutcomeDefinition:
    id: UUID
    organization_id: UUID
    name: str
    code: str
    description: Optional[str]
    is_active: bool
    sort_order: int
    primary_worklist_status: str
    requires_action: bool
    marks_data_problem: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        name: str,
        code: str,
        primary_worklist_status: str,
        now: datetime,
        description: Optional[str] = None,
        sort_order: int = 0,
        requires_action: bool = False,
        marks_data_problem: bool = False,
        is_active: bool = True,
    ) -> "TodoOutcomeDefinition":
        return cls(
            id=uuid4(),
            organization_id=organization_id,
            name=_validate_name(name),
            code=_validate_code(code),
            description=description.strip() if description else None,
            is_active=is_active,
            sort_order=sort_order,
            primary_worklist_status=_validate_primary_worklist_status(primary_worklist_status),
            requires_action=requires_action,
            marks_data_problem=marks_data_problem,
            created_at=now,
            updated_at=now,
        )

    def deactivate(self, *, now: datetime) -> None:
        self.is_active = False
        self.updated_at = now

    def reactivate(self, *, now: datetime) -> None:
        self.is_active = True
        self.updated_at = now

    def update_fields(
        self,
        *,
        now: datetime,
        name: Optional[str] = None,
        description: Optional[str] = None,
        set_description: bool = False,
        primary_worklist_status: Optional[str] = None,
        requires_action: Optional[bool] = None,
        marks_data_problem: Optional[bool] = None,
        sort_order: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> None:
        if name is not None:
            self.name = _validate_name(name)

        if set_description:
            self.description = description.strip() if description else None

        if primary_worklist_status is not None:
            self.primary_worklist_status = _validate_primary_worklist_status(
                primary_worklist_status
            )

        if requires_action is not None:
            self.requires_action = requires_action

        if marks_data_problem is not None:
            self.marks_data_problem = marks_data_problem

        if sort_order is not None:
            self.sort_order = sort_order

        if is_active is not None:
            self.is_active = is_active

        self.updated_at = now
