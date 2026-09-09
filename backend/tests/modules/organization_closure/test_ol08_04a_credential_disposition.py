from __future__ import annotations

from datetime import UTC, datetime
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.integrations.kyrox_core.ports import AuthContext
from app.modules.email_accounts.infrastructure.persistence.models import (
    EmailAccountModel,
    EmailAccountProviderConfigModel,
    EmailAccountSmtpConfigModel,
)
from app.modules.email_accounts.infrastructure.repositories.email_account_repository import (
    SqlAlchemyEmailAccountRepository,
)
from app.modules.organization_closure.application.credential_disposition import (
    ACTION_CONFIRM_EXTERNAL_INVALIDATION,
    ACTION_RECORD_TARGET,
    CAPABILITY_OPERATOR_REQUIRED,
    CAPABILITY_SUPPORTED_UNIDENTIFIABLE,
    EXTERNAL_CONFIRMED,
    STATUS_BLOCKED_SUPPORTED_UNIDENTIFIABLE,
    STATUS_DISPOSITION_COMPLETE,
    STATUS_OPERATOR_REQUIRED,
    TARGET_UNVERIFIED,
    OrganizationClosureCredentialDispositionService,
)
from app.modules.organization_closure.application.service import (
    ClosureExecutionConflictError,
    ClosureLifecyclePreconditionError,
    OrganizationClosureService,
)
from app.modules.organization_closure.infrastructure.credential_disposition_repository import (
    SqlAlchemyOrganizationClosureCredentialDispositionRepository,
)
from app.modules.organization_closure.infrastructure.models import (
    OrganizationClosureCredentialDispositionModel,
    OrganizationClosureCredentialEventModel,
)
from app.modules.organization_closure.infrastructure.repository import (
    SqlAlchemyOrganizationClosureRepository,
)
from app.shared.secret_encryption import encrypt_secret


class FakeAuthorization:
    def __init__(self, *, allowed: bool = True) -> None:
        self.allowed = allowed
        self.calls: list[dict[str, object]] = []

    def check_permission(self, **kwargs: object) -> bool:
        self.calls.append(kwargs)
        return self.allowed


class FakeLifecycle:
    def __init__(self, *, status: str = "suspended") -> None:
        self.status = status
        self.calls: list[object] = []

    def get_snapshot(self, organization_id: object) -> SimpleNamespace:
        self.calls.append(organization_id)
        return SimpleNamespace(status=self.status)


class RecordingAudit:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def record_event(self, **kwargs: object) -> None:
        self.events.append(kwargs)


def _auth(organization_id):
    return AuthContext(
        user_id=uuid4(),
        email="platform-admin@example.com",
        session_id=uuid4(),
        organization_id=organization_id,
    )


def _start_closure(db_session, organization_id):
    auth = _auth(organization_id)
    service = OrganizationClosureService(
        SqlAlchemyOrganizationClosureRepository(db_session),
        FakeAuthorization(),
        FakeLifecycle(),
        RecordingAudit(),
    )
    execution = service.start(
        organization_id=organization_id,
        idempotency_key=f"ol08-04a-{uuid4()}",
        auth=auth,
        access_token="token",
    )
    db_session.flush()
    return execution, auth


def _service(db_session, *, lifecycle_status: str = "suspended"):
    authorization = FakeAuthorization()
    lifecycle = FakeLifecycle(status=lifecycle_status)
    audit = RecordingAudit()
    service = OrganizationClosureCredentialDispositionService(
        SqlAlchemyOrganizationClosureCredentialDispositionRepository(db_session),
        SqlAlchemyOrganizationClosureRepository(db_session),
        SqlAlchemyEmailAccountRepository(db_session),
        authorization,
        lifecycle,
        audit,
    )
    return service, authorization, lifecycle, audit


