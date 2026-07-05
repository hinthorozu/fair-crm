from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.core.pagination import build_paginated_meta, normalize_page_params

from app.modules.mail_send_operations.domain.entities import MailSendOperationRecord
from app.modules.mail_send_operations.domain.exceptions import (
    InvalidMailSendOperationTransitionError,
    MailSendOperationNotFoundError,
    MissingOrganizationIdError,
)
from app.modules.mail_send_operations.domain.value_objects import (
    MailSendOperationStatus,
    MailSendSourceType,
    priority_for_source,
)
from app.modules.mail_send_operations.infrastructure.persistence.models import MailSendOperationModel


@dataclass(frozen=True)
class CreateMailSendOperationParams:
    organization_id: UUID
    source_type: MailSendSourceType | str
    recipient_email: str
    subject: str
    body_text: str | None = None
    body_html: str | None = None
    recipient_name: str | None = None
    smtp_account_id: UUID | None = None
    template_id: UUID | None = None
    fair_id: UUID | None = None
    customer_id: UUID | None = None
    batch_id: UUID | None = None
    metadata_json: dict[str, Any] | None = None
    max_retry_count: int = 3
    scheduled_at: datetime | None = None


@dataclass(frozen=True)
class MailSendOperationListPageResult:
    items: list[MailSendOperationRecord]
    page: int
    page_size: int
    total: int
    total_pages: int


class SqlAlchemyMailSendOperationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, params: CreateMailSendOperationParams) -> MailSendOperationRecord:
        if params.organization_id is None:
            raise MissingOrganizationIdError("organization_id is required")

        now = datetime.now(timezone.utc)
        priority = priority_for_source(params.source_type)
        model = MailSendOperationModel(
            id=uuid4(),
            organization_id=params.organization_id,
            source_type=str(params.source_type),
            status=MailSendOperationStatus.QUEUED,
            priority=priority,
            recipient_email=params.recipient_email.strip(),
            recipient_name=params.recipient_name,
            subject=params.subject.strip(),
            body_html=params.body_html,
            body_text=params.body_text,
            smtp_account_id=params.smtp_account_id,
            template_id=params.template_id,
            fair_id=params.fair_id,
            customer_id=params.customer_id,
            batch_id=params.batch_id,
            retry_count=0,
            max_retry_count=params.max_retry_count,
            error_code=None,
            error_message=None,
            operation_logs=[],
            metadata_json=params.metadata_json,
            scheduled_at=params.scheduled_at,
            queued_at=now,
            sending_started_at=None,
            sent_at=None,
            failed_at=None,
            cancelled_at=None,
            created_at=now,
            updated_at=now,
        )
        self._session.add(model)
        self._session.flush()
        return self._to_record(model)

    def create_immediate_failure(
        self,
        params: CreateMailSendOperationParams,
        *,
        error_code: str | None,
        error_message: str,
    ) -> MailSendOperationRecord:
        if params.organization_id is None:
            raise MissingOrganizationIdError("organization_id is required")

        now = datetime.now(timezone.utc)
        priority = priority_for_source(params.source_type)
        model = MailSendOperationModel(
            id=uuid4(),
            organization_id=params.organization_id,
            source_type=str(params.source_type),
            status=MailSendOperationStatus.FAILED,
            priority=priority,
            recipient_email=params.recipient_email.strip(),
            recipient_name=params.recipient_name,
            subject=params.subject.strip(),
            body_html=params.body_html,
            body_text=params.body_text,
            smtp_account_id=params.smtp_account_id,
            template_id=params.template_id,
            fair_id=params.fair_id,
            customer_id=params.customer_id,
            batch_id=params.batch_id,
            retry_count=0,
            max_retry_count=params.max_retry_count,
            error_code=error_code,
            error_message=error_message,
            operation_logs=[
                {
                    "time": now.isoformat().replace("+00:00", "Z"),
                    "event": "failed",
                    "message": error_message,
                }
            ],
            metadata_json=params.metadata_json,
            scheduled_at=params.scheduled_at,
            queued_at=None,
            sending_started_at=None,
            sent_at=None,
            failed_at=now,
            cancelled_at=None,
            created_at=now,
            updated_at=now,
        )
        self._session.add(model)
        self._session.flush()
        return self._to_record(model)

    def get_by_id(self, organization_id: UUID, operation_id: UUID) -> MailSendOperationRecord | None:
        model = (
            self._session.query(MailSendOperationModel)
            .filter(
                MailSendOperationModel.organization_id == organization_id,
                MailSendOperationModel.id == operation_id,
            )
            .one_or_none()
        )
        return self._to_record(model) if model else None

    def list_by_organization(
        self,
        organization_id: UUID,
        *,
        status: str | None = None,
        source_type: str | None = None,
        limit: int = 100,
    ) -> list[MailSendOperationRecord]:
        if organization_id is None:
            raise MissingOrganizationIdError("organization_id is required")

        query = self._session.query(MailSendOperationModel).filter(
            MailSendOperationModel.organization_id == organization_id,
        )
        if status:
            query = query.filter(MailSendOperationModel.status == status)
        if source_type:
            query = query.filter(MailSendOperationModel.source_type == source_type)
        models = (
            query.order_by(
                MailSendOperationModel.priority.asc(),
                MailSendOperationModel.created_at.asc(),
            )
            .limit(limit)
            .all()
        )
        return [self._to_record(model) for model in models]

    def list_paginated(
        self,
        organization_id: UUID,
        *,
        search: str | None = None,
        status: str | None = None,
        source_type: str | None = None,
        smtp_account_id: UUID | None = None,
        fair_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> MailSendOperationListPageResult:
        if organization_id is None:
            raise MissingOrganizationIdError("organization_id is required")

        page_params = normalize_page_params(page, page_size)
        query = self._session.query(MailSendOperationModel).filter(
            MailSendOperationModel.organization_id == organization_id,
        )

        if status:
            query = query.filter(MailSendOperationModel.status == status)
        if source_type:
            query = query.filter(MailSendOperationModel.source_type == source_type)
        if smtp_account_id is not None:
            query = query.filter(MailSendOperationModel.smtp_account_id == smtp_account_id)
        if fair_id is not None:
            query = query.filter(MailSendOperationModel.fair_id == fair_id)
        if date_from is not None:
            query = query.filter(MailSendOperationModel.created_at >= date_from)
        if date_to is not None:
            query = query.filter(MailSendOperationModel.created_at <= date_to)
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    MailSendOperationModel.recipient_email.ilike(pattern),
                    MailSendOperationModel.recipient_name.ilike(pattern),
                    MailSendOperationModel.subject.ilike(pattern),
                    MailSendOperationModel.error_message.ilike(pattern),
                )
            )

        total = query.count()
        models = (
            query.order_by(desc(MailSendOperationModel.created_at), desc(MailSendOperationModel.id))
            .offset(page_params.offset)
            .limit(page_params.page_size)
            .all()
        )
        meta = build_paginated_meta(page_params.page, page_params.page_size, total)
        return MailSendOperationListPageResult(
            items=[self._to_record(model) for model in models],
            page=meta.page,
            page_size=meta.page_size,
            total=meta.total,
            total_pages=meta.total_pages,
        )

    def _get_model(self, organization_id: UUID, operation_id: UUID) -> MailSendOperationModel:
        model = (
            self._session.query(MailSendOperationModel)
            .filter(
                MailSendOperationModel.organization_id == organization_id,
                MailSendOperationModel.id == operation_id,
            )
            .one_or_none()
        )
        if model is None:
            raise MailSendOperationNotFoundError("Mail send operation not found")
        return model

    def prepare_for_retry(self, organization_id: UUID, operation_id: UUID) -> MailSendOperationRecord:
        now = datetime.now(timezone.utc)
        model = self._get_model(organization_id, operation_id)
        if model.status != MailSendOperationStatus.FAILED:
            raise InvalidMailSendOperationTransitionError(
                "Only failed mail send operations can be retried",
            )
        model.retry_count += 1
        model.status = MailSendOperationStatus.QUEUED
        model.error_code = None
        model.error_message = None
        model.queued_at = now
        model.sending_started_at = None
        model.sent_at = None
        model.failed_at = None
        model.cancelled_at = None
        model.updated_at = now
        self._session.flush()
        return self._to_record(model)

    def mark_sending(self, organization_id: UUID, operation_id: UUID) -> MailSendOperationRecord:
        now = datetime.now(timezone.utc)
        model = self._get_model(organization_id, operation_id)
        model.status = MailSendOperationStatus.SENDING
        model.sending_started_at = now
        model.updated_at = now
        self._session.flush()
        return self._to_record(model)

    def mark_sent(self, organization_id: UUID, operation_id: UUID) -> MailSendOperationRecord:
        now = datetime.now(timezone.utc)
        model = self._get_model(organization_id, operation_id)
        model.status = MailSendOperationStatus.SENT
        model.sent_at = now
        model.error_code = None
        model.error_message = None
        model.updated_at = now
        self._session.flush()
        return self._to_record(model)

    def update_rendered_content(
        self,
        organization_id: UUID,
        operation_id: UUID,
        *,
        subject: str | None = None,
        body_html: str | None = None,
        body_text: str | None = None,
    ) -> MailSendOperationRecord:
        now = datetime.now(timezone.utc)
        model = self._get_model(organization_id, operation_id)
        if subject is not None:
            model.subject = subject.strip()
        if body_html is not None:
            model.body_html = body_html
        if body_text is not None:
            model.body_text = body_text
        model.updated_at = now
        self._session.flush()
        return self._to_record(model)

    def mark_failed(
        self,
        organization_id: UUID,
        operation_id: UUID,
        *,
        error_code: str | None,
        error_message: str | None,
    ) -> MailSendOperationRecord:
        now = datetime.now(timezone.utc)
        model = self._get_model(organization_id, operation_id)
        model.status = MailSendOperationStatus.FAILED
        model.failed_at = now
        model.error_code = error_code
        model.error_message = error_message
        model.updated_at = now
        self._session.flush()
        return self._to_record(model)

    def mark_cancelled(
        self,
        organization_id: UUID,
        operation_id: UUID,
        *,
        error_message: str | None = None,
    ) -> MailSendOperationRecord:
        now = datetime.now(timezone.utc)
        model = self._get_model(organization_id, operation_id)
        model.status = MailSendOperationStatus.CANCELLED
        model.cancelled_at = now
        if error_message:
            model.error_message = error_message
        model.updated_at = now
        self._session.flush()
        return self._to_record(model)

    def append_operation_log(
        self,
        organization_id: UUID,
        operation_id: UUID,
        *,
        event: str,
        message: str,
        at: datetime | None = None,
    ) -> MailSendOperationRecord:
        model = self._get_model(organization_id, operation_id)
        timestamp = at or datetime.now(timezone.utc)
        logs = list(model.operation_logs or [])
        logs.append(
            {
                "time": timestamp.isoformat().replace("+00:00", "Z"),
                "event": event,
                "message": message,
            }
        )
        model.operation_logs = logs
        model.updated_at = timestamp
        self._session.flush()
        return self._to_record(model)

    @staticmethod
    def _to_record(model: MailSendOperationModel) -> MailSendOperationRecord:
        return MailSendOperationRecord(
            id=model.id,
            organization_id=model.organization_id,
            source_type=model.source_type,
            status=model.status,
            priority=model.priority,
            recipient_email=model.recipient_email,
            recipient_name=model.recipient_name,
            subject=model.subject,
            body_html=model.body_html,
            body_text=model.body_text,
            smtp_account_id=model.smtp_account_id,
            template_id=model.template_id,
            fair_id=model.fair_id,
            customer_id=model.customer_id,
            batch_id=model.batch_id,
            retry_count=model.retry_count,
            max_retry_count=model.max_retry_count,
            error_code=model.error_code,
            error_message=model.error_message,
            operation_logs=list(model.operation_logs or []),
            metadata_json=model.metadata_json,
            scheduled_at=model.scheduled_at,
            queued_at=model.queued_at,
            sending_started_at=model.sending_started_at,
            sent_at=model.sent_at,
            failed_at=model.failed_at,
            cancelled_at=model.cancelled_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
