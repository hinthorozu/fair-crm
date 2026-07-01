from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import jwt

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.integrations.kyrox_core.ports import AuthContext


@dataclass(frozen=True)
class TokenClaims:
    user_id: UUID
    email: str
    session_id: UUID


def decode_access_token(token: str) -> TokenClaims:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc

    try:
        return TokenClaims(
            user_id=UUID(payload["sub"]),
            email=payload["email"],
            session_id=UUID(payload["sid"]),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise UnauthorizedError("Invalid token claims") from exc


def build_auth_context(
    token: str,
    organization_id: UUID,
) -> AuthContext:
    claims = decode_access_token(token)
    return AuthContext(
        user_id=claims.user_id,
        email=claims.email,
        session_id=claims.session_id,
        organization_id=organization_id,
    )


def create_test_token(
    *,
    user_id: UUID,
    email: str = "test@example.com",
    session_id: UUID | None = None,
    secret_key: str | None = None,
    expires_in_seconds: int = 3600,
) -> str:
    """Helper for tests — issues a JWT compatible with Core claim shape."""
    from uuid import uuid4

    settings = get_settings()
    now = datetime.now(tz=UTC)
    payload = {
        "sub": str(user_id),
        "email": email,
        "sid": str(session_id or uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(now.timestamp()) + expires_in_seconds,
        "jti": str(uuid4()),
    }
    return jwt.encode(
        payload,
        secret_key or settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
