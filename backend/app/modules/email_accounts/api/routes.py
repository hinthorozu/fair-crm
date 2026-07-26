from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.email_accounts.api.dependencies import (
    get_auth_context,
    get_create_email_account_use_case,
    get_create_provider_account_use_case,
    get_delete_email_account_unified_use_case,
    get_get_email_account_unified_use_case,
    get_list_email_accounts_unified_use_case,
    get_send_test_email_account_unified_use_case,
    get_set_default_email_account_unified_use_case,
    get_update_email_account_use_case,
    get_update_provider_account_use_case,
    require_read_permission,
)
from app.modules.smtp.api.dependencies import get_send_test_smtp_mail_use_case
from app.modules.email_accounts.api.schemas import (
    CreateEmailAccountRequest,
    EmailAccountListResponse,
    EmailAccountResponse,
    ErrorResponse,
    ProviderDefinitionListResponse,
    ProviderDefinitionResponse,
    SendTestEmailAccountMailRequest,
    SendTestEmailAccountMailResponse,
    UpdateEmailAccountRequest,
)
from app.modules.email_accounts.application.create_provider_account import (
    CreateProviderAccountCommand,
    CreateProviderAccountUseCase,
)
from app.modules.email_accounts.application.manage_email_accounts import (
    DeleteEmailAccountUseCase,
    GetEmailAccountUseCase,
    ListEmailAccountsUseCase,
    SendTestEmailAccountMailUseCase,
    SetDefaultEmailAccountUseCase,
)
from app.modules.email_accounts.application.provider_definitions import list_provider_definitions
from app.modules.email_accounts.application.response_mappers import email_account_to_response_dict
from app.modules.email_accounts.application.update_provider_account import (
    UpdateProviderAccountCommand,
    UpdateProviderAccountUseCase,
)
from app.modules.email_accounts.domain.error_policy import ProviderErrorPolicyValidationError
from app.modules.email_accounts.domain.exceptions import (
    EmailAccountAlreadyDeletedError,
    EmailAccountNotDefaultEligibleError,
    EmailAccountNotFoundError,
)
from app.modules.smtp.application.commands import (
    CreateSmtpAccountCommand,
    SendTestSmtpMailCommand,
    UpdateSmtpAccountCommand,
)
from app.modules.smtp.application.create_smtp_account import CreateSmtpAccountUseCase
from app.modules.smtp.application.send_test_smtp_mail import SendTestSmtpMailUseCase
from app.modules.smtp.application.smtp_test_debug import smtp_debug_response_enabled
from app.modules.smtp.application.update_smtp_account import UpdateSmtpAccountUseCase
from app.modules.smtp.domain.exceptions import (
    InvalidSmtpAccountEmailError,
    InvalidSmtpAccountHostError,
    InvalidSmtpAccountNameError,
    InvalidSmtpAccountPortError,
    InvalidSmtpEncryptionTypeError,
    InvalidSmtpTestRecipientError,
    SmtpAccountAlreadyDeletedError,
    SmtpAccountNotFoundError,
)

router = APIRouter(prefix="/email-accounts", tags=["email-accounts"])
bearer_scheme = HTTPBearer(auto_error=False)

_SMTP_COMMAND_FIELDS = frozenset(
    {
        "name",
        "from_email",
        "from_name",
        "host",
        "port",
        "username",
        "password",
        "encryption_type",
        "is_default",
        "is_active",
        "max_delivery_attempts",
    }
)


def _access_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials and credentials.credentials:
        return credentials.credentials
    from app.integrations.kyrox_core.dev_bypass import dev_bypass_enabled

    if dev_bypass_enabled():
        return get_settings().dev_bypass_token or "dev-bypass"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def _smtp_fields(data: dict) -> dict:
    return {key: value for key, value in data.items() if key in _SMTP_COMMAND_FIELDS and value is not None}


def _to_response(data: dict) -> EmailAccountResponse:
    return EmailAccountResponse.model_validate(data)


