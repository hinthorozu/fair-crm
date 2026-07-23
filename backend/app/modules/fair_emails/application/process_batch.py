from __future__ import annotations

import logging
from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.fair_emails.application.commands import ProcessBatchCommand
from app.modules.fair_emails.application.fair_bulk_email_activity import (
    FairBulkEmailActivityContext,
    FairBulkEmailActivityWriter,
)
from app.modules.fair_emails.application.fair_bulk_mail_operation_sync import FairBulkEmailMailOperationSync
from app.modules.fair_emails.application.recipient_resolution import build_render_variables
from app.modules.fair_emails.infrastructure.recipient_loader import FairBulkEmailRecipientLoader
from app.modules.fair_emails.infrastructure.persistence.models import FairEmailOutboxModel
from app.modules.fair_emails.infrastructure.repositories.fair_email_batch_repository import (
    FairEmailBatchRecord,
    SqlAlchemyFairEmailBatchRepository,
)
from app.modules.mail_templates.domain.exceptions import MailTemplateRenderError
from app.modules.mail_templates.infrastructure.repositories.mail_template_repository import (
    SqlAlchemyMailTemplateRepository,
)
from app.modules.mail_templates.infrastructure.template_renderer import JinjaMailTemplateRenderer
from app.modules.smtp.domain.entities import SmtpAccount
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from app.modules.smtp.infrastructure.repositories.smtp_account_repository import SqlAlchemySmtpAccountRepository
from app.modules.smtp.infrastructure.smtp_mailer import send_smtp_message

logger = logging.getLogger(__name__)

INACTIVE_SMTP_MESSAGE = "Seçilen SMTP hesabı pasif durumda."
MISSING_SMTP_MESSAGE = "Bu kuruluş için varsayılan SMTP hesabı bulunamadı."
MISSING_TEMPLATE_MESSAGE = "Mail şablonu bulunamadı."
PROCESSOR_ERROR_MESSAGE = "Toplu mail işleme sırasında beklenmeyen bir hata oluştu."


