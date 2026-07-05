#!/usr/bin/env python3
"""Diagnose SMTP test mail delivery for a tenant account."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _safe_print(text: str) -> None:
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.modules.smtp.application.smtp_test_debug import build_test_mail_failure_result
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from app.modules.smtp.domain.smtp_config_validation import smtp_config_warnings
from app.modules.smtp.infrastructure.persistence.mappers import model_to_entity
from app.modules.smtp.infrastructure.persistence.models import SmtpAccountModel
from app.modules.smtp.infrastructure.smtp_mailer import send_smtp_message


def _parse_uuid(value: str, label: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise SystemExit(f"Invalid {label}: {value}") from exc


def _resolve_account(
    session: Session,
    *,
    organization_id: UUID,
    account_id: UUID | None,
    account_name: str | None,
) -> SmtpAccountModel:
    stmt = select(SmtpAccountModel).where(
        SmtpAccountModel.organization_id == organization_id,
        SmtpAccountModel.deleted_at.is_(None),
    )
    if account_id is not None:
        stmt = stmt.where(SmtpAccountModel.id == account_id)
    elif account_name is not None:
        stmt = stmt.where(SmtpAccountModel.name == account_name)
    else:
        raise SystemExit("Provide --account-id or --account-name")

    model = session.scalars(stmt).first()
    if model is None:
        raise SystemExit("SMTP account not found for the given organization scope")
    return model


def _print_account(model: SmtpAccountModel) -> None:
    try:
        entity = model_to_entity(model)
        password_set = bool(entity.password)
        warnings = smtp_config_warnings(entity.port, entity.encryption_type)
    except Exception as exc:
        password_set = bool(model.password)
        warnings = smtp_config_warnings(model.port, model.encryption_type)
        _safe_print(f"  password_decrypt_error: {exc}")

    _safe_print("SMTP account")
    _safe_print(f"  id: {model.id}")
    _safe_print(f"  name: {model.name}")
    _safe_print(f"  organization_id: {model.organization_id}")
    _safe_print(f"  host: {model.host}")
    _safe_print(f"  port: {model.port}")
    _safe_print(f"  encryption_type: {model.encryption_type}")
    _safe_print(f"  from_email: {model.from_email}")
    _safe_print(f"  username: {model.username or '-'}")
    _safe_print(f"  password_set: {password_set}")
    _safe_print(f"  is_active: {model.is_active}")
    _safe_print(f"  config_warnings_count: {len(warnings)}")
    for warning in warnings:
        _safe_print(f"    - {warning}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a local SMTP test-mail diagnosis.")
    parser.add_argument("--organization-id", required=True, help="Tenant organization UUID")
    parser.add_argument("--account-id", help="SMTP account UUID")
    parser.add_argument("--account-name", help="Exact SMTP account name, e.g. 'Umaay Mailer Send'")
    parser.add_argument("--to-email", required=True, help="Recipient email for the test message")
    args = parser.parse_args()

    organization_id = _parse_uuid(args.organization_id, "organization id")
    account_id = _parse_uuid(args.account_id, "account id") if args.account_id else None
    if account_id is None and not args.account_name:
        parser.error("Provide --account-id or --account-name")

    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/fair_crm",
    )
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as session:
        model = _resolve_account(
            session,
            organization_id=organization_id,
            account_id=account_id,
            account_name=args.account_name,
        )
        _print_account(model)
        try:
            account = model_to_entity(model)
        except Exception as exc:
            _safe_print("")
            _safe_print(
                f"Cannot decrypt SMTP password with current FAIR_CRM_SMTP_SECRET_ENCRYPTION_KEY: {exc}"
            )
            return 2

    _safe_print("")
    _safe_print(f"Sending test mail to: {args.to_email}")

    try:
        send_smtp_message(
            account,
            recipient=args.to_email.strip(),
            subject="FAIR CRM SMTP Debug Test",
            body="Debug test message from scripts/debug_smtp_test.py",
        )
    except SmtpMailDeliveryError as exc:
        failure = build_test_mail_failure_result(account, recipient=args.to_email.strip(), exc=exc)
        _safe_print("Result: FAILED")
        _safe_print(f"  safe_message: {failure.message}")
        _safe_print(f"  exception_type: {failure.debug_error_type}")
        _safe_print(f"  raw_message: {failure.debug_error_message}")
        _safe_print(f"  config_warnings: {list(failure.config_warnings)}")
        return 1

    _safe_print("Result: SUCCESS")
    _safe_print("  safe_message: Test email sent successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