def _smtp_result_to_response(result) -> EmailAccountResponse:
    data = result.__dict__.copy()
    data["config_warnings"] = list(data.get("config_warnings") or ())
    data.setdefault("account_type", "smtp")
    data.setdefault("provider_key", None)
    data.setdefault("provider_config", None)
    data.setdefault("secrets_set", {})
    data.setdefault("error_policy", None)
    return _to_response(data)


@router.get(
    "/providers",
    response_model=ProviderDefinitionListResponse,
    responses={403: {"model": ErrorResponse}},
)
def list_email_account_providers(
    _auth: AuthContext = Depends(require_read_permission),
) -> ProviderDefinitionListResponse:
    items = [
        ProviderDefinitionResponse.model_validate(definition.to_dict())
        for definition in list_provider_definitions()
    ]
    return ProviderDefinitionListResponse(items=items)


@router.post(
    "",
    response_model=EmailAccountResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
def create_email_account(
    body: CreateEmailAccountRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    smtp_use_case: CreateSmtpAccountUseCase = Depends(get_create_email_account_use_case),
    provider_use_case: CreateProviderAccountUseCase = Depends(get_create_provider_account_use_case),
) -> EmailAccountResponse:
    account_type = (body.account_type or "smtp").strip().lower()
    try:
        if account_type == "provider":
            account, provider_config = provider_use_case.execute(
                CreateProviderAccountCommand(
                    organization_id=auth.organization_id,
                    access_token=_access_token(credentials),
                    user_id=auth.user_id,
                    name=body.name,
                    provider_key=body.provider_key or "",
                    provider_config=body.provider_config or {},
                    error_policy=body.error_policy.model_dump() if body.error_policy else None,
                    from_email=body.from_email,
                    from_name=body.from_name,
                    is_default=body.is_default,
                    is_active=body.is_active,
                    max_delivery_attempts=body.max_delivery_attempts,
                )
            )
            return _to_response(
                email_account_to_response_dict(account, provider_config=provider_config)
            )

        result = smtp_use_case.execute(
            CreateSmtpAccountCommand(
                organization_id=auth.organization_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                **_smtp_fields(body.model_dump()),
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (
        InvalidSmtpAccountNameError,
        InvalidSmtpAccountEmailError,
        InvalidSmtpAccountHostError,
        InvalidSmtpAccountPortError,
        InvalidSmtpEncryptionTypeError,
        ProviderErrorPolicyValidationError,
        ValueError,
    ) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _smtp_result_to_response(result)


@router.get(
    "",
    response_model=EmailAccountListResponse,
    responses={403: {"model": ErrorResponse}},
)
def list_email_accounts(
    auth: AuthContext = Depends(require_read_permission),
    use_case: ListEmailAccountsUseCase = Depends(get_list_email_accounts_unified_use_case),
) -> EmailAccountListResponse:
    items = use_case.execute(auth.organization_id)
    return EmailAccountListResponse(items=[_to_response(item) for item in items])


@router.get(
    "/{account_id}",
    response_model=EmailAccountResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_email_account(
    account_id: UUID,
    auth: AuthContext = Depends(require_read_permission),
    use_case: GetEmailAccountUseCase = Depends(get_get_email_account_unified_use_case),
) -> EmailAccountResponse:
    try:
        return _to_response(use_case.execute(auth.organization_id, account_id))
    except EmailAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch(
    "/{account_id}",
    response_model=EmailAccountResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
def update_email_account(
    account_id: UUID,
    body: UpdateEmailAccountRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    smtp_use_case: UpdateSmtpAccountUseCase = Depends(get_update_email_account_use_case),
    provider_use_case: UpdateProviderAccountUseCase = Depends(get_update_provider_account_use_case),
    get_use_case: GetEmailAccountUseCase = Depends(get_get_email_account_unified_use_case),
) -> EmailAccountResponse:
    try:
        current = get_use_case.execute(auth.organization_id, account_id)
    except EmailAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        if current.get("account_type") == "provider":
            account, provider_config = provider_use_case.execute(
                UpdateProviderAccountCommand(
                    organization_id=auth.organization_id,
                    account_id=account_id,
                    access_token=_access_token(credentials),
                    user_id=auth.user_id,
                    name=body.name,
                    from_email=body.from_email,
                    from_name=body.from_name,
                    is_default=body.is_default,
                    is_active=body.is_active,
                    max_delivery_attempts=body.max_delivery_attempts,
                    provider_config=body.provider_config,
                    error_policy=body.error_policy.model_dump() if body.error_policy else None,
                )
            )
            return _to_response(
                email_account_to_response_dict(account, provider_config=provider_config)
            )

        result = smtp_use_case.execute(
            UpdateSmtpAccountCommand(
                organization_id=auth.organization_id,
                account_id=account_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                **_smtp_fields(body.model_dump(exclude_unset=True)),
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (EmailAccountNotFoundError, SmtpAccountNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (
        EmailAccountAlreadyDeletedError,
        SmtpAccountAlreadyDeletedError,
        InvalidSmtpAccountNameError,
        InvalidSmtpAccountEmailError,
        InvalidSmtpAccountHostError,
        InvalidSmtpAccountPortError,
        InvalidSmtpEncryptionTypeError,
        ProviderErrorPolicyValidationError,
        ValueError,
    ) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _smtp_result_to_response(result)


@router.post(
    "/{account_id}/set-default",
    response_model=EmailAccountResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
def set_default_email_account(
    account_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: SetDefaultEmailAccountUseCase = Depends(get_set_default_email_account_unified_use_case),
) -> EmailAccountResponse:
    try:
        return _to_response(
            use_case.execute(
                organization_id=auth.organization_id,
                account_id=account_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except EmailAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (EmailAccountAlreadyDeletedError, EmailAccountNotDefaultEligibleError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _to_smtp_test_mail_response(result) -> SendTestEmailAccountMailResponse:
    data = {
        "success": result.success,
        "message": result.message,
        "config_warnings": list(result.config_warnings or ()),
    }
    if smtp_debug_response_enabled():
        data.update(
            {
                "debug_error_type": result.debug_error_type,
                "debug_error_message": result.debug_error_message,
                "smtp_host": result.smtp_host,
                "smtp_port": result.smtp_port,
                "encryption_type": result.encryption_type,
            }
        )
    return SendTestEmailAccountMailResponse.model_validate(data)


@router.post(
    "/{account_id}/test",
    response_model=SendTestEmailAccountMailResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
def send_test_email_account_mail(
    account_id: UUID,
    body: SendTestEmailAccountMailRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    get_use_case: GetEmailAccountUseCase = Depends(get_get_email_account_unified_use_case),
    smtp_use_case: SendTestSmtpMailUseCase = Depends(get_send_test_smtp_mail_use_case),
    provider_use_case: SendTestEmailAccountMailUseCase = Depends(
        get_send_test_email_account_unified_use_case
    ),
) -> SendTestEmailAccountMailResponse:
    try:
        current = get_use_case.execute(auth.organization_id, account_id)
    except EmailAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        if current.get("account_type") == "provider":
            result = provider_use_case.execute(
                organization_id=auth.organization_id,
                account_id=account_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                recipient=body.recipient,
            )
            response = SendTestEmailAccountMailResponse(
                success=result.success,
                message=result.message,
                config_warnings=list(result.config_warnings),
            )
        else:
            result = smtp_use_case.execute(
                SendTestSmtpMailCommand(
                    organization_id=auth.organization_id,
                    account_id=account_id,
                    access_token=_access_token(credentials),
                    user_id=auth.user_id,
                    recipient=body.recipient,
                )
            )
            response = _to_smtp_test_mail_response(result)
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (EmailAccountNotFoundError, SmtpAccountNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (InvalidSmtpTestRecipientError, EmailAccountAlreadyDeletedError, SmtpAccountAlreadyDeletedError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not result.success:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=response.model_dump(exclude_none=True),
        )
    return response


@router.delete(
    "/{account_id}",
    response_model=EmailAccountResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def delete_email_account(
    account_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: DeleteEmailAccountUseCase = Depends(get_delete_email_account_unified_use_case),
) -> EmailAccountResponse:
    try:
        return _to_response(
            use_case.execute(
                organization_id=auth.organization_id,
                account_id=account_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except EmailAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
