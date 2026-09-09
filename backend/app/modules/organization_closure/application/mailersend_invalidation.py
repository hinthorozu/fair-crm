from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.integrations.kyrox_core.lifecycle import (
    OrganizationLifecycleGuard,
    OrganizationLifecycleUnavailableError,
)
from app.integrations.kyrox_core.ports import AuditPort, AuthContext, AuthorizationPort
from app.integrations.mailersend.token_verification import (
    OUTCOME_INVALID,
    MailerSendExactSecretVerifier,
    MailerSendTokenVerificationResult,
)
from app.modules.email_accounts.application.provider_definitions import MAILERSEND_PROVIDER_KEY
from app.modules.email_accounts.domain.value_objects import EmailAccountType
from app.modules.email_accounts.infrastructure.repositories.email_account_repository import (
    SqlAlchemyEmailAccountRepository,
)
from app.modules.organization_closure.application.credential_disposition import (
    CAPABILITY_SUPPORTED_UNIDENTIFIABLE,
    EXTERNAL_BLOCKED_SUPPORTED_UNIDENTIFIABLE,
    EXTERNAL_CONFIRMED,
    STATUS_BLOCKED_SUPPORTED_UNIDENTIFIABLE,
    STATUS_DISPOSITION_COMPLETE,
    STATUS_LOCAL_SEND_SECRETS_PURGED,
)
from app.modules.organization_closure.application.service import (
    SYSTEM_CLOSURE_PERMISSION,
    ClosureAuthorizationUnavailableError,
    ClosureExecutionConflictError,
    ClosureExecutionNotFoundError,
    ClosureLifecyclePreconditionError,
    ClosureLifecycleUnavailableError,
    ClosurePermissionDeniedError,
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


class MailerSendCredentialInvalidationService:
    """Reconcile a legacy MailerSend token by exact-secret invalidity proof."""

    def __init__(
        self,
        disposition_repository: SqlAlchemyOrganizationClosureCredentialDispositionRepository,
        closure_repository: SqlAlchemyOrganizationClosureRepository,
        email_accounts: SqlAlchemyEmailAccountRepository,
        authorization: AuthorizationPort,
        lifecycle: OrganizationLifecycleGuard,
        audit: AuditPort,
        verifier: MailerSendExactSecretVerifier | None = None,
    ) -> None:
        self._repository = disposition_repository
        self._closures = closure_repository
        self._email_accounts = email_accounts
        self._authorization = authorization
        self._lifecycle = lifecycle
        self._audit = audit
        self._verifier = verifier or MailerSendExactSecretVerifier()

    def verify(
        self,
        *,
        organization_id: UUID,
        execution_id: UUID,
        disposition_id: UUID,
        auth: AuthContext,
        access_token: str,
    ) -> OrganizationClosureCredentialDispositionModel:
        self._require_system_authority(organization_id, auth, access_token)
        self._require_suspended(organization_id)
        self._require_open_execution(organization_id, execution_id)

        disposition = self._repository.get_by_id(
            organization_id,
            execution_id,
            disposition_id,
        )
        if disposition is None:
            raise ClosureExecutionNotFoundError("Credential disposition not found")

        if (
            disposition.external_invalidation_state == EXTERNAL_CONFIRMED
            and disposition.status == STATUS_DISPOSITION_COMPLETE
        ):
            return disposition

        if (
            disposition.capability_class != CAPABILITY_SUPPORTED_UNIDENTIFIABLE
            or disposition.account_type != EmailAccountType.PROVIDER.value
            or (disposition.provider_key or "").strip().lower()
            != MAILERSEND_PROVIDER_KEY
        ):
            raise ClosureExecutionConflictError(
                "Exact-secret invalidation verification is only valid for legacy MailerSend credentials"
            )
        if disposition.status != STATUS_BLOCKED_SUPPORTED_UNIDENTIFIABLE:
            raise ClosureExecutionConflictError(
                "MailerSend credential is not awaiting exact-secret invalidation verification"
            )

        pair = self._email_accounts.get_with_provider_config(
            organization_id,
            disposition.email_account_id,
        )
        if pair is None:
            raise ClosureExecutionConflictError("MailerSend credential configuration not found")
        account, provider_config = pair
        api_token = (provider_config.config.get("api_token") or "").strip()
        if not api_token:
            raise ClosureExecutionConflictError(
                "Exact MailerSend API token is unavailable; external invalidation cannot be proven"
            )

        result = self._verifier.verify(api_token)
        now = datetime.now(tz=UTC)
        disposition.attempt_count += 1
        disposition.last_retry_at = now
        disposition.updated_at = now
        disposition.actor_user_id = auth.user_id
        disposition.actor_session_id = auth.session_id

        if result.outcome != OUTCOME_INVALID:
            return self._record_unresolved_attempt(
                disposition=disposition,
                result=result,
                actor=auth,
                access_token=access_token,
                at=now,
            )

        disposition.external_invalidation_state = EXTERNAL_CONFIRMED
        disposition.external_invalidated_at = now
        disposition.failure_code = None
        disposition.failure_message = None
        self._append_event(
            disposition=disposition,
            actor=auth,
            action="mailersend_exact_secret_invalid",
            from_status=STATUS_BLOCKED_SUPPORTED_UNIDENTIFIABLE,
            to_status=STATUS_BLOCKED_SUPPORTED_UNIDENTIFIABLE,
            at=now,
            evidence_code=result.evidence_code,
        )

        provider_config.config = dict(provider_config.config)
        provider_config.config["api_token"] = ""
        provider_config.updated_at = now
        self._email_accounts.update_provider_account(account, provider_config)

        disposition.send_secret_purged_at = now
        disposition.status = STATUS_LOCAL_SEND_SECRETS_PURGED
        self._append_event(
            disposition=disposition,
            actor=auth,
            action="local_send_secret_purged",
            from_status=STATUS_BLOCKED_SUPPORTED_UNIDENTIFIABLE,
            to_status=STATUS_LOCAL_SEND_SECRETS_PURGED,
            at=now,
            evidence_code="mailersend_api_token_removed_from_secret_storage",
        )
        disposition.status = STATUS_DISPOSITION_COMPLETE
        disposition.updated_at = now
        self._append_event(
            disposition=disposition,
            actor=auth,
            action="disposition_complete",
            from_status=STATUS_LOCAL_SEND_SECRETS_PURGED,
            to_status=STATUS_DISPOSITION_COMPLETE,
            at=now,
            evidence_code="mailersend_exact_secret_invalidation_complete",
        )
        self._repository.flush()
        self._record_audit(
            organization_id=organization_id,
            access_token=access_token,
            disposition=disposition,
            action="organization_closure.credential_disposition.mailersend_invalidated",
        )
        return disposition

    def _record_unresolved_attempt(
        self,
        *,
        disposition: OrganizationClosureCredentialDispositionModel,
        result: MailerSendTokenVerificationResult,
        actor: AuthContext,
        access_token: str,
        at: datetime,
    ) -> OrganizationClosureCredentialDispositionModel:
        disposition.external_invalidation_state = EXTERNAL_BLOCKED_SUPPORTED_UNIDENTIFIABLE
        disposition.status = STATUS_BLOCKED_SUPPORTED_UNIDENTIFIABLE
        disposition.failure_code = result.evidence_code
        if result.outcome == "not_proven_invalid":
            disposition.failure_message = (
                "MailerSend did not prove the exact stored API token invalid; credential remains blocked"
            )
        else:
            disposition.failure_message = (
                "MailerSend exact-secret invalidation verification is unavailable or ambiguous; "
                "credential remains blocked"
            )
        self._append_event(
            disposition=disposition,
            actor=actor,
            action="mailersend_token_verification",
            from_status=STATUS_BLOCKED_SUPPORTED_UNIDENTIFIABLE,
            to_status=STATUS_BLOCKED_SUPPORTED_UNIDENTIFIABLE,
            at=at,
            evidence_code=result.evidence_code,
        )
        self._repository.flush()
        self._record_audit(
            organization_id=disposition.organization_id,
            access_token=access_token,
            disposition=disposition,
            action="organization_closure.credential_disposition.mailersend_verification_attempted",
        )
        return disposition

    def _require_open_execution(self, organization_id: UUID, execution_id: UUID) -> None:
        execution = self._closures.get_by_id(organization_id, execution_id)
        if execution is None or execution.closed_at is not None:
            raise ClosureExecutionNotFoundError("Open closure execution not found")

    def _require_system_authority(
        self,
        organization_id: UUID,
        auth: AuthContext,
        access_token: str,
    ) -> None:
        try:
            allowed = self._authorization.check_permission(
                organization_id=organization_id,
                user_id=auth.user_id,
                permission_code=SYSTEM_CLOSURE_PERMISSION,
                access_token=access_token,
            )
        except Exception as exc:
            raise ClosureAuthorizationUnavailableError(
                "Closure authorization authority unavailable"
            ) from exc
        if not allowed:
            raise ClosurePermissionDeniedError("Platform SuperAdmin authority required")

    def _require_suspended(self, organization_id: UUID) -> None:
        try:
            snapshot = self._lifecycle.get_snapshot(organization_id)
        except OrganizationLifecycleUnavailableError as exc:
            raise ClosureLifecycleUnavailableError(
                "Organization lifecycle authority unavailable"
            ) from exc
        if snapshot.status != "suspended":
            raise ClosureLifecyclePreconditionError(
                f"Organization must be suspended before credential disposition: {snapshot.status}"
            )

    def _append_event(
        self,
        *,
        disposition: OrganizationClosureCredentialDispositionModel,
        actor: AuthContext,
        action: str,
        from_status: str | None,
        to_status: str,
        at: datetime,
        evidence_code: str,
    ) -> None:
        self._repository.add_event(
            OrganizationClosureCredentialEventModel(
                id=uuid4(),
                disposition_id=disposition.id,
                closure_execution_id=disposition.closure_execution_id,
                organization_id=disposition.organization_id,
                email_account_id=disposition.email_account_id,
                actor_user_id=actor.user_id,
                actor_session_id=actor.session_id,
                action=action,
                from_status=from_status,
                to_status=to_status,
                evidence_code=evidence_code,
                evidence_reference=None,
                created_at=at,
            )
        )

    def _record_audit(
        self,
        *,
        organization_id: UUID,
        access_token: str,
        disposition: OrganizationClosureCredentialDispositionModel,
        action: str,
    ) -> None:
        self._audit.record_event(
            organization_id=organization_id,
            access_token=access_token,
            action=action,
            resource_type="organization_closure_credential_disposition",
            resource_id=str(disposition.id),
            new_values={
                "status": disposition.status,
                "capability_class": disposition.capability_class,
                "external_invalidation_state": disposition.external_invalidation_state,
                "target_verification_state": disposition.target_verification_state,
                "signing_secret_retained": disposition.signing_secret_retained,
            },
            metadata={
                "authority": "system",
                "ol08_slice": "OL08-C2",
                "closure_execution_id": str(disposition.closure_execution_id),
                "email_account_id": str(disposition.email_account_id),
            },
        )
