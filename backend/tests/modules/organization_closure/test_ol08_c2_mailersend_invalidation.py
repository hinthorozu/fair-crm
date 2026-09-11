from __future__ import annotations

from datetime import UTC, datetime
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.integrations.kyrox_core.ports import AuthContext
from app.integrations.mailersend.token_verification import (
    OUTCOME_INVALID,
    OUTCOME_NOT_PROVEN_INVALID,
    OUTCOME_UNKNOWN,
    MailerSendTokenVerificationResult,
)
from app.modules.email_accounts.infrastructure.persistence.models import (
    EmailAccountModel,
    EmailAccountProviderConfigModel,
)
from app.modules.email_accounts.infrastructure.repositories.email_account_repository import (
    SqlAlchemyEmailAccountRepository,
)
from app.modules.organization_closure.application.credential_disposition import (
    EXTERNAL_CONFIRMED,
    STATUS_BLOCKED_SUPPORTED_UNIDENTIFIABLE,
    STATUS_DISPOSITION_COMPLETE,
    OrganizationClosureCredentialDispositionService,
)
from app.modules.organization_closure.application.mailersend_invalidation import (
    MailerSendCredentialInvalidationService,
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
    OrganizationClosureCredentialEventModel,
)
from app.modules.organization_closure.infrastructure.repository import (
    SqlAlchemyOrganizationClosureRepository,
)
from app.shared.secret_encryption import encrypt_secret


class FakeAuthorization:
    def __init__(self, *, allowed: bool = True) -> None:
        self.allowed = allowed

    def check_permission(self, **kwargs: object) -> bool:
        _ = kwargs
        return self.allowed


class FakeLifecycle:
    def __init__(self, *, status: str = "suspended") -> None:
        self.status = status

    def get_snapshot(self, organization_id: object) -> SimpleNamespace:
        _ = organization_id
        return SimpleNamespace(status=self.status, is_deleted=False)


class RecordingAudit:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def record_event(self, **kwargs: object) -> None:
        self.events.append(kwargs)


class FakeVerifier:
    def __init__(self, *results: MailerSendTokenVerificationResult) -> None:
        self.results = list(results)
        self.calls: list[str] = []

    def verify(self, api_token: str) -> MailerSendTokenVerificationResult:
        self.calls.append(api_token)
        if not self.results:
            raise AssertionError("Unexpected MailerSend verification call")
        return self.results.pop(0)


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
        idempotency_key=f"ol08-c2-{uuid4()}",
        auth=auth,
        access_token="token",
    )
    db_session.flush()
    return execution, auth


