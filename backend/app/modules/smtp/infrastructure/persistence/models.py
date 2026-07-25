"""SMTP persistence compatibility — tables live under email_accounts (A1)."""

from app.modules.email_accounts.infrastructure.persistence.models import (
    EmailAccountModel,
    EmailAccountSmtpConfigModel,
)

# Historical import path used by tests/env; maps to generic email account tables.
SmtpAccountModel = EmailAccountModel

__all__ = [
    "EmailAccountModel",
    "EmailAccountSmtpConfigModel",
    "SmtpAccountModel",
]
