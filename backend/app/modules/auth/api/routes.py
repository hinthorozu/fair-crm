"""Auth bridge routes: Core token issuance + HttpOnly refresh cookie transport."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.modules.auth.api.cookies import (
    clear_refresh_cookie,
    csrf_header_ok,
    read_refresh_cookie,
    set_refresh_cookie,
)
from app.modules.auth.api.dependencies import get_core_auth_client
from app.modules.auth.api.schemas import (
    AccessTokenResponse,
    ActivationCompleteRequest,
    AuthMessageResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutBodyRequest,
    RefreshBodyRequest,
    ResetPasswordRequest,
    SignupRequest,
)
from app.modules.auth.infrastructure.core_auth_client import CoreAuthClient, CoreAuthError

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_error_response(exc: CoreAuthError, *, clear_cookie: bool = False) -> JSONResponse:
    status_code = exc.status_code if 400 <= exc.status_code < 600 else 401
    response = JSONResponse(status_code=status_code, content={"detail": exc.message})
    if clear_cookie:
        clear_refresh_cookie(response)
    return response


def _read_bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("Authorization", "")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        return None
    return parts[1].strip()


@router.post(
    "/login",
    response_model=AccessTokenResponse,
    responses={401: {"description": "Invalid credentials"}, 503: {"description": "Core unavailable"}},
)
def login(
    payload: LoginRequest,
    response: Response,
    client: CoreAuthClient = Depends(get_core_auth_client),
) -> AccessTokenResponse | JSONResponse:
    try:
        pair = client.login(email=payload.email, password=payload.password)
    except CoreAuthError as exc:
        return _auth_error_response(exc)

    set_refresh_cookie(response, pair.refresh_token)
    return AccessTokenResponse(
        access_token=pair.access_token,
        token_type=pair.token_type,
        expires_in=pair.expires_in,
    )


@router.post(
    "/signup",
    response_model=AuthMessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def signup(
    payload: SignupRequest,
    client: CoreAuthClient = Depends(get_core_auth_client),
) -> AuthMessageResponse | JSONResponse:
    try:
        result = client.signup(
            organization_name=payload.organization_name,
            email=str(payload.email),
            organization_slug=payload.organization_slug,
        )
    except CoreAuthError as exc:
        return _auth_error_response(exc)
    return AuthMessageResponse(message=result.message)


@router.post(
    "/activation/complete",
    response_model=AuthMessageResponse,
)
def complete_activation(
    payload: ActivationCompleteRequest,
    client: CoreAuthClient = Depends(get_core_auth_client),
) -> AuthMessageResponse | JSONResponse:
    try:
        result = client.complete_activation(token=payload.token, password=payload.password)
    except CoreAuthError as exc:
        return _auth_error_response(exc)
    return AuthMessageResponse(message=result.message)


@router.post(
    "/password/forgot",
    response_model=AuthMessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def forgot_password(
    payload: ForgotPasswordRequest,
    client: CoreAuthClient = Depends(get_core_auth_client),
) -> AuthMessageResponse | JSONResponse:
    try:
        result = client.forgot_password(email=str(payload.email))
    except CoreAuthError as exc:
        return _auth_error_response(exc)
    return AuthMessageResponse(message=result.message)


@router.post(
    "/password/reset",
    response_model=AuthMessageResponse,
)
def reset_password(
    payload: ResetPasswordRequest,
    response: Response,
    client: CoreAuthClient = Depends(get_core_auth_client),
) -> AuthMessageResponse | JSONResponse:
    try:
        result = client.reset_password(token=payload.token, password=payload.password)
    except CoreAuthError as exc:
        return _auth_error_response(exc)

    clear_refresh_cookie(response)
    return AuthMessageResponse(message=result.message)


@router.post(
    "/password/change",
    response_model=AuthMessageResponse,
    responses={401: {"description": "Bearer access token required"}},
)
def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    response: Response,
    client: CoreAuthClient = Depends(get_core_auth_client),
) -> AuthMessageResponse | JSONResponse:
    access_token = _read_bearer_token(request)
    if access_token is None:
        return JSONResponse(status_code=401, content={"detail": "Bearer access token required"})

    try:
        result = client.change_password(
            access_token=access_token,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except CoreAuthError as exc:
        return _auth_error_response(exc)

    clear_refresh_cookie(response)
    return AuthMessageResponse(message=result.message)


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    responses={401: {"description": "Invalid or expired refresh token"}},
)
def refresh(
    request: Request,
    response: Response,
    payload: RefreshBodyRequest = RefreshBodyRequest(),
    client: CoreAuthClient = Depends(get_core_auth_client),
) -> AccessTokenResponse | JSONResponse:
    if not csrf_header_ok(request):
        return JSONResponse(status_code=403, content={"detail": "CSRF header required"})

    cookie_token = read_refresh_cookie(request)
    refresh_token = cookie_token or payload.refresh_token
    if not refresh_token:
        missing = JSONResponse(status_code=401, content={"detail": "Refresh token required"})
        clear_refresh_cookie(missing)
        return missing

    try:
        pair = client.refresh(refresh_token=refresh_token)
    except CoreAuthError as exc:
        return _auth_error_response(exc, clear_cookie=True)

    # Rotation: always replace cookie with the new opaque refresh token from Core.
    set_refresh_cookie(response, pair.refresh_token)
    return AccessTokenResponse(
        access_token=pair.access_token,
        token_type=pair.token_type,
        expires_in=pair.expires_in,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={204: {"description": "Logged out"}},
)
def logout(
    request: Request,
    response: Response,
    payload: LogoutBodyRequest = LogoutBodyRequest(),
    client: CoreAuthClient = Depends(get_core_auth_client),
) -> Response:
    cookie_token = read_refresh_cookie(request)
    refresh_token = cookie_token or payload.refresh_token
    if refresh_token:
        client.logout(refresh_token=refresh_token)
    clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/session-config")
def session_config() -> dict[str, int]:
    """Expose configured TTLs (no secrets). Actual JWT exp is set by Core on issue."""
    settings = get_settings()
    return {
        "access_token_expire_days": settings.access_token_expire_days,
        "refresh_token_expire_days": settings.refresh_token_expire_days,
        "access_token_expire_seconds": settings.access_token_expire_days * 24 * 60 * 60,
        "refresh_cookie_max_age_seconds": settings.refresh_token_expire_days * 24 * 60 * 60,
    }