class ProcessFairEmailBatchUseCase:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._batch_repository = SqlAlchemyFairEmailBatchRepository(session)
        self._template_repository = SqlAlchemyMailTemplateRepository(session)
        self._smtp_repository = SqlAlchemySmtpAccountRepository(session)
        self._recipient_loader = FairBulkEmailRecipientLoader(session)
        self._renderer = JinjaMailTemplateRenderer()
        self._activity_writer = FairBulkEmailActivityWriter(session)
        self._mail_operation_sync = FairBulkEmailMailOperationSync(session)

    def execute(self, command: ProcessBatchCommand) -> None:
        logger.info(
            "fair_email_batch_start batch_id=%s organization_id=%s",
            command.batch_id,
            command.organization_id,
        )
        try:
            self._process(command)
        except Exception:
            logger.exception(
                "fair_email_batch_failed batch_id=%s organization_id=%s",
                command.batch_id,
                command.organization_id,
            )
            self._fail_unprocessed_batch(
                command.organization_id,
                command.batch_id,
                PROCESSOR_ERROR_MESSAGE,
            )
            self._session.commit()
            raise

    def _process(self, command: ProcessBatchCommand) -> None:
        batch = self._batch_repository.get_batch(command.organization_id, command.batch_id)
        if batch is None:
            logger.warning(
                "fair_email_batch_missing batch_id=%s organization_id=%s",
                command.batch_id,
                command.organization_id,
            )
            return

        template = self._template_repository.get_by_id(command.organization_id, batch.template_id)
        if template is None or template.deleted_at is not None:
            self._fail_entire_batch(
                command.organization_id,
                batch,
                MISSING_TEMPLATE_MESSAGE,
                fair_name=self._load_fair_name(command.organization_id, batch.fair_id),
                template_name="",
                default_subject=batch.subject_override or "",
            )
            self._session.commit()
            logger.warning(
                "fair_email_batch_template_missing batch_id=%s template_id=%s",
                batch.id,
                batch.template_id,
            )
            return

        account, account_error = self._resolve_smtp_account(command.organization_id, batch)
        batch_fair_name = self._load_fair_name(command.organization_id, batch.fair_id)
        if account is None:
            self._fail_entire_batch(
                command.organization_id,
                batch,
                account_error or MISSING_SMTP_MESSAGE,
                fair_name=batch_fair_name,
                template_name=template.name,
                default_subject=batch.subject_override or template.subject,
            )
            self._session.commit()
            logger.warning(
                "fair_email_batch_smtp_unavailable batch_id=%s error=%s",
                batch.id,
                account_error,
            )
            return

        self._batch_repository.mark_batch_processing(batch.id)
        default_subject = batch.subject_override or template.subject
        self._mail_operation_sync.ensure_operations_for_batch(
            organization_id=command.organization_id,
            batch=batch,
            default_subject=default_subject,
        )
        self._session.commit()
        logger.info("fair_email_batch_processing batch_id=%s total_count=%s", batch.id, batch.total_count)

        sent_count = 0
        failed_count = 0

        for outbox in self._batch_repository.list_pending_outbox(batch.id):
            fair_name = (getattr(outbox, "fair_name", None) or "").strip() or batch_fair_name
            self._batch_repository.mark_outbox_sending(outbox.id)
            self._mail_operation_sync.sync_outbox_sending(command.organization_id, outbox)
            self._session.commit()

            try:
                variables = self._build_variables(command.organization_id, fair_name, outbox)
                rendered_subject = self._renderer.render(template.subject, variables)
                rendered_body_html = (
                    self._renderer.render(template.body_html, variables) if template.body_html else None
                )
                rendered_body_text = (
                    self._renderer.render(template.body_text, variables) if template.body_text else None
                )
            except MailTemplateRenderError:
                failure_message = "Mail şablonu render edilemedi."
                self._batch_repository.update_outbox_failed(
                    outbox.id,
                    message=failure_message,
                )
                self._mail_operation_sync.sync_outbox_failed(
                    command.organization_id,
                    outbox,
                    error_code="template_render_error",
                    error_message=failure_message,
                )
                failed_count += 1
                self._session.commit()
                self._record_terminal_outbox_activity(
                    organization_id=command.organization_id,
                    batch=batch,
                    outbox_id=outbox.id,
                    fair_name=fair_name,
                    template_name=template.name,
                    subject=batch.subject_override or template.subject,
                    error_message=failure_message,
                )
                continue

            final_subject = batch.subject_override or rendered_subject
            body_text = rendered_body_text or final_subject
            try:
                send_smtp_message(
                    account,
                    recipient=outbox.email,
                    subject=final_subject,
                    body=body_text,
                    body_html=rendered_body_html,
                )
            except SmtpMailDeliveryError as exc:
                message = exc.args[0] if exc.args else "SMTP gönderimi başarısız oldu."
                self._batch_repository.update_outbox_failed(outbox.id, message=message)
                self._mail_operation_sync.sync_outbox_failed(
                    command.organization_id,
                    outbox,
                    error_code=exc.error_type,
                    error_message=message,
                )
                failed_count += 1
                self._session.commit()
                self._record_terminal_outbox_activity(
                    organization_id=command.organization_id,
                    batch=batch,
                    outbox_id=outbox.id,
                    fair_name=fair_name,
                    template_name=template.name,
                    subject=final_subject,
                    error_message=message,
                )
                logger.warning(
                    "fair_email_outbox_failed batch_id=%s outbox_id=%s email=%s error=%s",
                    batch.id,
                    outbox.id,
                    outbox.email,
                    message,
                )
                continue
            except Exception as exc:
                message = str(exc).strip() or PROCESSOR_ERROR_MESSAGE
                self._batch_repository.update_outbox_failed(outbox.id, message=message)
                self._mail_operation_sync.sync_outbox_failed(
                    command.organization_id,
                    outbox,
                    error_code=type(exc).__name__,
                    error_message=message,
                )
                failed_count += 1
                self._session.commit()
                self._record_terminal_outbox_activity(
                    organization_id=command.organization_id,
                    batch=batch,
                    outbox_id=outbox.id,
                    fair_name=fair_name,
                    template_name=template.name,
                    subject=final_subject,
                    error_message=message,
                )
                logger.exception(
                    "fair_email_outbox_unexpected_failure batch_id=%s outbox_id=%s email=%s",
                    batch.id,
                    outbox.id,
                    outbox.email,
                )
                continue

            self._batch_repository.update_outbox_sent(
                outbox.id,
                subject=final_subject,
                body_html=rendered_body_html,
                body_text=rendered_body_text,
            )
            self._mail_operation_sync.sync_outbox_sent(
                command.organization_id,
                outbox,
                subject=final_subject,
                body_html=rendered_body_html,
                body_text=rendered_body_text,
            )
            sent_count += 1
            self._session.commit()
            self._record_terminal_outbox_activity(
                organization_id=command.organization_id,
                batch=batch,
                outbox_id=outbox.id,
                fair_name=fair_name,
                template_name=template.name,
                subject=final_subject,
            )
            logger.info(
                "fair_email_outbox_sent batch_id=%s outbox_id=%s email=%s",
                batch.id,
                outbox.id,
                outbox.email,
            )

        sent_count, failed_count, status = self._batch_repository.recount_batch_from_outbox(batch.id)
        self._batch_repository.update_batch_counts(
            batch.id,
            status=status,
            sent_count=sent_count,
            failed_count=failed_count,
        )
        self._session.commit()
        self._sync_linked_operation(command.organization_id, batch.id)
        logger.info(
            "fair_email_batch_completed batch_id=%s status=%s sent_count=%s failed_count=%s",
            batch.id,
            status,
            sent_count,
            failed_count,
        )

    def _resolve_smtp_account(
        self,
        organization_id: UUID,
        batch: FairEmailBatchRecord,
    ) -> tuple[SmtpAccount | None, str | None]:
        account = None
        try:
            if batch.smtp_account_id is not None:
                account = self._smtp_repository.get_by_id(organization_id, batch.smtp_account_id)
            if account is None:
                account = self._smtp_repository.get_default_for_organization(organization_id)
        except Exception as exc:
            logger.exception(
                "fair_email_batch_smtp_load_failed batch_id=%s smtp_account_id=%s",
                batch.id,
                batch.smtp_account_id,
            )
            return None, str(exc)

        if account is None:
            return None, MISSING_SMTP_MESSAGE
        if account.deleted_at is not None:
            return None, "SMTP account is deleted"
        if not account.is_active:
            return None, INACTIVE_SMTP_MESSAGE
        if not account.password:
            return None, "SMTP password is not configured"
        return account, None

    def _fail_entire_batch(
        self,
        organization_id: UUID,
        batch: FairEmailBatchRecord,
        message: str,
        *,
        fair_name: str,
        template_name: str,
        default_subject: str,
    ) -> None:
        self._mail_operation_sync.ensure_operations_for_batch(
            organization_id=organization_id,
            batch=batch,
            default_subject=default_subject,
        )
        pending = self._batch_repository.list_pending_outbox(batch.id)
        self._batch_repository.fail_all_pending_outbox(batch.id, message=message)
        for outbox in pending:
            self._mail_operation_sync.sync_outbox_failed(
                organization_id,
                outbox,
                error_code="batch_failure",
                error_message=message,
            )
        self._batch_repository.update_batch_counts(
            batch.id,
            status="failed",
            sent_count=0,
            failed_count=max(len(pending), batch.total_count),
        )
        for outbox in pending:
            self._record_terminal_outbox_activity(
                organization_id=organization_id,
                batch=batch,
                outbox_id=outbox.id,
                fair_name=fair_name,
                template_name=template_name,
                subject=default_subject,
                error_message=message,
            )
        self._sync_linked_operation(organization_id, batch.id)

    def _fail_unprocessed_batch(self, organization_id: UUID, batch_id: UUID, message: str) -> None:
        batch = self._batch_repository.get_batch(organization_id, batch_id)
        if batch is None:
            return
        template = self._template_repository.get_by_id(organization_id, batch.template_id)
        template_name = template.name if template else ""
        default_subject = batch.subject_override or (template.subject if template else "")
        self._mail_operation_sync.ensure_operations_for_batch(
            organization_id=organization_id,
            batch=batch,
            default_subject=default_subject or "Toplu mail",
        )
        pending = self._batch_repository.list_pending_outbox(batch_id)
        self._batch_repository.fail_all_pending_outbox(batch_id, message=message)
        for outbox in pending:
            self._mail_operation_sync.sync_outbox_failed(
                organization_id,
                outbox,
                error_code="batch_failure",
                error_message=message,
            )
        sent_count, failed_count, status = self._batch_repository.recount_batch_from_outbox(batch_id)
        if sent_count == 0:
            status = "failed"
        elif status == "processing":
            status = "completed_with_errors"
        self._batch_repository.update_batch_counts(
            batch_id,
            status=status,
            sent_count=sent_count,
            failed_count=max(failed_count, len(pending)),
        )
        fair_name = self._load_fair_name(organization_id, batch.fair_id)
        for outbox in pending:
            self._record_terminal_outbox_activity(
                organization_id=organization_id,
                batch=batch,
                outbox_id=outbox.id,
                fair_name=fair_name,
                template_name=template_name,
                subject=default_subject,
                error_message=message,
            )
        self._sync_linked_operation(organization_id, batch_id)

    def _record_terminal_outbox_activity(
        self,
        *,
        organization_id: UUID,
        batch: FairEmailBatchRecord,
        outbox_id: UUID,
        fair_name: str,
        template_name: str,
        subject: str,
        error_message: str | None = None,
    ) -> None:
        outbox = (
            self._session.query(FairEmailOutboxModel)
            .filter(
                FairEmailOutboxModel.id == outbox_id,
                FairEmailOutboxModel.organization_id == organization_id,
            )
            .one_or_none()
        )
        if outbox is None:
            return
        try:
            self._activity_writer.record_terminal_outbox(
                FairBulkEmailActivityContext(
                    organization_id=organization_id,
                    batch=batch,
                    outbox=outbox,
                    fair_name=fair_name,
                    template_name=template_name,
                    subject=subject,
                    terminal_status="sent" if outbox.status == "sent" else "failed",
                    error_message=error_message,
                )
            )
            self._session.commit()
        except Exception:
            logger.exception(
                "fair_bulk_email_activity_write_failed batch_id=%s outbox_id=%s",
                batch.id,
                outbox_id,
            )

    def _load_fair_name(self, organization_id: UUID, fair_id: UUID | None) -> str:
        if fair_id is None:
            return ""
        from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository

        fair = SqlAlchemyFairRepository(self._session).get_by_id(organization_id, fair_id)
        return fair.name if fair else ""

    def _build_variables(self, organization_id: UUID, fair_name: str, outbox) -> dict[str, str]:
        contact_first_name = ""
        contact_last_name = ""
        contact_title = ""
        if outbox.contact_id is not None:
            contact = self._recipient_loader.load_contact(organization_id, outbox.contact_id)
            if contact is not None:
                contact_first_name = contact.first_name
                contact_last_name = contact.last_name
                contact_title = contact.title or ""

        hall = ""
        stand = ""
        if outbox.participation_id is not None:
            participation = self._recipient_loader.load_participation_by_id(
                organization_id,
                outbox.participation_id,
            )
            if participation is not None:
                hall = participation.hall or ""
                stand = participation.stand or ""

        return build_render_variables(
            fair_name=fair_name,
            customer_name=outbox.company_name or "",
            contact_first_name=contact_first_name,
            contact_last_name=contact_last_name,
            contact_title=contact_title,
            hall=hall,
            stand=stand,
        )

    def _sync_linked_operation(self, organization_id: UUID, batch_id: UUID) -> None:
        batch = self._batch_repository.get_batch(organization_id, batch_id)
        if batch is None or batch.operation_id is None:
            return
        try:
            from app.modules.operations.infrastructure.handlers.bulk_email_operation_sync import (
                sync_operation_run_from_batch,
            )

            sync_operation_run_from_batch(
                self._session,
                organization_id=organization_id,
                operation_id=batch.operation_id,
                batch=batch,
            )
            self._session.commit()
        except Exception:
            logger.exception(
                "fair_email_batch_operation_sync_failed batch_id=%s operation_id=%s",
                batch_id,
                batch.operation_id,
            )


_batch_session_factory: Callable[[], Session] | None = None


def configure_batch_session_factory(factory: Callable[[], Session]) -> None:
    global _batch_session_factory
    _batch_session_factory = factory


def process_fair_email_batch(batch_id: UUID, organization_id: UUID) -> None:
    from app.db.session import SessionLocal

    logger.info(
        "fair_email_batch_task_started batch_id=%s organization_id=%s",
        batch_id,
        organization_id,
    )
    session_factory = _batch_session_factory or SessionLocal
    session = session_factory()
    try:
        ProcessFairEmailBatchUseCase(session).execute(
            ProcessBatchCommand(batch_id=batch_id, organization_id=organization_id)
        )
    except Exception:
        logger.exception(
            "fair_email_batch_task_failed batch_id=%s organization_id=%s",
            batch_id,
            organization_id,
        )
        raise
    finally:
        if _batch_session_factory is None:
            session.close()
