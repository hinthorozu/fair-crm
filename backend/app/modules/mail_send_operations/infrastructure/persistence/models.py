from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, synonym

from app.db.base import Base


class MailSendOperationModel(Base):
    __tablename__ = "mail_send_operations"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="fair_bulk_email")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=99)
    recipient_email: Mapped[str] = mapped_column(String(320), nullable=False)
    recipient_name: Mapped[str | None] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(500), nullable=False, default="Toplu e-posta")
    body_html: Mapped[str | None] = mapped_column(Text)
    body_text: Mapped[str | None] = mapped_column(Text)
    email_account_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    template_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    fair_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    customer_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    contact_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    participation_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    batch_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    company_name: Mapped[str | None] = mapped_column(String(255))
    recipient_source: Mapped[str | None] = mapped_column(String(32))
    fair_name: Mapped[str | None] = mapped_column(String(255))
    skip_reason: Mapped[str | None] = mapped_column(String(255))
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    error_code: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    operation_logs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sending_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_message_id: Mapped[str | None] = mapped_column(String(255))
    provider_status: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Compatibility names used by the fair bulk-email API. These are aliases on
    # the same physical row; there is no second outbox record anymore.
    email = synonym("recipient_email")
    source = synonym("recipient_source")
    rendered_subject = synonym("subject")
    rendered_body_html = synonym("body_html")
    rendered_body_text = synonym("body_text")
    send_attempt = synonym("retry_count")
    mail_send_operation_id = synonym("id")
