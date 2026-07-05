"""Application-level secret encryption for credentials stored at rest."""

from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

logger = logging.getLogger(__name__)

ENC_PREFIX = "enc:v1:"


def _fernet() -> Fernet:
    settings = get_settings()
    raw = settings.smtp_secret_encryption_key or settings.jwt_secret_key
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(plaintext: str | None) -> str | None:
    if plaintext is None or plaintext == "":
        return plaintext
    if plaintext.startswith(ENC_PREFIX):
        return plaintext
    token = _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")
    return f"{ENC_PREFIX}{token}"


def decrypt_secret(stored: str | None) -> str | None:
    if stored is None or stored == "":
        return stored
    if not stored.startswith(ENC_PREFIX):
        return stored
    token = stored.removeprefix(ENC_PREFIX)
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:
        logger.warning("Failed to decrypt stored secret (invalid token)")
        return None


def is_encrypted_secret(stored: str | None) -> bool:
    return bool(stored and stored.startswith(ENC_PREFIX))