def _smtp_account(db_session, organization_id, *, password: str | None = "smtp-secret"):
    now = datetime.now(tz=UTC)
    account = EmailAccountModel(
        id=uuid4(),
        organization_id=organization_id,
        name="Closure SMTP",
        account_type="smtp",
        provider_key=None,
        from_email="smtp@example.com",
        from_name="SMTP",
        is_default=True,
        is_active=True,
        max_delivery_attempts=3,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    config = EmailAccountSmtpConfigModel(
        email_account_id=account.id,
        host="smtp.example.com",
        port=587,
        username="user",
        password=encrypt_secret(password),
        encryption_type="starttls",
    )
    db_session.add_all([account, config])
    db_session.flush()
    return account, config


def _mailersend_account(db_session, organization_id):
    now = datetime.now(tz=UTC)
    account = EmailAccountModel(
        id=uuid4(),
        organization_id=organization_id,
        name="Closure MailerSend",
        account_type="provider",
        provider_key="mailersend",
        from_email="provider@example.com",
        from_name="Provider",
        is_default=False,
        is_active=True,
        max_delivery_attempts=3,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    config = EmailAccountProviderConfigModel(
        email_account_id=account.id,
        provider_key="mailersend",
        config_json=json.dumps(
            {
                "api_token": encrypt_secret("mailersend-api-secret"),
                "from_email": "provider@example.com",
                "from_name": "Provider",
                "webhook_signing_secret": encrypt_secret("webhook-secret"),
            }
        ),
        error_policy_json="{}",
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([account, config])
    db_session.flush()
    return account, config


def test_start_disables_outbound_and_classifies_smtp_idempotently(
    db_session,
    organization_id,
) -> None:
    execution, auth = _start_closure(db_session, organization_id)
    account, _ = _smtp_account(db_session, organization_id)
    service, authorization, lifecycle, audit = _service(db_session)

    first = service.start(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )
    second = service.start(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )

    db_session.refresh(account)
    assert account.is_active is False
    assert account.is_default is False
    assert len(first) == 1
    assert len(second) == 1
    assert first[0].id == second[0].id
    assert first[0].capability_class == CAPABILITY_OPERATOR_REQUIRED
    assert first[0].status == STATUS_OPERATOR_REQUIRED
    assert first[0].external_invalidation_state == "operator_required"
    assert authorization.calls[0]["permission_code"] == "identity.organizations.delete"
    assert lifecycle.calls == [organization_id, organization_id]

    disposition_count = db_session.scalar(
        select(func.count()).select_from(OrganizationClosureCredentialDispositionModel)
    )
    assert disposition_count == 1
    assert any(
        event.get("action") == "organization_closure.credential_disposition.started"
        for event in audit.events
    )


def test_smtp_external_evidence_precedes_local_secret_zeroization(
    db_session,
    organization_id,
) -> None:
    execution, auth = _start_closure(db_session, organization_id)
    account, config = _smtp_account(db_session, organization_id)
    service, _, _, _ = _service(db_session)
    disposition = service.start(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )[0]

    db_session.refresh(config)
    assert config.password
    assert disposition.status == STATUS_OPERATOR_REQUIRED

    reconciled = service.reconcile(
        organization_id=organization_id,
        execution_id=execution.id,
        disposition_id=disposition.id,
        action=ACTION_CONFIRM_EXTERNAL_INVALIDATION,
        external_credential_id=None,
        evidence_code="smtp_provider_credential_revoked",
        evidence_reference="ticket-12345",
        auth=auth,
        access_token="token",
    )

    db_session.refresh(config)
    db_session.refresh(account)
    assert reconciled.external_invalidation_state == EXTERNAL_CONFIRMED
    assert reconciled.status == STATUS_DISPOSITION_COMPLETE
    assert reconciled.external_invalidated_at is not None
    assert reconciled.send_secret_purged_at is not None
    assert config.password == ""
    assert account.is_active is False

    events = list(
        db_session.scalars(
            select(OrganizationClosureCredentialEventModel).where(
                OrganizationClosureCredentialEventModel.disposition_id == disposition.id
            )
        ).all()
    )
    serialized = " ".join(
        f"{event.action} {event.evidence_code or ''} {event.evidence_reference or ''}"
        for event in events
    )
    assert "smtp-secret" not in serialized
    assert "ticket-12345" in serialized


def test_mailersend_supported_unidentifiable_cannot_be_operator_overridden(
    db_session,
    organization_id,
) -> None:
    execution, auth = _start_closure(db_session, organization_id)
    account, provider_config = _mailersend_account(db_session, organization_id)
    service, _, _, _ = _service(db_session)
    disposition = service.start(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )[0]

    assert disposition.capability_class == CAPABILITY_SUPPORTED_UNIDENTIFIABLE
    assert disposition.status == STATUS_BLOCKED_SUPPORTED_UNIDENTIFIABLE
    assert disposition.failure_code == "mailersend_token_target_missing"
    assert disposition.signing_secret_retained is False

    decrypted_config = SqlAlchemyEmailAccountRepository(db_session).get_provider_config(
        account.id,
        organization_id=organization_id,
    )
    assert decrypted_config is not None
    assert decrypted_config.config["api_token"] == "mailersend-api-secret"
    assert decrypted_config.config["webhook_signing_secret"] == ""

    recorded = service.reconcile(
        organization_id=organization_id,
        execution_id=execution.id,
        disposition_id=disposition.id,
        action=ACTION_RECORD_TARGET,
        external_credential_id="provider-token-id-123",
        evidence_code="operator_supplied_target_metadata",
        evidence_reference="ticket-999",
        auth=auth,
        access_token="token",
    )
    assert recorded.external_credential_id == "provider-token-id-123"
    assert recorded.target_verification_state == TARGET_UNVERIFIED
    assert recorded.status == STATUS_BLOCKED_SUPPORTED_UNIDENTIFIABLE

    with pytest.raises(ClosureExecutionConflictError):
        service.reconcile(
            organization_id=organization_id,
            execution_id=execution.id,
            disposition_id=disposition.id,
            action=ACTION_CONFIRM_EXTERNAL_INVALIDATION,
            external_credential_id=None,
            evidence_code="claimed_deleted",
            evidence_reference="operator-claim",
            auth=auth,
            access_token="token",
        )

    db_session.refresh(provider_config)
    stored = provider_config.config_json
    assert "mailersend-api-secret" not in stored
    assert "webhook-secret" not in stored
    assert provider_config.config_json
    assert account.is_active is False

    events = list(
        db_session.scalars(
            select(OrganizationClosureCredentialEventModel).where(
                OrganizationClosureCredentialEventModel.disposition_id == disposition.id
            )
        ).all()
    )
    assert any(event.action == "webhook_signing_secret_zeroized" for event in events)


def test_non_suspended_start_fails_closed_without_disabling_account(
    db_session,
    organization_id,
) -> None:
    execution, auth = _start_closure(db_session, organization_id)
    account, _ = _smtp_account(db_session, organization_id)
    service, _, _, _ = _service(db_session, lifecycle_status="active")

    with pytest.raises(ClosureLifecyclePreconditionError):
        service.start(
            organization_id=organization_id,
            execution_id=execution.id,
            auth=auth,
            access_token="token",
        )

    db_session.refresh(account)
    assert account.is_active is True
    count = db_session.scalar(
        select(func.count()).select_from(OrganizationClosureCredentialDispositionModel)
    )
    assert count == 0


def test_foreign_organization_cannot_read_disposition_by_scoped_identity(
    db_session,
    organization_id,
    other_organization_id,
) -> None:
    execution, auth = _start_closure(db_session, organization_id)
    _smtp_account(db_session, organization_id)
    service, _, _, _ = _service(db_session)
    disposition = service.start(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )[0]

    repository = SqlAlchemyOrganizationClosureCredentialDispositionRepository(db_session)
    assert (
        repository.get_by_id(
            other_organization_id,
            execution.id,
            disposition.id,
        )
        is None
    )
