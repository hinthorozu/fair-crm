from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.core.logging import get_logger
from app.integrations.kyrox_core.lifecycle import OrganizationLifecycleGuard
from app.modules.email_accounts.application.provider_definitions import MAILERSEND_PROVIDER_KEY
from app.modules.email_accounts.infrastructure.repositories.email_account_repository import (
    SqlAlchemyEmailAccountRepository,
)

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SuspensionSecurityResult:
    outcome: str
    zeroized_signing_secrets: int


class OrganizationSuspensionSecurityService:
    """Apply the OL09-B zero-retention webhook-secret boundary.

    The Core signal is not trusted by timestamp alone. It is accepted for
    mutation only while the live Core snapshot is still the same suspended
    lifecycle episode. Delayed signals from older suspension episodes are
    acknowledged without touching current credentials.
    """

    def __init__(
        self,
        email_accounts: SqlAlchemyEmailAccountRepository,
        lifecycle: OrganizationLifecycleGuard,
    ) -> None:
        self._email_accounts = email_accounts
        self._lifecycle = lifecycle

    def apply(
        self,
        *,
        organization_id: UUID,
        lifecycle_updated_at: datetime,
    ) -> SuspensionSecurityResult:
        snapshot = self._lifecycle.get_snapshot(organization_id)
        if (
            snapshot.status != "suspended"
            or snapshot.updated_at != lifecycle_updated_at
        ):
            logger.info(
                "ol09b_stale_suspension_signal_ignored organization_id=%s "
                "signal_updated_at=%s core_status=%s core_updated_at=%s",
                organization_id,
                lifecycle_updated_at.isoformat(),
                snapshot.status,
                snapshot.updated_at.isoformat(),
            )
            return SuspensionSecurityResult(
                outcome="stale_ignored",
                zeroized_signing_secrets=0,
            )

        now = datetime.now(tz=UTC)
        zeroized = 0
        for account in self._email_accounts.list_by_organization(organization_id):
            if (account.provider_key or "").strip().lower() != MAILERSEND_PROVIDER_KEY:
                continue
            provider_config = self._email_accounts.get_provider_config(
                account.id,
                organization_id=organization_id,
            )
            if provider_config is None:
                continue
            signing_secret = (
                provider_config.config.get("webhook_signing_secret") or ""
            ).strip()
            if not signing_secret:
                continue

            # Mutate only the inbound verification credential. The MailerSend
            # api_token is intentionally preserved so OL08-C2 can continue to
            # report supported_unidentifiable until exact provider authority is
            # independently proven invalidated.
            provider_config.config = dict(provider_config.config)
            provider_config.config["webhook_signing_secret"] = ""
            provider_config.updated_at = now
            self._email_accounts.update_provider_account(account, provider_config)
            zeroized += 1

        logger.info(
            "ol09b_suspension_secret_zeroization organization_id=%s "
            "lifecycle_updated_at=%s zeroized=%s",
            organization_id,
            lifecycle_updated_at.isoformat(),
            zeroized,
        )
        return SuspensionSecurityResult(
            outcome="applied",
            zeroized_signing_secrets=zeroized,
        )
