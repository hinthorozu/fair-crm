from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.core.pagination import normalize_page_params
from app.modules.customers.domain.ports import CustomerRepository
from app.modules.fairs.domain.ports import FairRepository
from app.modules.mail_send_operations.application.commands import ListMailSendOperationsQuery
from app.modules.mail_send_operations.application.display_labels import source_type_label, status_label
from app.modules.mail_send_operations.domain.entities import MailSendOperationRecord
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    MailSendOperationListPageResult,
    SqlAlchemyMailSendOperationRepository,
)
from app.modules.mail_templates.domain.ports import MailTemplateRepository
from app.modules.smtp.domain.ports import SmtpAccountRepository

PERMISSION_READ = "fair_crm.smtp.read"


@dataclass(frozen=True)
class MailSendOperationListItem:
    id: UUID
    created_at: datetime
    source_type: str
    source_type_label: str
    fair_id: UUID | None
    fair_name: str | None
    customer_id: UUID | None
    customer_name: str | None
    recipient_email: str
    recipient_name: str | None
    smtp_account_id: UUID | None
    smtp_account_name: str | None
    template_id: UUID | None
    template_name: str | None
    subject: str
    status: str
    status_label: str
    error_code: str | None
    error_message: str | None
    operation_logs: list
    retry_count: int
    priority: int
    sent_at: datetime | None
    failed_at: datetime | None
    cancelled_at: datetime | None


@dataclass(frozen=True)
class ListMailSendOperationsResult:
    items: list[MailSendOperationListItem]
    page: int
    page_size: int
    total: int
    total_pages: int


class ListMailSendOperationsUseCase:
    def __init__(
        self,
        repository: SqlAlchemyMailSendOperationRepository,
        smtp_repository: SmtpAccountRepository,
        template_repository: MailTemplateRepository,
        fair_repository: FairRepository,
        customer_repository: CustomerRepository,
    ) -> None:
        self._repository = repository
        self._smtp_repository = smtp_repository
        self._template_repository = template_repository
        self._fair_repository = fair_repository
        self._customer_repository = customer_repository

    def execute(self, query: ListMailSendOperationsQuery) -> ListMailSendOperationsResult:
        page_params = normalize_page_params(query.page, query.page_size)
        page_result = self._repository.list_paginated(
            query.organization_id,
            search=query.search,
            status=query.status,
            source_type=query.source_type,
            smtp_account_id=query.smtp_account_id,
            fair_id=query.fair_id,
            date_from=query.date_from,
            date_to=query.date_to,
            page=page_params.page,
            page_size=page_params.page_size,
        )
        return self._to_result(query.organization_id, page_result)

    def _to_result(
        self,
        organization_id: UUID,
        page_result: MailSendOperationListPageResult,
    ) -> ListMailSendOperationsResult:
        smtp_names: dict[UUID, str] = {}
        template_names: dict[UUID, str] = {}
        fair_names: dict[UUID, str] = {}
        customer_names: dict[UUID, str] = {}

        items = [
            self._to_list_item(
                organization_id,
                record,
                smtp_names,
                template_names,
                fair_names,
                customer_names,
            )
            for record in page_result.items
        ]
        return ListMailSendOperationsResult(
            items=items,
            page=page_result.page,
            page_size=page_result.page_size,
            total=page_result.total,
            total_pages=page_result.total_pages,
        )

    def _to_list_item(
        self,
        organization_id: UUID,
        record: MailSendOperationRecord,
        smtp_names: dict[UUID, str],
        template_names: dict[UUID, str],
        fair_names: dict[UUID, str],
        customer_names: dict[UUID, str],
    ) -> MailSendOperationListItem:
        return build_mail_send_operation_list_item(
            organization_id,
            record,
            smtp_repository=self._smtp_repository,
            template_repository=self._template_repository,
            fair_repository=self._fair_repository,
            customer_repository=self._customer_repository,
            smtp_names=smtp_names,
            template_names=template_names,
            fair_names=fair_names,
            customer_names=customer_names,
        )


def build_mail_send_operation_list_item(
    organization_id: UUID,
    record: MailSendOperationRecord,
    *,
    smtp_repository: SmtpAccountRepository,
    template_repository: MailTemplateRepository,
    fair_repository: FairRepository,
    customer_repository: CustomerRepository,
    smtp_names: dict[UUID, str] | None = None,
    template_names: dict[UUID, str] | None = None,
    fair_names: dict[UUID, str] | None = None,
    customer_names: dict[UUID, str] | None = None,
) -> MailSendOperationListItem:
    smtp_cache = smtp_names if smtp_names is not None else {}
    template_cache = template_names if template_names is not None else {}
    fair_cache = fair_names if fair_names is not None else {}
    customer_cache = customer_names if customer_names is not None else {}

    smtp_account_name = None
    if record.smtp_account_id is not None:
        smtp_account_name = smtp_cache.get(record.smtp_account_id)
        if smtp_account_name is None:
            account = smtp_repository.get_by_id(organization_id, record.smtp_account_id)
            smtp_account_name = account.name if account is not None else None
            if smtp_account_name is not None:
                smtp_cache[record.smtp_account_id] = smtp_account_name

    template_name = None
    if record.template_id is not None:
        template_name = template_cache.get(record.template_id)
        if template_name is None:
            template = template_repository.get_by_id(organization_id, record.template_id)
            template_name = template.name if template is not None else None
            if template_name is not None:
                template_cache[record.template_id] = template_name

    fair_name = None
    if record.fair_id is not None:
        fair_name = fair_cache.get(record.fair_id)
        if fair_name is None:
            fair = fair_repository.get_by_id(organization_id, record.fair_id)
            fair_name = fair.name if fair is not None else None
            if fair_name is not None:
                fair_cache[record.fair_id] = fair_name

    customer_name = record.recipient_name
    if record.customer_id is not None:
        customer_name = customer_cache.get(record.customer_id)
        if customer_name is None:
            customer = customer_repository.get_by_id(organization_id, record.customer_id)
            customer_name = customer.display_name if customer is not None else record.recipient_name
            if customer_name is not None:
                customer_cache[record.customer_id] = customer_name

    return MailSendOperationListItem(
        id=record.id,
        created_at=record.created_at,
        source_type=record.source_type,
        source_type_label=source_type_label(record.source_type),
        fair_id=record.fair_id,
        fair_name=fair_name,
        customer_id=record.customer_id,
        customer_name=customer_name,
        recipient_email=record.recipient_email,
        recipient_name=record.recipient_name,
        smtp_account_id=record.smtp_account_id,
        smtp_account_name=smtp_account_name,
        template_id=record.template_id,
        template_name=template_name,
        subject=record.subject,
        status=record.status,
        status_label=status_label(record.status),
        error_code=record.error_code,
        error_message=record.error_message,
        operation_logs=list(record.operation_logs or []),
        retry_count=record.retry_count,
        priority=record.priority,
        sent_at=record.sent_at,
        failed_at=record.failed_at,
        cancelled_at=record.cancelled_at,
    )
