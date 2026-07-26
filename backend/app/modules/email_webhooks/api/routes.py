"""Public MailerSend email webhook ingress (no JWT)."""

from __future__ import annotations

import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.email_webhooks.application.mailersend_webhook_service import (
    MailerSendWebhookAccountNotFoundError,
    MailerSendWebhookInvalidSignatureError,
    MailerSendWebhookMissingSigningSecretError,
    MailerSendWebhookNotMailerSendAccountError,
    MailerSendWebhookService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/email", tags=["webhooks"])


@router.post("/mailersend/{email_account_id}")
async def mailersend_email_webhook(
    email_account_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    raw_body = await request.body()
    signature = request.headers.get("Signature") or request.headers.get("signature")

    try:
        payload = json.loads(raw_body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body",
        )

    service = MailerSendWebhookService(db)
    try:
        result = service.handle(
            email_account_id=email_account_id,
            raw_body=raw_body,
            signature_header=signature,
            payload=payload,
        )
    except MailerSendWebhookInvalidSignatureError as exc:
        logger.warning(
            "mailersend_webhook_invalid_signature account_id=%s",
            email_account_id,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        ) from exc
    except MailerSendWebhookMissingSigningSecretError as exc:
        logger.error(
            "mailersend_webhook_missing_signing_secret account_id=%s",
            email_account_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook signing secret not configured",
        ) from exc
    except MailerSendWebhookAccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email account not found",
        ) from exc
    except MailerSendWebhookNotMailerSendAccountError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email account is not a MailerSend provider",
        ) from exc
    except Exception as exc:
        logger.exception(
            "mailersend_webhook_internal_error account_id=%s",
            email_account_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error",
        ) from exc

    return Response(
        content=json.dumps({"ok": True, "outcome": result.outcome, "detail": result.detail}),
        media_type="application/json",
        status_code=status.HTTP_200_OK,
    )
