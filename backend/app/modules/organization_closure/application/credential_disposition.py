from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.integrations.kyrox_core.lifecycle import (
    OrganizationLifecycleGuard,
    OrganizationLifecycleUnavailableError,
)
from app.integrations.kyrox_core.ports import AuditPort, AuthContext, AuthorizationPort
from app.modules.email_accounts.application.provider_definitions import MAILERSEND_PROVIDER_KEY
from app.modules.email_accounts.domain.value_objects import EmailAccountType
from app.modules.email_accounts.infrastructure.repositories.email_account_repository import (
    SqlAlchemyEmailAccountRepository,
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

CAPABILITY_SUPPORTED_UNIDENTIFIABLE = "supported_unidentifiable"
CAPABILITY_OPERATOR_REQUIRED = "operator_required"
CAPABILITY_NOT_APPLICABLE = "not_applicable"

EXTERNAL_BLOCKED_SUPPORTED_UNIDENTIFIABLE = "blocked_supported_unidentifiable"
EXTERNAL_OPERATOR_REQUIRED = "operator_required"
EXTERNAL_NOT_APPLICABLE = "not_applicable"
EXTERNAL_CONFIRMED = "confirmed"

TARGET_MISSING = "missing"
TARGET_UNVERIFIED = "unverified"
TARGET_NOT_REQUIRED = "not_required"

STATUS_OUTBOUND_DISABLED = "outbound_disabled"
STATUS_OPERATOR_REQUIRED = "operator_required"
STATUS_BLOCKED_SUPPORTED_UNIDENTIFIABLE = "blocked_supported_unidentifiable"
STATUS_LOCAL_SEND_SECRETS_PURGED = "local_send_secrets_purged"
STATUS_DISPOSITION_COMPLETE = "disposition_complete"

ACTION_RECORD_TARGET = "record_target"
ACTION_CONFIRM_EXTERNAL_INVALIDATION = "confirm_external_invalidation"


class OrganizationClosureCredentialDispositionService:
    def __init__(
        self,
        disposition_repository: SqlAlchemyOrganizationClosureCredentialDispositionRepository,
        closure_repository: SqlAlchemyOrganizationClosureRepository,
        email_accounts: SqlAlchemyEmailAccountRepository,
        authorization: AuthorizationPort,
        lifecycle: OrganizationLifecycleGuard,
        audit: AuditPort,
    ) -> None:
        self._repository = disposition_repository
        self._closures = closure_repository
        self._email_accounts = email_accounts
        self._authorization = authorization
        self._lifecycle = lifecycle
        self._audit = audit

    def start(
        self,
        *,
        organization_id: UUID,
        execution_id: UUID,
        auth: AuthContext,
        access_token: str,
    ) -> list[OrganizationClosureCredentialDispositionModel]:
        self._require_system_authority(organization_id, auth, access_token)
        self._require_suspended(organization_id)
        self._require_open_execution(organization_id, execution_id)

        accounts = self._email_accounts.list_by_organization(organization_id)
        now = datetime.now(tz=UTC)
        for account in accounts:
            existing = self._repository.get_by_account(
                organization_id,
                execution_id,
                account.id,
            )
            if existing is not None:
                continue

            account.update_common_fields(
                is_active=False,
                is_default=False,
                now=now,
            )
            self._email_accounts.update_account(account)

            disposition = OrganizationClosureCredentialDispositionModel(
                id=uuid4(),
                organization_id=organization_id,
                closure_execution_id=execution_id,
                email_account_id=account.id,
                account_type=account.account_type.value,
                provider_key=account.provider_key,
                capability_class=CAPABILITY_NOT_APPLICABLE,
                external_invalidation_state=EXTERNAL_NOT_APPLICABLE,
                target_verification_state=TARGET_NOT_REQUIRED,
                external_credential_id=None,
                status=STATUS_OUTBOUND_DISABLED,
                signing_secret_retained=False,
                attempt_count=1,
                failure_code=None,
                failure_message=None,
                actor_user_id=auth.user_id,
                actor_session_id=auth.session_id,
                outbound_disabled_at=now,
                external_invalidated_at=None,
                send_secret_purged_at=None,
                created_at=now,
                updated_at=now,
                last_retry_at=None,
            )
            self._repository.add_disposition(disposition)
            self._repository.flush()
            self._append_event(
                disposition=disposition,
                actor=auth,
                action="outbound_disabled",
                from_status=None,
                to_status=STATUS_OUTBOUND_DISABLED,
                at=now,
                evidence_code="email_account_inactive_for_closure",
            )
            self._classify(disposition, account.account_type, account.provider_key, auth, now)
            self._repository.flush()
            self._record_audit(
                organization_id=organization_id,
                access_token=access_token,
                disposition=disposition,
                action="organization_closure.credential_disposition.started",
            )

        return self._repository.list_for_execution(organization_id, execution_id)

    def list(
        self,
        *,
        organization_id: UUID,
        execution_id: UUID,
        auth: AuthContext,
        access_token: str,
    ) -> list[OrganizationClosureCredentialDispositionModel]:
        self._require_system_authority(organization_id, auth, access_token)
        self._require_open_execution(organization_id, execution_id)
        return self._repository.list_for_execution(organization_id, execution_id)

    def get(
        self,
        *,
        organization_id: UUID,
        execution_id: UUID,
        disposition_id: UUID,
        auth: AuthContext,
        access_token: str,
    ) -> OrganizationClosureCredentialDispositionModel:
        self._require_system_authority(organization_id, auth, access_token)
        self._require_open_execution(organization_id, execution_id)
        disposition = self._repository.get_by_id(
            organization_id,
            execution_id,
            disposition_id,
        )
        if disposition is None:
            raise ClosureExecutionNotFoundError("Credential disposition not found")
        return disposition

    def retry(
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
        disposition = self._get_required(organization_id, execution_id, disposition_id)

        now = datetime.now(tz=UTC)
        disposition.attempt_count += 1
        disposition.last_retry_at = now
        disposition.updated_at = now
        disposition.actor_user_id = auth.user_id
        disposition.actor_session_id = auth.session_id
        self._append_event(
            disposition=disposition,
            actor=auth,
            action="retried",
            from_status=disposition.status,
            to_status=disposition.status,
            at=now,
            evidence_code="fail_closed_recheck",
        )
        self._repository.flush()
        self._record_audit(
            organization_id=organization_id,
            access_token=access_token,
            disposition=disposition,
            action="organization_closure.credential_disposition.retried",
        )
        return disposition

    def reconcile(
        self,
        *,
        organization_id: UUID,
        execution_id: UUID,
        disposition_id: UUID,
        action: str,
        external_credential_id: str | None,
        evidence_code: str | None,
        evidence_reference: str | None,
        auth: AuthContext,
        access_token: str,
    ) -> OrganizationClosureCredentialDispositionModel:
        self._require_system_authority(organization_id, auth, access_token)
        self._require_suspended(organization_id)
        self._require_open_execution(organization_id, execution_id)
        disposition = self._get_required(organization_id, execution_id, disposition_id)

        if action == ACTION_RECORD_TARGET:
            return self._record_target_metadata(
                disposition=disposition,
                external_credential_id=external_credential_id,
                evidence_code=evidence_code,
                evidence_reference=evidence_reference,
                actor=auth,
                access_token=access_token,
            )
        if action == ACTION_CONFIRM_EXTERNAL_INVALIDATION:
            return self._confirm_operator_external_invalidation(
                disposition=disposition,
                evidence_code=evidence_code,
                evidence_reference=evidence_reference,
                actor=auth,
                access_token=access_token,
            )
        raise ClosureExecutionConflictError("Unsupported credential reconciliation action")

    def _classify(self, disposition, account_type, provider_key, actor, now) -> None:
        if account_type == EmailAccountType.SMTP:
            pair = self._email_accounts.get_with_smtp_config(
                disposition.organization_id,
                disposition.email_account_id,
            )
            has_send_secret = bool(pair and pair[1].password)
            if has_send_secret:
                disposition.capability_class = CAPABILITY_OPERATOR_REQUIRED
                disposition.external_invalidation_state = EXTERNAL_OPERATOR_REQUIRED
                disposition.target_verification_state = TARGET_NOT_REQUIRED
                disposition.status = STATUS_OPERATOR_REQUIRED
                self._append_event(
                    disposition=disposition,
                    actor=actor,
                    action="operator_evidence_required",
                    from_status=STATUS_OUTBOUND_DISABLED,
                    to_status=STATUS_OPERATOR_REQUIRED,
                    at=now,
                    evidence_code="smtp_external_invalidation_requires_explicit_evidence",
                )
            else:
                disposition.capability_class = CAPABILITY_NOT_APPLICABLE
                disposition.external_invalidation_state = EXTERNAL_NOT_APPLICABLE
                disposition.target_verification_state = TARGET_NOT_REQUIRED
                disposition.status = STATUS_DISPOSITION_COMPLETE
                disposition.send_secret_purged_at = now
                self._append_event(
                    disposition=disposition,
                    actor=actor,
                    action="disposition_complete",
                    from_status=STATUS_OUTBOUND_DISABLED,
                    to_status=STATUS_DISPOSITION_COMPLETE,
                    at=now,
                    evidence_code="no_reusable_smtp_secret_present",
                )
            disposition.updated_at = now
            return

        if account_type == EmailAccountType.PROVIDER and (provider_key or "").lower() == MAILERSEND_PROVIDER_KEY:
            pair = self._email_accounts.get_with_provider_config(
                disposition.organization_id,
                disposition.email_account_id,
            )
            provider_config = pair[1] if pair is not None else None
            config = provider_config.config if provider_config is not None else {}
            has_api_token = bool((config.get("api_token") or "").strip())
            has_signing_secret = bool((config.get("webhook_signing_secret") or "").strip())

            if pair is not None and has_signing_secret:
                account, provider_config = pair
                provider_config.config = dict(provider_config.config)
                provider_config.config["webhook_signing_secret"] = ""
                provider_config.updated_at = now
                self._email_accounts.update_provider_account(account, provider_config)
                self._append_event(
                    disposition=disposition,
                    actor=actor,
                    action="webhook_signing_secret_zeroized",
                    from_status=STATUS_OUTBOUND_DISABLED,
                    to_status=STATUS_OUTBOUND_DISABLED,
                    at=now,
                    evidence_code="ol09b_zero_retention_boundary",
                )

            disposition.signing_secret_retained = False
            if has_api_token:
                disposition.capability_class = CAPABILITY_SUPPORTED_UNIDENTIFIABLE
                disposition.external_invalidation_state = EXTERNAL_BLOCKED_SUPPORTED_UNIDENTIFIABLE
                disposition.target_verification_state = TARGET_MISSING
                disposition.status = STATUS_BLOCKED_SUPPORTED_UNIDENTIFIABLE
                disposition.failure_code = "mailersend_token_target_missing"
                disposition.failure_message = (
                    "MailerSend supports token invalidation but the exact stored token cannot be "
                    "safely targeted from current FAIR CRM credential metadata"
                )
                self._append_event(
                    disposition=disposition,
                    actor=actor,
                    action="blocked_supported_unidentifiable",
                    from_status=STATUS_OUTBOUND_DISABLED,
                    to_status=STATUS_BLOCKED_SUPPORTED_UNIDENTIFIABLE,
                    at=now,
                    evidence_code="mailersend_token_target_missing",
                )
            else:
                disposition.capability_class = CAPABILITY_NOT_APPLICABLE
                disposition.external_invalidation_state = EXTERNAL_NOT_APPLICABLE
                disposition.target_verification_state = TARGET_NOT_REQUIRED
                disposition.status = STATUS_DISPOSITION_COMPLETE
                disposition.send_secret_purged_at = now
                self._append_event(
                    disposition=disposition,
                    actor=actor,
                    action="disposition_complete",
                    from_status=STATUS_OUTBOUND_DISABLED,
                    to_status=STATUS_DISPOSITION_COMPLETE,
                    at=now,
                    evidence_code="no_reusable_provider_send_secret_present",
                )
            disposition.updated_at = now
            return

        disposition.capability_class = CAPABILITY_OPERATOR_REQUIRED
        disposition.external_invalidation_state = EXTERNAL_OPERATOR_REQUIRED
        disposition.target_verification_state = TARGET_NOT_REQUIRED
        disposition.status = STATUS_OPERATOR_REQUIRED
        disposition.failure_code = "provider_capability_not_automated"
        disposition.failure_message = "Provider credential disposition requires explicit operator evidence"
        disposition.updated_at = now
        self._append_event(
            disposition=disposition,
            actor=actor,
            action="operator_evidence_required",
            from_status=STATUS_OUTBOUND_DISABLED,
            to_status=STATUS_OPERATOR_REQUIRED,
            at=now,
            evidence_code="provider_capability_not_automated",
        )

    def _record_target_metadata(
        self,
        *,
        disposition: OrganizationClosureCredentialDispositionModel,
        external_credential_id: str | None,
        evidence_code: str | None,
        evidence_reference: str | None,
        actor: AuthContext,
        access_token: str,
    ) -> OrganizationClosureCredentialDispositionModel:
        if disposition.capability_class != CAPABILITY_SUPPORTED_UNIDENTIFIABLE:
            raise ClosureExecutionConflictError(
                "External target metadata is only accepted for supported-unidentifiable credentials"
            )
        target = (external_credential_id or "").strip()
        if not target or len(target) > 200:
            raise ClosureExecutionConflictError(
                "A bounded external credential identifier is required"
            )
        now = datetime.now(tz=UTC)
        disposition.external_credential_id = target
        disposition.target_verification_state = TARGET_UNVERIFIED
        disposition.failure_code = "mailersend_token_target_unverified"
        disposition.failure_message = (
            "Target metadata is recorded but is not deterministic proof that it identifies the stored token"
        )
        disposition.updated_at = now
        disposition.actor_user_id = actor.user_id
        disposition.actor_session_id = actor.session_id
        self._append_event(
            disposition=disposition,
            actor=actor,
            action="target_metadata_recorded",
            from_status=disposition.status,
            to_status=disposition.status,
            at=now,
            evidence_code=self._bounded_evidence(evidence_code, 128) or "target_metadata_recorded",
            evidence_reference=self._bounded_evidence(evidence_reference, 255),
        )
        self._repository.flush()
        self._record_audit(
            organization_id=disposition.organization_id,
            access_token=access_token,
            disposition=disposition,
            action="organization_closure.credential_disposition.target_recorded",
        )
        return disposition

    def _confirm_operator_external_invalidation(
        self,
        *,
        disposition: OrganizationClosureCredentialDispositionModel,
        evidence_code: str | None,
        evidence_reference: str | None,
        actor: AuthContext,
        access_token: str,
    ) -> OrganizationClosureCredentialDispositionModel:
        if disposition.capability_class == CAPABILITY_SUPPORTED_UNIDENTIFIABLE:
            raise ClosureExecutionConflictError(
                "Operator evidence cannot override a supported-but-unidentifiable managed-provider credential"
            )
        if disposition.capability_class != CAPABILITY_OPERATOR_REQUIRED:
            return disposition
        code = self._bounded_evidence(evidence_code, 128)
        reference = self._bounded_evidence(evidence_reference, 255)
        if not code or not reference:
            raise ClosureExecutionConflictError(
                "Non-secret external invalidation evidence code and reference are required"
            )
        if disposition.account_type != EmailAccountType.SMTP.value:
            raise ClosureExecutionConflictError(
                "OL08-04A operator reconciliation currently supports generic SMTP credentials only"
            )

        now = datetime.now(tz=UTC)
        previous = disposition.status
        disposition.external_invalidation_state = EXTERNAL_CONFIRMED
        disposition.external_invalidated_at = now
        disposition.failure_code = None
        disposition.failure_message = None
        disposition.updated_at = now
        disposition.actor_user_id = actor.user_id
        disposition.actor_session_id = actor.session_id
        self._append_event(
            disposition=disposition,
            actor=actor,
            action="external_invalidation_confirmed",
            from_status=previous,
            to_status=previous,
            at=now,
            evidence_code=code,
            evidence_reference=reference,
        )

        pair = self._email_accounts.get_with_smtp_config(
            disposition.organization_id,
            disposition.email_account_id,
        )
        if pair is None:
            raise ClosureExecutionConflictError("SMTP credential configuration not found")
        account, smtp_config = pair
        smtp_config.update(password="")
        self._email_accounts.update_smtp_account(account, smtp_config)
        disposition.send_secret_purged_at = now
        disposition.status = STATUS_LOCAL_SEND_SECRETS_PURGED
        self._append_event(
            disposition=disposition,
            actor=actor,
            action="local_send_secret_purged",
            from_status=previous,
            to_status=STATUS_LOCAL_SEND_SECRETS_PURGED,
            at=now,
            evidence_code="smtp_password_removed_from_secret_storage",
        )
        disposition.status = STATUS_DISPOSITION_COMPLETE
        disposition.updated_at = now
        self._append_event(
            disposition=disposition,
            actor=actor,
            action="disposition_complete",
            from_status=STATUS_LOCAL_SEND_SECRETS_PURGED,
            to_status=STATUS_DISPOSITION_COMPLETE,
            at=now,
            evidence_code="credential_only_disposition_complete",
        )
        self._repository.flush()
        self._record_audit(
            organization_id=disposition.organization_id,
            access_token=access_token,
            disposition=disposition,
            action="organization_closure.credential_disposition.reconciled",
        )
        return disposition

    def _get_required(self, organization_id, execution_id, disposition_id):
        disposition = self._repository.get_by_id(
            organization_id,
            execution_id,
            disposition_id,
        )
        if disposition is None:
            raise ClosureExecutionNotFoundError("Credential disposition not found")
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
        evidence_code: str | None = None,
        evidence_reference: str | None = None,
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
                evidence_reference=evidence_reference,
                created_at=at,
            )
        )

    @staticmethod
    def _bounded_evidence(value: str | None, limit: int) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if len(normalized) > limit:
            raise ClosureExecutionConflictError("Credential evidence value is too long")
        return normalized

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
                "ol08_slice": "OL08-04A",
                "closure_execution_id": str(disposition.closure_execution_id),
                "email_account_id": str(disposition.email_account_id),
            },
        )