def _mailersend_account(db_session, organization_id):
    now = datetime.now(tz=UTC)
    account = EmailAccountModel(
        id=uuid4(),
        organization_id=organization_id,
        name="C2 MailerSend",
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


def _start_disposition(db_session, organization_id, execution, auth):
    service = OrganizationClosureCredentialDispositionService(
        SqlAlchemyOrganizationClosureCredentialDispositionRepository(db_session),
        SqlAlchemyOrganizationClosureRepository(db_session),
        SqlAlchemyEmailAccountRepository(db_session),
        FakeAuthorization(),
        FakeLifecycle(),
        RecordingAudit(),
    )
    return service.start(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )[0]


def _verification_service(
    db_session,
    verifier: FakeVerifier,
    *,
    lifecycle_status: str = "suspended",
):
    audit = RecordingAudit()
    service = MailerSendCredentialInvalidationService(
        SqlAlchemyOrganizationClosureCredentialDispositionRepository(db_session),
        SqlAlchemyOrganizationClosureRepository(db_session),
        SqlAlchemyEmailAccountRepository(db_session),
        FakeAuthorization(),
        FakeLifecycle(status=lifecycle_status),
        audit,
        verifier=verifier,
    )
    return service, audit


def test_definitive_401_proof_zeroizes_exact_local_token_idempotently(
    db_session,
    organization_id,
) -> None:
    execution, auth = _start_closure(db_session, organization_id)
    account, provider_config = _mailersend_account(db_session, organization_id)
    disposition = _start_disposition(
        db_session,
        organization_id,
        execution,
        auth,
    )
    verifier = FakeVerifier(
        MailerSendTokenVerificationResult(
            outcome=OUTCOME_INVALID,
            evidence_code="mailersend_exact_secret_http_401",
        )
    )
    service, audit = _verification_service(db_session, verifier)

    result = service.verify(
        organization_id=organization_id,
        execution_id=execution.id,
        disposition_id=disposition.id,
        auth=auth,
        access_token="token",
    )

    assert verifier.calls == ["mailersend-api-secret"]
    assert result.external_invalidation_state == EXTERNAL_CONFIRMED
    assert result.status == STATUS_DISPOSITION_COMPLETE
    assert result.external_invalidated_at is not None
    assert result.send_secret_purged_at is not None
    assert result.failure_code is None

    decrypted = SqlAlchemyEmailAccountRepository(db_session).get_provider_config(
        account.id,
        organization_id=organization_id,
    )
    assert decrypted is not None
    assert decrypted.config["api_token"] == ""
    assert decrypted.config["webhook_signing_secret"] == ""

    events = list(
        db_session.scalars(
            select(OrganizationClosureCredentialEventModel).where(
                OrganizationClosureCredentialEventModel.disposition_id == disposition.id
            )
        ).all()
    )
    durable_text = " ".join(
        f"{event.action} {event.evidence_code or ''} {event.evidence_reference or ''}"
        for event in events
    ) + str(audit.events)
    assert "mailersend-api-secret" not in durable_text
    assert "Bearer" not in durable_text
    assert "mailersend_exact_secret_http_401" in durable_text

    second = service.verify(
        organization_id=organization_id,
        execution_id=execution.id,
        disposition_id=disposition.id,
        auth=auth,
        access_token="token",
    )
    assert second.status == STATUS_DISPOSITION_COMPLETE
    assert verifier.calls == ["mailersend-api-secret"]

    db_session.refresh(provider_config)
    assert "mailersend-api-secret" not in provider_config.config_json


@pytest.mark.parametrize(
    ("outcome", "evidence_code"),
    [
        (OUTCOME_NOT_PROVEN_INVALID, "mailersend_exact_secret_http_200"),
        (OUTCOME_NOT_PROVEN_INVALID, "mailersend_exact_secret_http_403"),
        (OUTCOME_UNKNOWN, "mailersend_exact_secret_http_429"),
        (OUTCOME_UNKNOWN, "mailersend_exact_secret_http_5xx"),
        (OUTCOME_UNKNOWN, "mailersend_exact_secret_transport_error"),
    ],
)
def test_non_401_results_remain_blocked_and_preserve_reconciliation_secret(
    db_session,
    organization_id,
    outcome: str,
    evidence_code: str,
) -> None:
    execution, auth = _start_closure(db_session, organization_id)
    account, _ = _mailersend_account(db_session, organization_id)
    disposition = _start_disposition(db_session, organization_id, execution, auth)
    verifier = FakeVerifier(
        MailerSendTokenVerificationResult(
            outcome=outcome,
            evidence_code=evidence_code,
        )
    )
    service, _ = _verification_service(db_session, verifier)

    result = service.verify(
        organization_id=organization_id,
        execution_id=execution.id,
        disposition_id=disposition.id,
        auth=auth,
        access_token="token",
    )

    assert result.status == STATUS_BLOCKED_SUPPORTED_UNIDENTIFIABLE
    assert result.external_invalidation_state == "blocked_supported_unidentifiable"
    assert result.failure_code == evidence_code
    assert result.external_invalidated_at is None
    assert result.send_secret_purged_at is None

    decrypted = SqlAlchemyEmailAccountRepository(db_session).get_provider_config(
        account.id,
        organization_id=organization_id,
    )
    assert decrypted is not None
    assert decrypted.config["api_token"] == "mailersend-api-secret"


def test_ambiguous_verification_can_be_reconciled_later_by_definitive_401(
    db_session,
    organization_id,
) -> None:
    execution, auth = _start_closure(db_session, organization_id)
    account, _ = _mailersend_account(db_session, organization_id)
    disposition = _start_disposition(db_session, organization_id, execution, auth)
    verifier = FakeVerifier(
        MailerSendTokenVerificationResult(
            outcome=OUTCOME_UNKNOWN,
            evidence_code="mailersend_exact_secret_transport_error",
        ),
        MailerSendTokenVerificationResult(
            outcome=OUTCOME_INVALID,
            evidence_code="mailersend_exact_secret_http_401",
        ),
    )
    service, _ = _verification_service(db_session, verifier)

    first = service.verify(
        organization_id=organization_id,
        execution_id=execution.id,
        disposition_id=disposition.id,
        auth=auth,
        access_token="token",
    )
    assert first.status == STATUS_BLOCKED_SUPPORTED_UNIDENTIFIABLE

    second = service.verify(
        organization_id=organization_id,
        execution_id=execution.id,
        disposition_id=disposition.id,
        auth=auth,
        access_token="token",
    )
    assert second.status == STATUS_DISPOSITION_COMPLETE
    assert second.external_invalidation_state == EXTERNAL_CONFIRMED
    assert verifier.calls == ["mailersend-api-secret", "mailersend-api-secret"]

    decrypted = SqlAlchemyEmailAccountRepository(db_session).get_provider_config(
        account.id,
        organization_id=organization_id,
    )
    assert decrypted is not None
    assert decrypted.config["api_token"] == ""


def test_verification_fails_closed_when_organization_is_not_suspended(
    db_session,
    organization_id,
) -> None:
    execution, auth = _start_closure(db_session, organization_id)
    account, _ = _mailersend_account(db_session, organization_id)
    disposition = _start_disposition(db_session, organization_id, execution, auth)
    verifier = FakeVerifier(
        MailerSendTokenVerificationResult(
            outcome=OUTCOME_INVALID,
            evidence_code="mailersend_exact_secret_http_401",
        )
    )
    service, _ = _verification_service(
        db_session,
        verifier,
        lifecycle_status="active",
    )

    with pytest.raises(ClosureLifecyclePreconditionError):
        service.verify(
            organization_id=organization_id,
            execution_id=execution.id,
            disposition_id=disposition.id,
            auth=auth,
            access_token="token",
        )

    assert verifier.calls == []
    decrypted = SqlAlchemyEmailAccountRepository(db_session).get_provider_config(
        account.id,
        organization_id=organization_id,
    )
    assert decrypted is not None
    assert decrypted.config["api_token"] == "mailersend-api-secret"


def test_missing_local_exact_secret_never_fabricates_external_invalidation(
    db_session,
    organization_id,
) -> None:
    execution, auth = _start_closure(db_session, organization_id)
    account, _ = _mailersend_account(db_session, organization_id)
    disposition = _start_disposition(db_session, organization_id, execution, auth)

    repository = SqlAlchemyEmailAccountRepository(db_session)
    pair = repository.get_with_provider_config(organization_id, account.id)
    assert pair is not None
    account_entity, provider_config = pair
    provider_config.config = dict(provider_config.config)
    provider_config.config["api_token"] = ""
    provider_config.updated_at = datetime.now(tz=UTC)
    repository.update_provider_account(account_entity, provider_config)

    verifier = FakeVerifier(
        MailerSendTokenVerificationResult(
            outcome=OUTCOME_INVALID,
            evidence_code="mailersend_exact_secret_http_401",
        )
    )
    service, _ = _verification_service(db_session, verifier)

    with pytest.raises(ClosureExecutionConflictError, match="cannot be proven"):
        service.verify(
            organization_id=organization_id,
            execution_id=execution.id,
            disposition_id=disposition.id,
            auth=auth,
            access_token="token",
        )

    assert verifier.calls == []
    assert disposition.external_invalidation_state != EXTERNAL_CONFIRMED
    assert disposition.status == STATUS_BLOCKED_SUPPORTED_UNIDENTIFIABLE
